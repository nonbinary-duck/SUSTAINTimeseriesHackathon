package main

import (
    "bytes"
    "encoding/json"
    "log"
    "net/http"
    "os"
)

func main() {
    http.HandleFunc("/webhook", func(w http.ResponseWriter, r *http.Request) {
        if r.Method != http.MethodPost {
            http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
            return
        }
        var payload struct{ After string `json:"after"` }
        json.NewDecoder(r.Body).Decode(&payload)
        
        commit := payload.After
        if commit == "" { commit = "manual-trigger" }

        // Forward to internal builder
        builderURL := os.Getenv("BUILDER_URL")
        http.Post(builderURL+"?commit="+commit, "application/json", bytes.NewBuffer([]byte{}))
        
        w.WriteHeader(http.StatusAccepted)
        w.Write([]byte("Build Triggered"))
    })
    log.Println("Receiver listening on :8080")
    log.Fatal(http.ListenAndServe(":8080", nil))
}