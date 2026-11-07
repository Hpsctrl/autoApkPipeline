#!/bin/bash
set -e

echo "=========================================="
echo " AutoAPK Pipeline — Rebuild, Align & Sign"
echo "=========================================="

WORKSPACE="${1:-smali_workspace}"
OUTPUT_DIR="output"
KEYSTORE="release.keystore"
mkdir -p "$OUTPUT_DIR"

if [ ! -d "$WORKSPACE" ]; then
    echo "[!] Workspace '$WORKSPACE' not found!"
    exit 1
fi

# 1. Ensure signing keystore
if [ ! -f "$KEYSTORE" ]; then
    echo "[+] Generating release signing keystore..."
    bash scripts/generate_keystore.sh "$KEYSTORE" "autokey" "android"
fi

# 2. Compile Smali & Resources with Apktool
echo "[+] Assembling APK from $WORKSPACE..."
apktool b "$WORKSPACE" -o "$OUTPUT_DIR/unsigned.apk"

# 3. 4-Byte Zip Alignment
echo "[+] Aligning APK archive..."
if command -v zipalign >/dev/null 2>&1; then
    zipalign -p -f 4 "$OUTPUT_DIR/unsigned.apk" "$OUTPUT_DIR/aligned.apk"
else
    echo "[!] zipalign not found, using unsigned APK directly"
    cp "$OUTPUT_DIR/unsigned.apk" "$OUTPUT_DIR/aligned.apk"
fi

# 4. Release Signing (v1 + v2 + v3)
FINAL_APK="$OUTPUT_DIR/AutoAPK_Patched.apk"
echo "[+] Signing APK with release key..."
if command -v apksigner >/dev/null 2>&1; then
    apksigner sign \
        --ks "$KEYSTORE" \
        --ks-pass "pass:android" \
        --key-pass "pass:android" \
        --ks-key-alias "autokey" \
        --v1-signing-enabled true \
        --v2-signing-enabled true \
        --v3-signing-enabled true \
        --out "$FINAL_APK" \
        "$OUTPUT_DIR/aligned.apk"

    echo "[+] Verifying APK signature..."
    apksigner verify -v "$FINAL_APK" | head -n 10
else
    echo "[!] apksigner not found, falling back to jarsigner..."
    jarsigner -verbose -sigalg SHA256withRSA -digestalg SHA-256 \
        -keystore "$KEYSTORE" \
        -storepass "android" \
        "$OUTPUT_DIR/aligned.apk" autokey
    mv "$OUTPUT_DIR/aligned.apk" "$FINAL_APK"
fi

# Remove temporary intermediates
rm -f "$OUTPUT_DIR/unsigned.apk" "$OUTPUT_DIR/aligned.apk"

echo "=========================================="
echo "✅ Finished APK Built: $FINAL_APK"
ls -lh "$FINAL_APK"
echo "=========================================="
