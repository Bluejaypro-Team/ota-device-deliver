---
name: ota-device-deliver
description: Compiles and delivers developer files to a connected Android device over the internet via WebSocket bridge.
---

# ota-device-deliver

This skill compiles local developer files, uploads them to the Google Cloud Storage bucket, and delivers them directly to a connected Android companion device.

## Core Methodology

1. Compile the file or resource.
2. Upload the file to the GCS bucket `tidal-mode-490503-i9.appspot.com`.
3. Issue a POST request to `/command` on the Node.js bridge backend with the appropriate action and payload.

## Handling Offline Devices

If the backend server returns an HTTP `400 Bad Request` with an error message like `"No active device connection"`, the target device may be asleep or offline.
In this case, the skill must:
1. Schedule a retry timer utilizing the `/schedule` tool.
2. The retry timer should trigger in 30 seconds to attempt delivery again.
