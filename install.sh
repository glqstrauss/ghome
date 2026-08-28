#!/bin/bash
set -e

REPO_URL="https://github.com/glqstrauss/ghome"
MATRIX_REPO="https://github.com/hzeller/rpi-rgb-led-matrix"

# --- swap (compilation needs more RAM than the Pi has by default) ---
if [ ! -f /swapfile ]; then
    echo "Creating 1GB swapfile..."
    sudo fallocate -l 1G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
fi

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

# --- rgbmatrix build dependencies ---
echo "Installing rgbmatrix build dependencies..."
sudo apt-get update -qq
sudo apt-get install -y python3-dev cython3

# --- rgbmatrix: sparse checkout ---
MATRIX_DIR="$HOME/rpi-rgb-led-matrix"
if [ ! -d "$MATRIX_DIR" ]; then
    echo "Cloning rpi-rgb-led-matrix..."
    git clone "$MATRIX_REPO" "$MATRIX_DIR"
else
    echo "Updating rpi-rgb-led-matrix..."
    git -C "$MATRIX_DIR" pull
fi

# --- Pillow internal header workaround (github.com/hzeller/rpi-rgb-led-matrix/issues/1869) ---
# The build requires Pillow's internal C headers which aren't shipped in modern wheels.
PILLOW_VERSION=$(grep -A2 'name = "pillow"' "$HOME/ghome/uv.lock" | grep version | awk -F'"' '{print $2}')
SHIMS="$MATRIX_DIR/bindings/python/rgbmatrix/shims"
PILLOW_BASE="https://raw.githubusercontent.com/python-pillow/Pillow/$PILLOW_VERSION/src/libImaging"
echo "Fetching Pillow $PILLOW_VERSION internal headers..."
for header in Arrow.h Bcn.h Bit.h Convert.h Gif.h ImDib.h ImPlatform.h Imaging.h \
              ImagingUtils.h Jpeg.h Jpeg2K.h Mode.h QuantHash.h QuantHeap.h \
              QuantOctree.h QuantPngQuant.h QuantTypes.h Raw.h Sgi.h TiffDecode.h \
              ZipCodecs.h; do
    curl -LsSf -o "$SHIMS/$header" "$PILLOW_BASE/$header"
done

# --- sync all deps including rgbmatrix (builds from source, takes a few minutes first run) ---
echo "Syncing ghome dependencies..."
cd "$HOME/ghome"
uv sync --group pi --no-group dev

echo ""
echo "Done. Run with: cd ~/ghome && sudo uv run src/ghome/display/__init__.py"
