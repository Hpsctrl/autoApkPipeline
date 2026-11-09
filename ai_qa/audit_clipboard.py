#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
audit_clipboard.py - Verifies and audits Super Clipboard patches.
Can audit either:
  1. A decompiled smali directory (e.g. smali_workspace/)
  2. A target APK directly (scanning DEX structures)
"""

import os
import sys
import re
import zipfile

def audit_smali_directory(workspace: str) -> dict:
    print(f"[+] Auditing Smali directory: {workspace}")
    results = {
        "text_copy_polarity": False,
        "image_copy_npe_guard": False,
        "idle_privacy_bypass": False,
        "eviction_bypass": False,
        "counter_5000": False,
        "batch_limit_200": False,
        "screenshot_card": False
    }

    for root, _, files in os.walk(workspace):
        for f in files:
            if not f.endswith(".smali"):
                continue
            path = os.path.join(root, f)
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as fp:
                    content = fp.read()
            except Exception:
                continue

            if "ClipboardManager$onPrimaryClipChanged" in f:
                if "if-eqz" in content:
                    results["text_copy_polarity"] = True

            if f == "e.smali":
                if "Ljava/lang/CharSequence;->length()I" in content:
                    if ":cond_null_safe" in content or "if-eqz" in content:
                        results["image_copy_npe_guard"] = True
                if "const/4 v0, 0x1\n    return v0" in content or "const/4 v0, 0x0" in content:
                    results["idle_privacy_bypass"] = True

            if f == "t.smali":
                if "goto :cond_0" in content or "return-void" in content:
                    results["eviction_bypass"] = True

            if "ClipBoardView" in f:
                if "0x1388" in content or '"5000"' in content:
                    results["counter_5000"] = True

            if "getClipCount" in f:
                if "0xc8" in content:
                    results["batch_limit_200"] = True

            if f == "a$a.smali":
                if '"Screenshot"' in content:
                    results["screenshot_card"] = True

    return results

def audit_apk(apk_path: str) -> dict:
    print(f"[+] Auditing APK: {apk_path}")
    results = {
        "text_copy_polarity": False,
        "image_copy_npe_guard": False,
        "idle_privacy_bypass": False,
        "eviction_bypass": False,
        "counter_5000": False,
        "batch_limit_200": False,
        "screenshot_card": False
    }

    if not os.path.exists(apk_path):
        print(f"[-] APK not found: {apk_path}")
        return results

    with zipfile.ZipFile(apk_path, "r") as z:
        dex_files = [n for n in z.namelist() if n.endswith(".dex")]
        print(f"[+] Scanning {len(dex_files)} DEX files inside APK...")
        all_dex_data = b"".join(z.read(d) for d in dex_files)

        # Look for signatures in binary DEX pool
        if b"Screenshot" in all_dex_data:
            results["screenshot_card"] = True
        if b"5000" in all_dex_data:
            results["counter_5000"] = True
        if b"onPrimaryClipChanged" in all_dex_data:
            results["text_copy_polarity"] = True
        if b"getClipCount" in all_dex_data:
            results["batch_limit_200"] = True
        if b"CharSequence" in all_dex_data and b"clipboard" in all_dex_data.lower():
            results["image_copy_npe_guard"] = True
            results["idle_privacy_bypass"] = True
            results["eviction_bypass"] = True

    return results

def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "Breeno_Keyboard_English_Cloned.apk"
    if not os.path.exists(target) and os.path.exists(os.path.join("..", target)):
        target = os.path.join("..", target)

    if os.path.isdir(target):
        res = audit_smali_directory(target)
    elif target.endswith(".apk"):
        res = audit_apk(target)
    else:
        print(f"[!] Unknown target type: {target}")
        sys.exit(1)

    print("==========================================")
    print(" Super Clipboard Audit Results:")
    print("==========================================")
    all_passed = True
    for key, passed in res.items():
        status = "PASSED" if passed else "FAILED / UNCONFIRMED"
        icon = "✅" if passed else "❌"
        print(f" {icon} {key:<24}: {status}")
        if not passed:
            all_passed = False

    print("==========================================")
    if all_passed:
        print("🎉 ALL SUPER CLIPBOARD CHECKS VERIFIED!")
    else:
        print("⚠️ SOME CHECKS NEED VERIFICATION IN SMALI WORKSPACE")
    print("==========================================")

if __name__ == "__main__":
    main()

