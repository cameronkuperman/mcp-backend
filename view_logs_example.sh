#!/bin/bash
# Example script to view real-time logs when running the Oracle server

echo "Starting Oracle server with detailed logging..."
echo "You'll see report generation progress in real-time!"
echo "=================================================="

# Set logging level to INFO to see all our custom logs
export LOG_LEVEL=INFO

# Run the server and follow logs
# Use grep to filter for report-specific logs if needed
python run_oracle.py 2>&1 | grep -E "(REPORT|GATHER_|LLM|Report)"

# Alternative: View all logs
# python run_oracle.py

# Alternative: Save logs to file
# python run_oracle.py 2>&1 | tee oracle_logs.txt