package main

import (
    "archive/tar"
    "bytes"
    "context"
    "encoding/json"
    "io"
    "log"
    "net/http"
    "os"
    "sync"

    "github.com/docker/docker/api/types"
    "github.com/docker/docker/api/types/container"
    "github.com/docker/docker/client"
    "github.com/docker/go-connections/nat"
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
    if err != nil { return "Unknown Time" }
    defer resp.Body.Close()
    var res map[string]string
    json.NewDecoder(resp.Body).Decode(&res)
    return res["time"]
}

func sendStatus(commit, status, logStr, buildTime string) {
    data, _ := json.Marshal(Update{Commit: commit, Status: status, Log: logStr, Time: buildTime})
    http.Post(os.Getenv("STATUS_URL"), "application/json", bytes.NewBuffer(data))
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

    // 1. Create Tarball in memory containing just Dockerfile.autoci
    buf := new(bytes.Buffer)
    tw := tar.NewWriter(buf)
    df, err := os.ReadFile("/app/Dockerfile.autoci")
    if err == nil {
        tw.WriteHeader(&tar.Header{Name: "Dockerfile", Size: int64(len(df))})
        tw.Write(df)
    }
    tw.Close()

    // 2. Build Image
    buildArgs := make(map[string]*string)
    buildArgs["COMMIT_ID"] = &commit
    buildArgs["BUILD_TIME"] = &buildTime

    res, err := cli.ImageBuild(ctx, buf, types.ImageBuildOptions{
        Tags:       []string{os.Getenv("TARGET_IMAGE")},
        BuildArgs:  buildArgs,
        Dockerfile: "Dockerfile",
    })
    
    if err != nil {
        sendStatus(commit, "Failed", logStr+"Build error: "+err.Error(), buildTime)
        return
    }
    
    buildLogs, _ := io.ReadAll(res.Body)
    res.Body.Close()
    logStr += string(buildLogs) + "\nBuild finished. Replacing container..."

    // Check if context was cancelled during build
    if ctx.Err() != nil {
        sendStatus(commit, "Cancelled", logStr+"\nCancelled by newer push.", buildTime)
        return
    }

    // 3. Recreate Container
    target := os.Getenv("TARGET_CONTAINER")
    cli.ContainerStop(ctx, target, container.StopOptions{})
    cli.ContainerRemove(ctx, target, types.ContainerRemoveOptions{Force: true})

    cont, err := cli.ContainerCreate(ctx, &container.Config{
        Image: os.Getenv("TARGET_IMAGE"),
        ExposedPorts: nat.PortSet{"5001/tcp": struct{}{}},
    }, &container.HostConfig{
        PortBindings: nat.PortMap{"5001/tcp": []nat.PortBinding{{HostIP: "0.0.0.0", HostPort: "5001"}}},
        Resources: container.Resources{Memory: 4 * 1024 * 1024 * 1024, NanoCPUs: 4000000000},
        RestartPolicy: container.RestartPolicy{Name: "always"},
    }, nil, nil, target)

    if err != nil {
        sendStatus(commit, "Failed", logStr+"\nRun error: "+err.Error(), buildTime)
        return
    }

    cli.ContainerStart(ctx, cont.ID, types.ContainerStartOptions{})
    sendStatus(commit, "Success", logStr+"\nContainer running successfully.", buildTime)
}