#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
smali_patcher.py - Rule-based Dalvik Smali bytecode patcher.
Executes declarative patch rules from patch_plan.json or patch_rules/*.json.
"""

import os
import sys
import json
import re

def apply_patch(workspace: str, patch: dict) -> bool:
    target_rel = patch.get("file")
    if not target_rel:
        print(f"[-] Invalid patch item: missing 'file'")
        return False

    target_path = os.path.join(workspace, target_rel)
    if not os.path.exists(target_path):
        # Check alternative classes directories (e.g. smali_classes2, smali_classes3, etc.)
        base_name = target_rel.replace("smali/", "")
        alt_found = None
        for cand in os.listdir(workspace):
            if cand.startswith("smali") and os.path.isdir(os.path.join(workspace, cand)):
                alt = os.path.join(workspace, cand, base_name)
                if os.path.exists(alt):
                    alt_found = alt
                    break
        if alt_found:
            target_path = alt_found
        else:
            print(f"[-] Target file not found: {target_rel}")
            return False

    with open(target_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    find_str = patch.get("find", "")
    replace_str = patch.get("replace", "")
    is_regex = patch.get("regex", False)
    desc = patch.get("description", "Smali patch")

    if not find_str:
        print(f"[-] No 'find' target provided for {desc}")
        return False

    if is_regex:
        if not re.search(find_str, content):
            print(f"[-] Pattern not found in {target_rel}: {find_str}")
            return False
        new_content = re.sub(find_str, replace_str, content)
    else:
        if find_str not in content:
            print(f"[-] String not found in {target_rel}: {find_str[:60]}")
            return False
        new_content = content.replace(find_str, replace_str, 1)

    with open(target_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"✅ Patched: {target_rel} — {desc}")
    return True

def run(workspace: str = "smali_workspace", plan_path: str = "patch_plan.json"):
    patches = []

    if os.path.exists(plan_path):
        try:
            with open(plan_path, "r", encoding="utf-8") as f:
                plan = json.load(f)
            patches.extend(plan.get("smali_patches", []))
        except Exception as e:
            print(f"[!] Error loading {plan_path}: {e}")
    else:
        print(f"[!] Patch plan '{plan_path}' not found.")

    # Also automatically discover and load modular rules from patch_rules/
    script_dir = os.path.dirname(os.path.abspath(__file__))
    rules_dir = os.path.join(script_dir, "patch_rules")
    if os.path.exists(rules_dir):
        for rf in os.listdir(rules_dir):
            if rf.endswith(".json"):
                rf_path = os.path.join(rules_dir, rf)
                try:
                    with open(rf_path, "r", encoding="utf-8") as f:
                        rdata = json.load(f)
                    if isinstance(rdata, dict):
                        if "smali_patches" in rdata and isinstance(rdata["smali_patches"], list):
                            patches.extend(rdata["smali_patches"])
                        elif "file" in rdata and "find" in rdata:
                            patches.append(rdata)
                except Exception as e:
                    print(f"[!] Error loading rule {rf}: {e}")

    if not patches:
        print("[!] No smali patches to apply.")
        return

    print(f"[+] Applying {len(patches)} smali bytecode patches...")

    success = 0
    for p in patches:
        if apply_patch(workspace, p):
            success += 1

    print(f"[+] Applied {success}/{len(patches)} smali patches.")

if __name__ == "__main__":
    ws = sys.argv[1] if len(sys.argv) > 1 else "smali_workspace"
    plan = sys.argv[2] if len(sys.argv) > 2 else "patch_plan.json"
    run(ws, plan)
