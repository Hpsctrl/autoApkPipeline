#!/bin/bash
set -e

KEYSTORE="${1:-release.keystore}"
ALIAS="${2:-autokey}"
PASSWORD="${3:-android}"

if [ -f "$KEYSTORE" ]; then
    echo "Keystore already exists at: $KEYSTORE"
    exit 0
fi

echo "Generating release signing keystore..."
keytool -genkeypair -v \
    -keystore "$KEYSTORE" \
    -alias "$ALIAS" \
    -keyalg RSA \
    -keysize 2048 \
    -validity 10000 \
    -storepass "$PASSWORD" \
    -keypass "$PASSWORD" \
    -dname "CN=AutoAPK, OU=Mobile, O=AutoAPK Pipeline, L=Global, S=Global, C=US"

echo "✅ Generated keystore: $KEYSTORE (alias: $ALIAS)"
