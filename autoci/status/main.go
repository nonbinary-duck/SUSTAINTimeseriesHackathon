package main

import (
    "encoding/json"
    "html/template"
    "log"
    "net/http"
    "sync"
    "time"
)

type Build struct {
    Commit string `json:"commit"`
    Status string `json:"status"`
    Log    string `json:"log"`
    Time   string `json:"time"`
}

var (
    builds []Build
    mu     sync.Mutex
)

func main() {
    // API: Receive updates from Builder
    http.HandleFunc("/update", func(w http.ResponseWriter, r *http.Request) {
        var update Build
        json.NewDecoder(r.Body).Decode(&update)

        mu.Lock()
        if len(builds) == 0 || builds[0].Status == "Success" || builds[0].Status == "Failed" || builds[0].Status == "Cancelled" {
            if update.Time == "" { update.Time = time.Now().Format(time.RFC3339) }
            builds = append([]Build{update}, builds...)
        } else {
            builds[0].Status = update.Status
            builds[0].Log = update.Log
            if update.Time != "" { builds[0].Time = update.Time }
        }
        mu.Unlock()
        w.WriteHeader(http.StatusOK)
    })

    // API: Time provider
    http.HandleFunc("/api/time", func(w http.ResponseWriter, r *http.Request) {
        w.Header().Set("Content-Type", "application/json")
        json.NewEncoder(w).Encode(map[string]string{"time": time.Now().Format(time.RFC3339)})
    })

    // API: AJAX latest status
    http.HandleFunc("/api/latest", func(w http.ResponseWriter, r *http.Request) {
        mu.Lock()
        defer mu.Unlock()
        w.Header().Set("Content-Type", "application/json")
        w.Header().Set("Access-Control-Allow-Origin", "*")
        if len(builds) > 0 {
            json.NewEncoder(w).Encode(builds[0])
        } else {
            json.NewEncoder(w).Encode(Build{Status: "None"})
        }
    })

    // UI: Dashboard
    http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
        tmpl := `
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>CI Build Status</title>
            <meta http-equiv="refresh" content="5">
            <style>
                body { font-family: 'Segoe UI', sans-serif; background: #0d1117; color: #c9d1d9; margin: 40px; }
                h1 a { color: #58a6ff; text-decoration: none; }
                .card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px; margin-bottom: 20px; }
                .status-Success { color: #3fb950; font-weight: bold; }
                .status-Building { color: #d29922; font-weight: bold; animation: blink 1.5s infinite; }
                .status-Failed, .status-Cancelled { color: #f85149; font-weight: bold; }
                pre { background: #010409; padding: 15px; border-radius: 6px; overflow-x: auto; color: #8b949e; }
                @keyframes blink { 50% { opacity: 0.5; } }
            </style>
        </head>
        <body>
            <h1><a href="/">🚀 Live Build Status</a></h1>
            {{range .}}
            <div class="card" id="{{.Commit}}">
                <h3>Commit: <a href="?commit={{.Commit}}" style="color:#58a6ff">{{.Commit}}</a></h3>
                <p>Time: {{.Time}} | Status: <span class="status-{{.Status}}">{{.Status}}</span></p>
                <pre>{{.Log}}</pre>
            </div>
            {{else}}
            <p>No builds yet.</p>
            {{end}}
        </body>
        </html>`
        
        mu.Lock()
        defer mu.Unlock()
        
        filter := r.URL.Query().Get("commit")
        display := builds
        if filter != "" {
            display = []Build{}
            for _, b := range builds {
                if b.Commit == filter {
                    display = append(display, b)
                    break
                }
            }
        }

        t, _ := template.New("ui").Parse(tmpl)
        t.Execute(w, display)
    })

    log.Println("Status listening on :8080")
    log.Fatal(http.ListenAndServe(":8080", nil))
}