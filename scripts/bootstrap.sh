#!/bin/bash
set -e

echo "=========================================="
echo " AutoAPK Pipeline — Toolchain Bootstrapper"
echo "=========================================="

# 1. System packages
if command -v apt-get >/dev/null 2>&1; then
    echo "[+] Updating apt repositories and installing core packages..."
    sudo apt-get update -qq || true
    sudo apt-get install -y -qq openjdk-17-jdk zipalign aapt wget curl unzip >/dev/null 2>&1 || true
fi

# 2. Setup Android Build Tools (d8, apksigner, zipalign)
echo "[+] Checking Android SDK Build Tools..."
BUILD_TOOLS_PATH=""
CANDIDATE_PATHS=(
    "$ANDROID_HOME/build-tools"
    "$ANDROID_SDK_ROOT/build-tools"
    "/usr/local/lib/android/sdk/build-tools"
    "$HOME/Android/Sdk/build-tools"
    "/opt/android-sdk/build-tools"
)

for p in "${CANDIDATE_PATHS[@]}"; do
    if [ -d "$p" ]; then
        LATEST_DIR=$(ls -1d "$p"/* 2>/dev/null | sort -V | tail -n 1)
        if [ -n "$LATEST_DIR" ] && [ -f "$LATEST_DIR/apksigner" ]; then
            BUILD_TOOLS_PATH="$LATEST_DIR"
            break
        fi
    fi
done

if [ -n "$BUILD_TOOLS_PATH" ]; then
    echo "[+] Found build tools at: $BUILD_TOOLS_PATH"
    sudo ln -sf "$BUILD_TOOLS_PATH/d8" /usr/local/bin/d8 || true
    sudo ln -sf "$BUILD_TOOLS_PATH/apksigner" /usr/local/bin/apksigner || true
    sudo ln -sf "$BUILD_TOOLS_PATH/zipalign" /usr/local/bin/zipalign || true
else
    echo "[!] Android SDK not found in standard paths; checking system packages..."
    if ! command -v apksigner >/dev/null 2>&1 && command -v apt-get >/dev/null 2>&1; then
        sudo apt-get install -y -qq apksigner || true
    fi
fi

# 3. Setup Apktool
if ! command -v apktool >/dev/null 2>&1; then
    echo "[+] Installing Apktool..."
    APKTOOL_VER="2.10.0"
    sudo wget -q "https://github.com/iBotPeaches/Apktool/releases/download/v${APKTOOL_VER}/apktool_${APKTOOL_VER}.jar" -O /usr/local/bin/apktool.jar
    sudo wget -q "https://raw.githubusercontent.com/iBotPeaches/Apktool/master/scripts/linux/apktool" -O /usr/local/bin/apktool
    sudo chmod +x /usr/local/bin/apktool
fi

# 4. Verify toolchain
echo "[+] Verifying toolchain..."
java -version 2>&1 | head -n 1
apktool --version 2>&1 | head -n 1 || echo "Apktool verified"
command -v zipalign >/dev/null && echo "zipalign: $(which zipalign)" || echo "[!] zipalign missing"
command -v apksigner >/dev/null && echo "apksigner: $(which apksigner)" || echo "[!] apksigner missing"

echo "=========================================="
echo " Toolchain Bootstrap Complete"
echo "=========================================="
