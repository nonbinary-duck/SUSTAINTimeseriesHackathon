package main

import (
    "archive/tar"
    "bytes"
    "context"
    "encoding/json"
    "log"
    "net/http"
    "net/netip"
    "os"
    "sync"
    "time"

    "github.com/moby/moby/api/types/container"
    "github.com/moby/moby/api/types/network"
    "github.com/moby/moby/client"
)

var (
    currentCtx    context.Context
    cancelCurrent context.CancelFunc
    activeCommit  string // Track which commit is currently building
    mu            sync.Mutex
)

type Update struct {
    Commit string `json:"commit"`
    Status string `json:"status"`
    Log    string `json:"log"`
    Time   string `json:"time"`
}

func main() {
    http.HandleFunc("/trigger", func(w http.ResponseWriter, r *http.Request) {
        commit := r.URL.Query().Get("commit")
        if commit == "" {
            http.Error(w, "Missing commit parameter", http.StatusBadRequest)
            return
        }

        mu.Lock()
        // 1. If the same commit is already running, ignore this request
        if activeCommit == commit && cancelCurrent != nil {
            mu.Unlock()
            log.Printf("Build for %s already in progress. Ignoring request.", commit)
            w.WriteHeader(http.StatusAccepted)
            return
        }

        // 2. If a different commit is running, cancel it
        if cancelCurrent != nil {
            log.Printf("Newer commit %s received. Cancelling build for %s.", commit, activeCommit)
            cancelCurrent()
            // Notify UI that the PREVIOUS commit was cancelled
            go sendStatus(activeCommit, "Cancelled", "Build cancelled by newer push.", "")
        }

        // 3. Set up the new build context
        currentCtx, cancelCurrent = context.WithCancel(context.Background())
        activeCommit = commit
        ctx := currentCtx
        mu.Unlock()

        go runBuild(ctx, commit)
        w.WriteHeader(http.StatusOK)
    })

    log.Println("Builder listening on :8080")
    log.Fatal(http.ListenAndServe(":8080", nil))
}

func getBuildTime() string {
    resp, err := http.Get(os.Getenv("STATUS_TIME_URL"))
    if err != nil {
        return time.Now().Format(time.RFC3339)
    }
    defer resp.Body.Close()
    var res map[string]string
    _ = json.NewDecoder(resp.Body).Decode(&res)
    return res["time"]
}

func sendStatus(commit, status, logStr, buildTime string) {
    if commit == "" {
        return
    }
    data, _ := json.Marshal(Update{
        Commit: commit,
        Status: status,
        Log:    logStr,
        Time:   buildTime,
    })
    _, _ = http.Post(os.Getenv("STATUS_URL"), "application/json", bytes.NewBuffer(data))
}

func runBuild(ctx context.Context, commit string) {
    // Ensure we clean up global state when this specific build finishes
    defer func() {
        mu.Lock()
        if activeCommit == commit {
            activeCommit = ""
            cancelCurrent = nil
        }
        mu.Unlock()
    }()

    buildTime := getBuildTime()
    logStr := "Starting Docker build via Go API...\n"
    sendStatus(commit, "Building", logStr, buildTime)

    cli, err := client.NewClientWithOpts(client.FromEnv, client.WithAPIVersionNegotiation())
    if err != nil {
        sendStatus(commit, "Failed", logStr+"Docker init error: "+err.Error(), buildTime)
        return
    }

    // Prepare Docker Context (Tar)
    buf := new(bytes.Buffer)
    tw := tar.NewWriter(buf)
    df, err := os.ReadFile("/app/Dockerfile.autoci")
    if err == nil {
        _ = tw.WriteHeader(&tar.Header{
            Name: "Dockerfile",
            Size: int64(len(df)),
        })
        _, _ = tw.Write(df)
    }
    _ = tw.Close()

    buildArgs := make(map[string]*string)
    buildArgs["COMMIT_ID"] = &commit
    buildArgs["BUILD_TIME"] = &buildTime

    res, err := cli.ImageBuild(ctx, buf, client.ImageBuildOptions{
        Tags:       []string{os.Getenv("TARGET_IMAGE")},
        BuildArgs:  buildArgs,
        Dockerfile: "Dockerfile",
    })
    if err != nil {
        if ctx.Err() != nil {
            sendStatus(commit, "Cancelled", logStr+"Build cancelled.", buildTime)
        } else {
            sendStatus(commit, "Failed", logStr+"Build error: "+err.Error(), buildTime)
        }
        return
    }

    // ----------------------------------------------------
    // STREAM LOGS
    // ----------------------------------------------------
    var logMu sync.Mutex
    done := make(chan bool)

    go func() {
        ticker := time.NewTicker(1 * time.Second)
        defer ticker.Stop()
        for {
            select {
            case <-ticker.C:
                logMu.Lock()
                currLog := logStr
                logMu.Unlock()
                sendStatus(commit, "Building", currLog, buildTime)
            case <-done:
                return
            case <-ctx.Done():
                return
            }
        }
    }()

    decoder := json.NewDecoder(res.Body)
    for {
        var msg struct {
            Stream string `json:"stream"`
            Error  string `json:"error"`
        }
        if err := decoder.Decode(&msg); err != nil {
            break
        }
        logMu.Lock()
        if msg.Error != "" {
            logStr += msg.Error + "\n"
        } else if msg.Stream != "" {
            logStr += msg.Stream
        }
        logMu.Unlock()
    }
    res.Body.Close()
    close(done)

    logMu.Lock()
    logStr += "\nBuild finished. Replacing container..."
    finalLog := logStr
    logMu.Unlock()

    // Check if we were cancelled during the log streaming phase
    if ctx.Err() != nil {
        sendStatus(commit, "Cancelled", finalLog+"\nCancelled by newer push.", buildTime)
        return
    }

    // ----------------------------------------------------
    // DEPLOYMENT
    // ----------------------------------------------------
    target := os.Getenv("TARGET_CONTAINER")
    _, _ = cli.ContainerStop(ctx, target, client.ContainerStopOptions{})
    _, _ = cli.ContainerRemove(ctx, target, client.ContainerRemoveOptions{Force: true})

    port5001, err := network.ParsePort("5001/tcp")
    if err != nil {
        sendStatus(commit, "Failed", finalLog+"\nPort parse error: "+err.Error(), buildTime)
        return
    }

    cont, err := cli.ContainerCreate(ctx, client.ContainerCreateOptions{
        Name: target,
        Config: &container.Config{
            Image:        os.Getenv("TARGET_IMAGE"),
            ExposedPorts: network.PortSet{port5001: struct{}{}},
        },
        HostConfig: &container.HostConfig{
            PortBindings: network.PortMap{
                port5001: []network.PortBinding{{
                    HostIP:   netip.MustParseAddr("0.0.0.0"),
                    HostPort: "5001",
                }},
            },
            Resources: container.Resources{
                Memory:   4 * 1024 * 1024 * 1024,
                NanoCPUs: 4000000000,
            },
            RestartPolicy: container.RestartPolicy{Name: "always"},
        },
    })
    if err != nil {
        sendStatus(commit, "Failed", finalLog+"\nRun error: "+err.Error(), buildTime)
        return
    }

    if err := cli.ContainerStart(ctx, cont.ID, client.ContainerStartOptions{}); err != nil {
        sendStatus(commit, "Failed", finalLog+"\nStart error: "+err.Error(), buildTime)
        return
    }

    sendStatus(commit, "Success", finalLog+"\nContainer running successfully.", buildTime)
}