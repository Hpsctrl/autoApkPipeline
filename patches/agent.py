#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agent.py - Autonomous AI Reverse Engineering Agent for AutoAPK Pipeline.
Interprets plain-English user instructions, inspects decompiled APK assets,
and generates a surgical, deterministic patch plan via Gemini API.
"""

import os
import sys
import json
import re
import subprocess
import time
import urllib.request
import urllib.parse
import urllib.error

WORKSPACE = "smali_workspace"
INPUT_APK = "input/target.apk"
PLAN_FILE = "patch_plan.json"

def decompile_apk():
    os.makedirs("input", exist_ok=True)
    target = None
    if os.path.exists(INPUT_APK) and os.path.getsize(INPUT_APK) > 1000000:
        target = INPUT_APK
    else:
        cands = [os.path.join("input", f) for f in os.listdir("input") if f.endswith(".apk") and os.path.getsize(os.path.join("input", f)) > 1000000]
        if cands:
            target = cands[0]
        else:
            print("[+] Downloading default Breeno Keyboard reference APK via curl...")
            target = INPUT_APK
            ref_url = "https://github.com/Hpsctrl/autoApkPipeline/releases/download/v1.0.0/breeno_reference.apk"
            subprocess.run(["curl", "-L", "-s", ref_url, "-o", target], check=False)

    if not os.path.exists(target) or os.path.getsize(target) < 1000000:
        print(f"[!] Error: Target APK '{target}' is missing or corrupted (< 1MB)!")
        sys.exit(1)

    print(f"[+] Decompiling {target} ({os.path.getsize(target) / 1024 / 1024:.1f} MB) into {WORKSPACE}...")
    subprocess.run(["apktool", "d", target, "-o", WORKSPACE, "-f"], check=True)
    print(f"✅ Decompiled into {WORKSPACE}")

def scan_codebase_context(user_instruction: str) -> dict:
    """Find relevant classes and smali files matching keywords in instruction."""
    keywords = re.findall(r'[a-zA-Z]{3,}', user_instruction.lower())
    matches = []
    
    for root, _, files in os.walk(WORKSPACE):
        for f in files:
            if f.endswith(".smali"):
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, WORKSPACE)
                name_lower = f.lower()
                
                # Check file name matches
                score = sum(1 for kw in keywords if kw in name_lower)
                if score > 0:
                    matches.append((score, rel_path))

    matches.sort(key=lambda x: x[0], reverse=True)
    top_files = [m[1] for m in matches[:15]]
    return {"top_relevant_files": top_files}

def call_gemini_for_plan(instruction: str, context: dict, api_key: str) -> dict:
    print(f"[+] Calling Gemini AI to generate patch plan for: '{instruction}'")
    
    system_prompt = (
        "You are an elite Android reverse engineer and Dalvik Smali patching expert. "
        "Analyze the user's natural language instruction and the decompiled APK context. "
        "Output ONLY a valid JSON object describing the exact patches to apply. "
        "Do NOT include Markdown fences (```json), commentary, or explanations."
    )
    
    prompt = f"""User Instruction: {instruction}
Decompiled context: {json.dumps(context)}

Expected JSON schema:
{{
  "package_clone": {{
    "enabled": true,
    "suffix": ".en"
  }},
  "arsc_strings": [
    {{"find": "New line", "replace": "Enter"}},
    {{"find": "换行", "replace": "Enter"}}
  ],
  "smali_patches": [
    {{
      "file": "smali/com/oplus/keyboard/input/view/body/r.smali",
      "find": "const-string/jumbo v6, \\"EN\\"",
      "replace": "const-string/jumbo v6, \\".\\"",
      "description": "Replace EN key with dot period key"
    }}
  ],
  "injections": {{
    "giphy_search": true,
    "voice_timeout_seconds": 120
  }}
}}
"""

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": system_prompt + "\n\n" + prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json"
        }
    }
    
    models = ["gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-2.5-flash"]
    for model_name in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    resp_json = json.loads(resp.read().decode("utf-8"))
                    text = resp_json["candidates"][0]["content"]["parts"][0]["text"].strip()
                    # Clean out markdown fences if any
                    text = re.sub(r'^```json\s*', '', text)
                    text = re.sub(r'\s*```$', '', text)
                    plan = json.loads(text)
                    print(f"✅ Generated patch plan via {model_name}")
                    return plan
            except urllib.error.HTTPError as e:
                print(f"[!] {model_name} HTTP {e.code}: {e.read().decode('utf-8', errors='ignore')}")
                if e.code == 429:
                    time.sleep(5 * (attempt + 1))
                else:
                    break
            except Exception as e:
                print(f"[!] Error calling {model_name}: {e}")
                time.sleep(3)

    print("[!] Warning: All Gemini API attempts failed. Falling back to default plan.")
    return get_default_plan()

def get_default_plan() -> dict:
    return {
        "package_clone": {"enabled": True, "suffix": ".en"},
        "arsc_strings": [
            {"find": "New line", "replace": "Enter"},
            {"find": "换行", "replace": "Enter"}
        ],
        "smali_patches": [
            {
                "file": "smali/com/oplus/keyboard/input/view/body/r.smali",
                "find": "const-string/jumbo v6, \"EN\"",
                "replace": "const-string/jumbo v6, \".\"",
                "description": "Replace EN key with dot period key"
            }
        ],
        "injections": {
            "giphy_search": True,
            "voice_timeout_seconds": 120
        }
    }

def main():
    instruction = os.environ.get("USER_INSTRUCTION", "").strip()
    if not instruction:
        if os.path.exists("config.json"):
            with open("config.json", "r") as f:
                cfg = json.load(f)
                instruction = cfg.get("default_instruction", "Localize to English, fix Chinese strings, add dot key and enable live search")
        else:
            instruction = "Localize to English, fix Chinese strings, add dot key and enable live search"

    print(f"==========================================")
    print(f" AutoAPK Agent Starting")
    print(f" User Instruction: {instruction}")
    print(f"==========================================")

    # 1. Decompile
    if not os.path.exists(WORKSPACE):
        decompile_apk()

    # 2. Context scan
    context = scan_codebase_context(instruction)

    # 3. Plan generation
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if api_key:
        plan = call_gemini_for_plan(instruction, context, api_key)
    else:
        print("[!] No GEMINI_API_KEY found, using default patch plan.")
        plan = get_default_plan()

    with open(PLAN_FILE, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2)
    print(f"✅ Saved patch plan to {PLAN_FILE}")

    # 4. Execute Smali patches
    subprocess.run([sys.executable, "patches/smali_patcher.py", WORKSPACE, PLAN_FILE], check=False)

    # 5. Localize ARSC strings
    arsc_path = os.path.join(WORKSPACE, "resources.arsc")
    if os.path.exists(arsc_path):
        print("[+] Running binary ARSC localizer...")
        subprocess.run([sys.executable, "patches/arsc_localizer.py", arsc_path, "-o", arsc_path], check=False)

    # 6. Clone manifest package identifier
    manifest_path = os.path.join(WORKSPACE, "AndroidManifest.xml")
    if os.path.exists(manifest_path) and plan.get("package_clone", {}).get("enabled", True):
        print("[+] Running manifest cloner...")
        # If manifest is text XML (standard apktool):
        try:
            with open(manifest_path, "r", encoding="utf-8", errors="ignore") as f:
                m_content = f.read()
            if "<manifest" in m_content:
                # Text manifest
                suffix = plan.get("package_clone", {}).get("suffix", ".en")
                m_content = re.sub(r'package="([^"]+)"', rf'package="\1{suffix}"', m_content)
                with open(manifest_path, "w", encoding="utf-8") as f:
                    f.write(m_content)
                print(f"✅ Appended {suffix} to package attribute in AndroidManifest.xml")
        except Exception as e:
            print(f"[!] Warning updating manifest: {e}")

    print(f"==========================================")
    print(f" AutoAPK Agent Patching Complete")
    print(f"==========================================")

if __name__ == "__main__":
    main()
