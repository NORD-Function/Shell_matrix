#!/bin/bash

# Shell Matrix - Quick Installation Script
# Author: Rondinelli Castilho (N0rd)

set -e

echo "================================="
echo "  SHELL MATRIX - Installation"
echo "================================="
echo ""

# Check Python version
echo "[*] Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "[!] Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
REQUIRED_VERSION="3.8"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "[!] Python $PYTHON_VERSION found. Python 3.8 or higher is required."
    exit 1
fi

echo "[+] Python $PYTHON_VERSION found - OK"

# Check pip
echo "[*] Checking pip..."
if ! command -v pip3 &> /dev/null; then
    echo "[!] pip3 is not installed. Installing pip..."
    sudo apt-get update
    sudo apt-get install -y python3-pip
fi
echo "[+] pip found - OK"

# Install dependencies
echo "[*] Installing Python dependencies..."
pip3 install -r requirements.txt

echo ""
echo "[+] Installation completed successfully!"
echo ""
echo "To start Shell Matrix, run:"
echo "  python3 shell_matrix.py"
echo ""
echo "Then open your browser and navigate to:"
echo "  http://localhost:8000"
echo ""
echo "================================="
echo "  Enjoy Shell Matrix! - N0rd"
echo "================================="
