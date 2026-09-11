# OTA Device Deliver (`ota-device-deliver`)

[![Skill Architecture](https://img.shields.io/badge/Architecture-Antigravity%20Agentic%20Studio-blue)](https://github.com/Bluejaypro-Team)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Installed%20%26%20Active-brightgreen)](manifest.json)

An autonomous developer skill that compiles local assets, stages them to Google Cloud Storage, and delivers them directly to a connected Android companion device over an encrypted WebSocket bridge.

---

## 🚀 Overview

The `ota-device-deliver` skill enables seamless Over-The-Air (OTA) synchronization between desktop developer workstations and physical Android companion devices. It handles offline caching, automated scheduled retries, toast alerts, URL browsing, and notification delivery.

### Key Capabilities
- **Direct Cloud Staging:** Uploads developer files directly to Google Cloud Storage (`helpfulhub-ev-comparison` / App Engine buckets).
- **Persistent Bridge Commands:** Communicates with the Node.js WebSocket bridge to dispatch instant execution payloads (`OPEN_URL`, `SHOW_TOAST`, `SHOW_ALERT`).
- **Offline Device Resilience:** Gracefully falls back to scheduled polling queues if the target companion device is sleeping or disconnected.
- **Cryptographic Tracking:** Fully declared with `manifest.json` and registered with SHA256 integrity verification.

---

## 📁 Repository Structure

```
ota-device-deliver/
├── manifest.json            # Official skill identity, runtime, & command metadata
├── SKILL.md                 # Agent instruction specification & offline retry rules
├── .gitignore               # Ignored cache files & bytecode
├── README.md                # Public documentation & architecture guide
└── scripts/
    └── ota_deliver.py       # Standalone Python CLI delivery orchestrator
```

---

## 💻 CLI Usage

```bash
# Deliver a document or asset to open on device:
python scripts/ota_deliver.py --file "/path/to/document.docx"

# Display a companion toast notification:
python scripts/ota_deliver.py --action SHOW_TOAST --payload "Build completed successfully!"

# Trigger an on-device alert dialog:
python scripts/ota_deliver.py --action SHOW_ALERT --title "Deploy Warning" --payload "Review server logs"
```

---

## ⚙️ Configuration

Optional configuration can be stored at `~/.config/ota-deliver/config.json`:

```json
{
  "device_id": "default_device",
  "server_url": "https://project-4e0e14b0-60c5-47d8-b75.uc.r.appspot.com",
  "bucket_name": "helpfulhub-ev-comparison"
}
```

---

## 👤 Author & Maintainer

**Bluejaypro-Team** (Justin Jones)  
*Antigravity Agentic Studio • Developer Skills Registry*
