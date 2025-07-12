#!/bin/bash
set -e

echo "=== Railway Python Package Installation ==="
echo "Python version:"
python --version

# Method 1: Try ensurepip
echo "Attempting ensurepip..."
python -m ensurepip --upgrade 2>/dev/null || {
    echo "ensurepip failed, trying get-pip.py..."
    # Method 2: Download get-pip.py
    curl -sSL https://bootstrap.pypa.io/get-pip.py -o get-pip.py
    python get-pip.py
    rm get-pip.py
}

# Verify pip is installed
echo "Pip version:"
python -m pip --version

# Upgrade pip
echo "Upgrading pip..."
python -m pip install --upgrade pip

# Install requirements
echo "Installing requirements..."
python -m pip install -r requirements.txt

echo "=== Installation Complete ==="
python -m pip list | head -20