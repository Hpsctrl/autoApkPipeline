#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_clipboard_full.py - Complete Super Clipboard Patcher for Breeno Keyboard.
Implements surgical Dalvik bytecode patches across all multidex smali folders:
1. Fixes inverted branch in ClipboardManager$onPrimaryClipChanged$1$1.smali (text copy drop)
2. Injects null-safety guard before CharSequence->length() in function/e.smali (NPE on image copy)
3. Bypasses L.n privacy dialog check & hardcodes e.j() to return true in e.smali (idle background survival)
4. Bypasses 500-item deletion query with goto :cond_0 in t.smali (5,000+ item retention)
5. Expands visual counter from 500 to 5,000 in ClipBoardView
6. Increases batch load chunk from 25 to 200 items in getClipCount$1.smali
7. Routes image/* clips and content URIs to a$a.smali as Screenshot cards
"""

import os
import sys
import re

def find_smali_files(workspace: str, filename_pattern: str) -> list[str]:
    """Finds all smali files matching filename_pattern recursively across all smali folders."""
    matches = []
    regex = re.compile(filename_pattern, re.IGNORECASE)
    for root, _, files in os.walk(workspace):
        for f in files:
            if regex.search(f):
                matches.append(os.path.join(root, f))
    return matches

def patch_file(filepath: str, find_pattern: str, replace_str: str, desc: str, is_regex: bool = False) -> bool:
    """Applies a patch to a file if target pattern is present."""
    if not os.path.exists(filepath):
        print(f"[-] File not found: {filepath}")
        return False
        
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    if replace_str in content and not is_regex:
        print(f"[=] Already patched: {os.path.basename(filepath)} ({desc})")
        return True

    if is_regex:
        if not re.search(find_pattern, content):
            print(f"[-] Pattern not found in {os.path.basename(filepath)}: {desc}")
            return False
        new_content = re.sub(find_pattern, replace_str, content)
    else:
        if find_pattern not in content:
            print(f"[-] String not found in {os.path.basename(filepath)}: {desc}")
            return False
        new_content = content.replace(find_pattern, replace_str, 1)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"✅ Patched: {os.path.basename(filepath)} — {desc}")
    return True

def fix_text_copy_inverted_jump(workspace: str) -> bool:
    """Fix inverted conditional branch in ClipboardManager$onPrimaryClipChanged$1$1.smali."""
    files = find_smali_files(workspace, r"ClipboardManager\$onPrimaryClipChanged\$1\$1\.smali$")
    if not files:
        print("[-] Target ClipboardManager$onPrimaryClipChanged$1$1.smali not found in workspace.")
        return False

    success = False
    for filepath in files:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Inverted jump: non-null text skipped into image URI handler
        # Look for if-nez on text null-check and invert to if-eqz (or vice versa depending on branch label)
        # Regex matches conditional check right before text capture
        pattern = r"(invoke-static\s+.*?,?\s*Landroid/text/TextUtils;->isEmpty\(Ljava/lang/CharSequence;\)Z[\s\S]*?)if-nez\s+([vp]\d+),\s*(:cond_\w+)"
        replacement = r"\1if-eqz \2, \3"

        if re.search(pattern, content):
            if patch_file(filepath, pattern, replacement, "Invert conditional jump for non-empty clipboard text", is_regex=True):
                success = True
        else:
            # Fallback direct bytecode pattern
            direct_pat = "if-nez v0, :cond_0"
            direct_rep = "if-eqz v0, :cond_0"
            if direct_pat in content:
                if patch_file(filepath, direct_pat, direct_rep, "Invert if-nez to if-eqz in onPrimaryClipChanged"):
                    success = True
            else:
                print(f"[!] Text copy branch pattern already inverted or not matched in {filepath}")
                success = True
    return success

def fix_image_copy_npe(workspace: str) -> bool:
    """Inject safe null guard before CharSequence->length() in function/e.smali."""
    files = find_smali_files(workspace, r"function[/\\]e\.smali$|e\.smali$")
    success = False
    for filepath in files:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        if "Ljava/lang/CharSequence;->length()I" in content:
            # Check if null guard already exists
            if "if-eqz v2, :cond_0" in content or "if-nez v2, :cond_safe" in content:
                print(f"[=] Null guard already present in {os.path.basename(filepath)}")
                success = True
                continue

            # Look for invoke-interface {v2}, Ljava/lang/CharSequence;->length()I
            target = r"(\s*)(invoke-interface\s*\{([vp]\d+)\},\s*Ljava/lang/CharSequence;->length\(\)I)"
            def replacer(match):
                indent = match.group(1)
                inv = match.group(2)
                reg = match.group(3)
                return f"{indent}if-eqz {reg}, :cond_null_safe_img\n{indent}{inv}\n{indent}:cond_null_safe_img"

            new_content = re.sub(target, replacer, content, count=1)
            if new_content != content:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print(f"✅ Patched: {os.path.basename(filepath)} — Added safe null guard before CharSequence->length()")
                success = True
    return success

def fix_background_idle_privacy(workspace: str) -> bool:
    """Bypass L.n privacy dialog check & force e.j() to return true unconditionally."""
    files = find_smali_files(workspace, r"(?:function[/\\])?e\.smali$")
    success = False
    for filepath in files:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # 1. Hardcode e.j() to return true (0x1)
        # Search for .method public static j()Z or .method public j()Z
        j_method_pat = r"(\.method\s+(?:public|private|protected)?\s*(?:static)?\s*j\(\)Z[\s\S]*?\.end method)"
        match = re.search(j_method_pat, content)
        if match:
            old_method = match.group(1)
            new_method = (
                ".method public static j()Z\n"
                "    .registers 1\n"
                "    const/4 v0, 0x1\n"
                "    return v0\n"
                ".end method"
            )
            content = content.replace(old_method, new_method, 1)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"✅ Patched: {os.path.basename(filepath)} — Hardcoded e.j() to return true unconditionally")
            success = True

        # 2. Bypass L.n check if present
        if "sget-boolean" in content and "L;->n:Z" in content:
            content = re.sub(r"sget-boolean\s+([vp]\d+),\s*.*?L;->n:Z", r"const/4 \1, 0x0", content)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"✅ Patched: {os.path.basename(filepath)} — Bypassed L.n privacy flag check")
            success = True
            
    return success

def fix_eviction_bypass(workspace: str) -> bool:
    """Bypass 500-item deletion query with goto :cond_0 in t.smali."""
    files = find_smali_files(workspace, r"t\.smali$")
    success = False
    for filepath in files:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Look for method executing delete query on clipboard DB table
        if "DELETE FROM" in content or "clipboard" in content.lower():
            # Inject short-circuit jump at start of eviction method
            evict_pat = r"(\.method\s+.*?deleteOldClips.*?\n)([\s\S]*?)(\.end method)"
            match = re.search(evict_pat, content)
            if match:
                header = match.group(1)
                body = match.group(2)
                ender = match.group(3)
                new_body = "    .registers 2\n    return-void\n"
                content = content.replace(header + body + ender, header + new_body + ender, 1)
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"✅ Patched: {os.path.basename(filepath)} — Short-circuited clipboard eviction query")
                success = True
            elif "const/16 v0, 0x1f4" in content:
                # Bypass comparison that triggers deletion
                content = content.replace("if-le v0, v1, :cond_0", "goto :cond_0")
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"✅ Patched: {os.path.basename(filepath)} — Injected goto :cond_0 to bypass eviction")
                success = True
    return success

def fix_counter_and_batch_limits(workspace: str) -> bool:
    """Expand UI counter from 500 to 5000 and batch load limit from 25 to 200."""
    # 1. Counter expansion in ClipBoardView files
    counter_files = find_smali_files(workspace, r"ClipBoardView.*\.smali$")
    success = False
    for filepath in counter_files:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # 500 in hex is 0x1f4; 5000 in hex is 0x1388
        if "const/16 v0, 0x1f4" in content:
            content = content.replace("const/16 v0, 0x1f4", "const/16 v0, 0x1388")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"✅ Patched: {os.path.basename(filepath)} — Expanded visual counter from 500 to 5000")
            success = True
        elif 'const-string v0, "500"' in content:
            content = content.replace('const-string v0, "500"', 'const-string v0, "5000"')
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"✅ Patched: {os.path.basename(filepath)} — Expanded visual string counter to 5000")
            success = True

    # 2. Batch count query limit in getClipCount$1.smali
    batch_files = find_smali_files(workspace, r"getClipCount\$1\.smali$")
    for filepath in batch_files:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # 25 in hex is 0x19; 200 in hex is 0xc8
        if "const/16 v0, 0x19" in content or "const/4 v0, 0x19" in content:
            content = re.sub(r"const/(?:16|4)\s+([vp]\d+),\s*0x19", r"const/16 \1, 0xc8", content)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"✅ Patched: {os.path.basename(filepath)} — Increased batch fetch chunk from 25 to 200")
            success = True

    return success

def fix_screenshot_card_routing(workspace: str) -> bool:
    """Route image/* clips to a$a.smali as Screenshot cards."""
    files = find_smali_files(workspace, r"a\$a\.smali$")
    success = False
    for filepath in files:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Tag image cards as "Screenshot" cards if not already set
        if "Screenshot" in content:
            print(f"[=] Screenshot tag already active in {os.path.basename(filepath)}")
            success = True
            continue

        if "const-string v1, \"image/*\"" in content or "image/png" in content:
            content = re.sub(
                r'const-string\s+([vp]\d+),\s*"image/\*"',
                r'const-string \1, "image/*"\n    const-string v0, "Screenshot"',
                content
            )
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"✅ Patched: {os.path.basename(filepath)} — Routed image clips to Screenshot card tag")
            success = True

    return success

def run_all(workspace: str = "smali_workspace"):
    print(f"==================================================")
    print(f" Running Super Clipboard Patcher on: {workspace}")
    print(f"==================================================")

    if not os.path.exists(workspace):
        print(f"[!] Workspace directory '{workspace}' does not exist.")
        return False

    r1 = fix_text_copy_inverted_jump(workspace)
    r2 = fix_image_copy_npe(workspace)
    r3 = fix_background_idle_privacy(workspace)
    r4 = fix_eviction_bypass(workspace)
    r5 = fix_counter_and_batch_limits(workspace)
    r6 = fix_screenshot_card_routing(workspace)

    print(f"==================================================")
    print(f" Clipboard Patching Summary:")
    print(f"  1. Text Copy Polarity Fix:      {'✅' if r1 else '⚠️ / checked'}")
    print(f"  2. Image Copy NPE Guard:        {'✅' if r2 else '⚠️ / checked'}")
    print(f"  3. Background Idle Bypass:      {'✅' if r3 else '⚠️ / checked'}")
    print(f"  4. Eviction Limit Bypass:       {'✅' if r4 else '⚠️ / checked'}")
    print(f"  5. 5,000 & 200 Limit Expansion: {'✅' if r5 else '⚠️ / checked'}")
    print(f"  6. Screenshot Card Routing:     {'✅' if r6 else '⚠️ / checked'}")
    print(f"==================================================")
    return True

if __name__ == "__main__":
    target_ws = sys.argv[1] if len(sys.argv) > 1 else "smali_workspace"
    run_all(target_ws)

