#!/bin/bash

echo "Starting Oracle API Server..."
echo "Server will be available at: http://localhost:8000"
echo "API docs at: http://localhost:8000/docs"
echo ""

# Use uv to run in the virtual environment
uv run python run_api_server.py