package main

import (
    "archive/tar"
    "bytes"
    "context"
    "encoding/json"
    "io"
    "log"
    "net/http"
    "net/netip"
    "os"
    "sync"

    "github.com/moby/moby/api/types/container"
    "github.com/moby/moby/api/types/network"
    "github.com/moby/moby/client"
)

var (
    currentCtx    context.Context
    cancelCurrent context.CancelFunc
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

        mu.Lock()
        if cancelCurrent != nil {
            cancelCurrent()
            sendStatus(commit, "Cancelled", "Build cancelled by newer push.", "")
        }
        currentCtx, cancelCurrent = context.WithCancel(context.Background())
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
        return "Unknown Time"
    }
    defer resp.Body.Close()

    var res map[string]string
    _ = json.NewDecoder(resp.Body).Decode(&res)
    return res["time"]
}

func sendStatus(commit, status, logStr, buildTime string) {
    data, _ := json.Marshal(Update{
        Commit: commit,
        Status: status,
        Log:    logStr,
        Time:   buildTime,
    })
    _, _ = http.Post(os.Getenv("STATUS_URL"), "application/json", bytes.NewBuffer(data))
}

func runBuild(ctx context.Context, commit string) {
    buildTime := getBuildTime()
    logStr := "Starting Docker build via Go API...\n"
    sendStatus(commit, "Building", logStr, buildTime)

    cli, err := client.NewClientWithOpts(client.FromEnv, client.WithAPIVersionNegotiation())
    if err != nil {
        sendStatus(commit, "Failed", logStr+"Docker init error: "+err.Error(), buildTime)
        return
    }

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
        sendStatus(commit, "Failed", logStr+"Build error: "+err.Error(), buildTime)
        return
    }

    buildLogs, _ := io.ReadAll(res.Body)
    _ = res.Body.Close()
    logStr += string(buildLogs) + "\nBuild finished. Replacing container..."

    if ctx.Err() != nil {
        sendStatus(commit, "Cancelled", logStr+"\nCancelled by newer push.", buildTime)
        return
    }

    target := os.Getenv("TARGET_CONTAINER")

    _, _ = cli.ContainerStop(ctx, target, client.ContainerStopOptions{})
    _, _ = cli.ContainerRemove(ctx, target, client.ContainerRemoveOptions{Force: true})

    port5001, err := network.ParsePort("5001/tcp")
    if err != nil {
        sendStatus(commit, "Failed", logStr+"\nPort parse error: "+err.Error(), buildTime)
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
        sendStatus(commit, "Failed", logStr+"\nRun error: "+err.Error(), buildTime)
        return
    }

    _, err = cli.ContainerStart(ctx, cont.ID, client.ContainerStartOptions{})
    if err != nil {
        sendStatus(commit, "Failed", logStr+"\nStart error: "+err.Error(), buildTime)
        return
    }

    sendStatus(commit, "Success", logStr+"\nContainer running successfully.", buildTime)
}