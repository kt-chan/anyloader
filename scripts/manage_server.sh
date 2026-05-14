#!/bin/bash

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="$PROJECT_ROOT/storage/server.pid"
LOG_FILE="$PROJECT_ROOT/storage/server.log"

start_server() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null; then
            echo "Server is already running (PID: $PID)"
            return
        else
            rm "$PID_FILE"
        fi
    fi

    echo "Starting anyLoader server..."
    cd "$PROJECT_ROOT"
    
    # Load environment variables if .env exists
    if [ -f ".env" ]; then
        export $(grep -v '^#' .env | xargs)
    fi

    # Run uvicorn in background
    mkdir -p storage
    nohup python3 -m uvicorn src.server.main:app --host 0.0.0.0 --port ${RAG_PORT:-8000} > "$LOG_FILE" 2>&1 &
    
    NEW_PID=$!
    echo $NEW_PID > "$PID_FILE"
    echo "Server started with PID: $NEW_PID"
    echo "Logs are being written to: $LOG_FILE"
}

stop_server() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        echo "Stopping server (PID: $PID)..."
        kill $PID
        rm "$PID_FILE"
        echo "Server stopped."
    else
        echo "Server is not running (no PID file found)."
    fi
}

status_server() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null; then
            echo "Server is running (PID: $PID)"
        else
            echo "PID file exists but process is not running."
        fi
    else
        echo "Server is not running."
    fi
}

case "$1" in
    start)
        start_server
        ;;
    stop)
        stop_server
        ;;
    restart)
        stop_server
        sleep 2
        start_server
        ;;
    status)
        status_server
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
esac
