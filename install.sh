#!/usr/bin/env bash
set -euo pipefail

REPO="amaryange/spring-obs-starter"
BINARY="sos"
INSTALL_DIR="/usr/local/bin"

# ── Detect OS + arch ────────────────────────────────────────────────────────
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)

case "$OS" in
  linux)  PLATFORM="linux" ;;
  darwin) PLATFORM="macos" ;;
  *)
    echo "❌  Unsupported OS: $OS"
    echo "    Download manually from https://github.com/$REPO/releases"
    exit 1
    ;;
esac

case "$ARCH" in
  x86_64 | amd64) ARCH_SUFFIX="x86_64" ;;
  arm64  | aarch64) ARCH_SUFFIX="arm64" ;;
  *)
    echo "❌  Unsupported architecture: $ARCH"
    exit 1
    ;;
esac

ASSET_NAME="${BINARY}-${PLATFORM}-${ARCH_SUFFIX}"

# ── Resolve latest release ───────────────────────────────────────────────────
echo "🔍  Fetching latest release..."
LATEST=$(curl -fsSL "https://api.github.com/repos/$REPO/releases/latest" \
  | grep '"tag_name"' | head -1 | cut -d'"' -f4)

if [[ -z "$LATEST" ]]; then
  echo "❌  Could not fetch release info. Check your internet connection."
  exit 1
fi

DOWNLOAD_URL="https://github.com/$REPO/releases/download/$LATEST/$ASSET_NAME"

# ── Download ─────────────────────────────────────────────────────────────────
TMP=$(mktemp)
echo "⬇️   Downloading sos $LATEST ($PLATFORM/$ARCH_SUFFIX)..."
curl -fsSL "$DOWNLOAD_URL" -o "$TMP"
chmod +x "$TMP"

# ── Install ───────────────────────────────────────────────────────────────────
if [[ -w "$INSTALL_DIR" ]]; then
  mv "$TMP" "$INSTALL_DIR/$BINARY"
else
  echo "🔒  $INSTALL_DIR requires sudo..."
  sudo mv "$TMP" "$INSTALL_DIR/$BINARY"
fi

# ── Verify ────────────────────────────────────────────────────────────────────
echo ""
echo "✅  sos installed → $(which sos)"
echo ""
sos
