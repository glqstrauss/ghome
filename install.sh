#!/bin/bash
set -e

REPO_URL="https://github.com/glqstrauss/ghome"
MATRIX_REPO="https://github.com/hzeller/rpi-rgb-led-matrix"

# --- uv ---
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

# --- ghome repo ---
if [ ! -d "$HOME/ghome" ]; then
    echo "Cloning ghome..."
    git clone "$REPO_URL" "$HOME/ghome"
else
    echo "Updating ghome..."
    git -C "$HOME/ghome" pull
fi

# --- rgbmatrix dependencies ---
echo "Installing rgbmatrix build dependencies..."
sudo apt-get update -qq
sudo apt-get install -y python3-dev cython3

# --- rgbmatrix: sparse checkout of bindings/python only ---
MATRIX_DIR="$HOME/rpi-rgb-led-matrix"
if [ ! -d "$MATRIX_DIR" ]; then
    echo "Sparse-cloning rpi-rgb-led-matrix (bindings/python only)..."
    git clone --filter=blob:none --no-checkout "$MATRIX_REPO" "$MATRIX_DIR"
    git -C "$MATRIX_DIR" sparse-checkout set bindings/python lib include
    git -C "$MATRIX_DIR" checkout
else
    echo "Updating rpi-rgb-led-matrix..."
    git -C "$MATRIX_DIR" pull
fi

# --- build and install rgbmatrix into ghome venv ---
echo "Building and installing rgbmatrix Python bindings..."
cd "$HOME/ghome"
uv pip install "$MATRIX_DIR"

# --- sync ghome deps ---
echo "Syncing ghome dependencies..."
cd "$HOME/ghome"
uv sync

echo ""
echo "Done. Run with: cd ~/ghome && sudo uv run src/ghome/display/__init__.py"
