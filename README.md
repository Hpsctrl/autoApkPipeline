# 🚀 AutoAPK Pipeline

> **Autonomous Cloud APK Re-Engineering & Vision-QA Pipeline**  
> Powered by GitHub Actions, Android KVM Virtualization, and Gemini Vision.

---

## ⚡ Quick Start (Two Ways to Run)

### Method 1: 1-Click Cloud Automation (GitHub Actions)
1. Go to the [**Actions**](https://github.com/Hpsctrl/autoApkPipeline/actions) tab.
2. Select **AutoAPK Pipeline** → click **Run workflow**.
3. Type what you want to change in plain English (e.g., *"Replace Chinese ENG key with dot key, fix voice timeout, enable live Giphy search"*).
4. Click **Run workflow** and walk away.
5. In ~10 minutes, the finished, signed APK and HTML Visual QA Report will be automatically published under [**Releases**](https://github.com/Hpsctrl/autoApkPipeline/releases).

*Alternative:* You can also trigger a build simply by opening a new [**GitHub Issue**](https://github.com/Hpsctrl/autoApkPipeline/issues) with your instruction! The AI will automatically build the APK and reply to your issue with the download link.

---

### Method 2: Google Colab (Interactive Notebook)
Open [`AutoAPK_Pipeline.ipynb`](https://github.com/Hpsctrl/autoApkPipeline/blob/main/AutoAPK_Pipeline.ipynb) directly in Google Colab:

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Hpsctrl/autoApkPipeline/blob/main/AutoAPK_Pipeline.ipynb)

1. Open the notebook in Colab.
2. Click **Runtime** → **Run All**.
3. The APK will be built, tested, and downloaded straight to your browser.

---

## 🏗️ Architecture & Features

```
User Instruction (Plain English)
               ↓
   GitHub Actions (KVM Cloud Runner)
               ↓
  AI Agent (Gemini 2.5 Flash Planning)
               ↓
  Surgical Bytecode & Resource Patching
               ↓
    Apktool Rebuild + 4-Byte ZipAlign
               ↓
  Release Signing (v1 + v2 + v3 Schemes)
               ↓
  Real-Time Vision QA (Gemini Vision)
               ↓
  Automated GitHub Release with APK & Report
```

- **Surgical Smali Patching:** Deterministic instruction replacements without breaking method signatures.
- **Binary ARSC String Pool Localizer:** Rewrites CJK strings directly with length prefixes and 4-byte chunk alignment.
- **Binary AXML Package Cloner:** Automatically re-authorizes `<provider>` tags and appends clone suffixes to avoid OEM installation collisions.
- **Vision-in-the-Loop QA:** Uses Gemini Vision to inspect keyboard layouts for missing icons, clipped text, or crash dialogs.
- **Token Efficiency:** The entire pipeline executes with only 2 lightweight Gemini API calls (~3,500 tokens total), making it impossible to run out of credits mid-task.

---

## 📦 Directory Structure

```
autoApkPipeline/
├── .github/workflows/pipeline.yml  # GitHub Actions workflow definition
├── scripts/
│   ├── bootstrap.sh                # Automated toolchain installer (Java, Apktool, d8, apksigner)
│   ├── rebuild.sh                  # Reassembles, aligns, and release-signs APKs
│   └── generate_keystore.sh        # Generates release signing keystores
├── patches/
│   ├── agent.py                    # Autonomous AI planning agent (Gemini Flash)
│   ├── smali_patcher.py            # Rule-based Smali bytecode modifier
│   ├── arsc_localizer.py           # Binary ARSC string pool localizer
│   └── manifest_cloner.py          # Binary AXML package and authority cloner
├── ai_qa/
│   ├── run_visual_qa.py            # Real-time screenshot capturer and Gemini Vision inspector
│   └── qa_report.py                # Standalone HTML visual report generator
├── input/                          # Place your target input APK here
├── config.json                     # Declarative pipeline configuration
└── AutoAPK_Pipeline.ipynb          # 1-Click Google Colab notebook
```

---

## 🔐 Configured Secrets

The repository is already pre-configured with the required GitHub Actions secrets:
- `GEMINI_API_KEY`: Google Gemini Vision & Planning Engine
- `GIPHY_API_KEY`: Live Giphy Stickers & GIFs Search API

---

## 📄 License
MIT License. Created by [Hpsctrl](https://github.com/Hpsctrl).
