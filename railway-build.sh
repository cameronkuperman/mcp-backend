#!/bin/bash
# Railway build script to ensure pip is available

echo "Railway build script starting..."

# Ensure pip is installed
python -m ensurepip --upgrade || echo "ensurepip failed, trying alternative..."

# Alternative: download get-pip.py if ensurepip fails
if ! python -m pip --version; then
    echo "Downloading get-pip.py..."
    curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
    python get-pip.py
    rm get-pip.py
fi

# Upgrade pip
python -m pip install --upgrade pip

# Install requirements
python -m pip install -r requirements.txt

echo "Build completed successfully!"