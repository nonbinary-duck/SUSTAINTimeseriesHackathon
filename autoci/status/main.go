package main

import (
    "encoding/json"
    "log"
    "net/http"
    "os"
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

const dataFile = "/data/builds.json"
const tempFile = "/data/builds.tmp"

func loadBuilds() {
    b, err := os.ReadFile(dataFile)
    if err == nil {
        json.Unmarshal(b, &builds)
        log.Printf("Loaded %d builds from disk", len(builds))
    } else {
        log.Println("No existing build data found. Starting fresh.")
    }
}

func saveBuilds() {
    b, err := json.MarshalIndent(builds, "", "  ")
    if err == nil {
        // Write safely to a temp file, then rename to prevent corruption if container crashes mid-write
        os.WriteFile(tempFile, b, 0644)
        os.Rename(tempFile, dataFile)
    }
}

func main() {
    loadBuilds()

    // API: Receive updates from Builder
    http.HandleFunc("/update", func(w http.ResponseWriter, r *http.Request) {
        var update Build
        json.NewDecoder(r.Body).Decode(&update)
        
        mu.Lock()
        if len(builds) == 0 || builds[0].Status == "Success" || builds[0].Status == "Failed" || builds[0].Status == "Cancelled" {
            if update.Time == "" {
                update.Time = time.Now().Format(time.RFC3339)
            }
            builds = append([]Build{update}, builds...)
        } else {
            builds[0].Status = update.Status
            builds[0].Log = update.Log
            if update.Time != "" {
                builds[0].Time = update.Time
            }
        }
        saveBuilds()
        mu.Unlock()
        
        w.WriteHeader(http.StatusOK)
    })

    // API: Time provider
    http.HandleFunc("/api/time", func(w http.ResponseWriter, r *http.Request) {
        w.Header().Set("Content-Type", "application/json")
        json.NewEncoder(w).Encode(map[string]string{"time": time.Now().Format(time.RFC3339)})
    })

    // API: AJAX latest status for the webapp footer
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

    // API: All builds for the UI
    http.HandleFunc("/api/all", func(w http.ResponseWriter, r *http.Request) {
        mu.Lock()
        defer mu.Unlock()
        w.Header().Set("Content-Type", "application/json")
        json.NewEncoder(w).Encode(builds)
    })

    // UI: Dashboard
    http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
        html := `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>CI Build Status</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0d1117; color: #c9d1d9; margin: 40px; }
        h1 { margin-bottom: 30px; }
        h1 a { color: #58a6ff; text-decoration: none; }
        .card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; margin-bottom: 15px; overflow: hidden; }
        .card-header { padding: 15px 20px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; background: #21262d; transition: background 0.2s; }
        .card-header:hover { background: #30363d; }
        .card-body { padding: 0; display: none; border-top: 1px solid #30363d; }
        .status-Success { color: #3fb950; font-weight: bold; background: rgba(63, 185, 80, 0.1); padding: 4px 8px; border-radius: 4px; }
        .status-Building { color: #d29922; font-weight: bold; background: rgba(210, 153, 34, 0.1); padding: 4px 8px; border-radius: 4px; animation: blink 1.5s infinite; }
        .status-Failed, .status-Cancelled { color: #f85149; font-weight: bold; background: rgba(248, 81, 73, 0.1); padding: 4px 8px; border-radius: 4px; }
        pre { background: #010409; padding: 20px; margin: 0; overflow-x: auto; color: #8b949e; font-size: 13px; max-height: 500px; overflow-y: auto; }
        .commit-link { color: #58a6ff; text-decoration: none; font-family: monospace; font-size: 1.1em; }
        .commit-link:hover { text-decoration: underline; }
        @keyframes blink { 50% { opacity: 0.6; } }
    </style>
</head>
<body>
    <h1><a href="javascript:window.location.reload()">🚀 Live Build Status</a></h1>
    <div id="builds-container">
        <p style="color: #8b949e;">Loading builds...</p>
    </div>

    <script>
        function toggle(id) {
            const el = document.getElementById('body-' + id);
            el.style.display = el.style.display === 'block' ? 'none' : 'block';
        }

        // Dynamically fix the path to survive reverse proxies missing trailing slashes
        const basePath = window.location.pathname.endsWith('/') 
            ? window.location.pathname 
            : window.location.pathname + '/';

        async function fetchBuilds() {
            try {
                const res = await fetch(basePath + 'api/all');
                if (!res.ok) throw new Error("HTTP " + res.status);
                
                const builds = await res.json();
                const container = document.getElementById('builds-container');
                
                if (!builds || builds.length === 0) {
                    container.innerHTML = '<p style="color: #8b949e;">No builds have been triggered yet.</p>';
                    return;
                }

                let html = '';
                builds.forEach((b, i) => {
                    const isOpen = (i === 0 || b.status === 'Building') ? 'block' : 'none';
                    const shortCommit = b.commit.substring(0, 7) || 'Manual';
                    
                    html += '<div class="card">';
                    html += '  <div class="card-header" onclick="toggle(\'' + b.commit + '\')">';
                    html += '    <div><strong>Commit:</strong> <a href="https://github.com/nonbinary-duck/SUSTAINTimeseriesHackathon/commit/' + b.commit + '" class="commit-link" target="_blank" onclick="event.stopPropagation()">' + shortCommit + '</a></div>';
                    html += '    <div><span style="color: #8b949e; margin-right: 15px;">' + b.time + '</span> <span class="status-' + b.status + '">' + b.status + '</span></div>';
                    html += '  </div>';
                    html += '  <div class="card-body" id="body-' + b.commit + '" style="display: ' + isOpen + ';">';
                    html += '    <pre>' + (b.log || 'Waiting for logs...') + '</pre>';
                    html += '  </div>';
                    html += '</div>';
                });
                
                if (container.getAttribute('data-hash') !== JSON.stringify(builds.map(b => b.status + b.log.length))) {
                    container.innerHTML = html;
                    container.setAttribute('data-hash', JSON.stringify(builds.map(b => b.status + b.log.length)));
                }
            } catch (e) {
                console.error("Failed to fetch builds:", e);
            }
        }

        fetchBuilds();
        setInterval(fetchBuilds, 1500);
    </script>
</body>
</html>`
        w.Header().Set("Content-Type", "text/html")
        w.Write([]byte(html))
    })

    log.Println("Status listening on :8080")
    log.Fatal(http.ListenAndServe(":8080", nil))
}