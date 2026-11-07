#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
download_target.py - Intelligent APK Downloader for AutoAPK Pipeline.
Handles:
1. Google Drive share links (bypasses HTML preview & virus scan warning pages)
2. Direct HTTP/HTTPS APK download links
3. Automatic fallback to Breeno reference APK if no URL is provided
4. Strict validation (verifies PK zip magic header and size > 1MB)
"""

import sys
import os
import re
import urllib.request
import urllib.parse
import http.cookiejar
import subprocess

DEFAULT_REF_URL = "https://github.com/Hpsctrl/autoApkPipeline/releases/download/v1.0.0/breeno_reference.apk"

def extract_gdrive_id(url: str) -> str:
    """Extracts file ID from various Google Drive URL formats."""
    # Format: /file/d/<id>/view
    m = re.search(r'/file/d/([a-zA-Z0-9_-]+)', url)
    if m:
        return m.group(1)
    # Format: id=<id>
    m = re.search(r'[?&]id=([a-zA-Z0-9_-]+)', url)
    if m:
        return m.group(1)
    return ""

def download_from_gdrive(file_id: str, dest_path: str):
    print(f"[+] Detected Google Drive file ID: {file_id}")
    cookie_jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
    opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')]

    url = f"https://drive.google.com/uc?id={file_id}&export=download"
    print(f"[+] Requesting Google Drive download page: {url}")
    resp = opener.open(url)
    content = resp.read()

    # Check if this is directly the binary or the virus warning HTML form
    if content.startswith(b'PK\x03\x04'):
        print("[+] Direct binary stream received!")
        with open(dest_path, 'wb') as f:
            f.write(content)
            # Read remainder of stream if chunked
            while True:
                chunk = resp.read(1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)
        return

    html = content.decode('utf-8', errors='ignore')
    form_match = re.search(r'<form[^>]*action=\"([^\"]+)\"[^>]*>(.*?)</form>', html, re.DOTALL)
    if form_match:
        action = form_match.group(1)
        inputs = dict(re.findall(r'<input[^>]*name=\"([^\"]+)\"[^>]*value=\"([^\"]*)\"', form_match.group(2)))
        final_url = action + '?' + urllib.parse.urlencode(inputs)
        print(f"[+] Bypassing Google Drive warning screen...")
        resp2 = opener.open(final_url)
        with open(dest_path, 'wb') as f:
            downloaded = 0
            while True:
                chunk = resp2.read(1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                print(f"\r[+] Downloaded: {downloaded / 1024 / 1024:.2f} MB", end='', flush=True)
            print()
    else:
        raise RuntimeError("Failed to resolve Google Drive download form. Ensure file is set to 'Anyone with the link can view'.")

def download_file(url: str, dest_path: str):
    os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
    url = url.strip()

    if not url:
        print("[+] No URL specified. Using reference Breeno Keyboard APK...")
        url = DEFAULT_REF_URL

    if "drive.google.com" in url or "drive.usercontent.google.com" in url:
        file_id = extract_gdrive_id(url)
        if file_id:
            download_from_gdrive(file_id, dest_path)
        else:
            print("[!] Could not extract Google Drive file ID, falling back to curl...")
            subprocess.run(["curl", "-L", url, "-o", dest_path], check=True)
    else:
        print(f"[+] Downloading APK from: {url}")
        subprocess.run(["curl", "-L", url, "-o", dest_path], check=True)

    # Validation
    if not os.path.exists(dest_path):
        raise FileNotFoundError(f"Download failed: {dest_path} not created.")

    size = os.path.getsize(dest_path)
    if size < 1000000:
        with open(dest_path, 'rb') as f:
            head = f.read(200)
        raise ValueError(f"Downloaded file is too small ({size} bytes). Likely an HTML error page:\n{head.decode('utf-8', errors='ignore')[:150]}")

    with open(dest_path, 'rb') as f:
        magic = f.read(4)
    if magic != b'PK\x03\x04':
        raise ValueError(f"Downloaded file does not have a valid APK/ZIP magic header (got {magic!r}).")

    print(f"✅ Successfully downloaded and verified APK: {dest_path} ({size / 1024 / 1024:.2f} MB)")

if __name__ == '__main__':
    target_url = sys.argv[1] if len(sys.argv) > 1 else ""
    out_file = sys.argv[2] if len(sys.argv) > 2 else "input/target.apk"
    download_file(target_url, out_file)
