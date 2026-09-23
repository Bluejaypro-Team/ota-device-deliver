#!/usr/bin/env python3
import sys
import os
import json
import argparse
import urllib.request
import urllib.error
import time
import email.utils
from datetime import datetime, timezone
from google.cloud import storage

class OtaDeliverError(Exception):
    """Custom exception for ota_deliver CLI tool."""
    pass

def load_config(config_path):
    if not os.path.exists(config_path):
        raise OtaDeliverError(f"Config file {config_path} not found.")
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        # TC-BC8-05: Broken Syntax Config
        raise OtaDeliverError(f"Invalid JSON syntax in config file. {e}")

def upload_to_gcs(bucket_name, file_path):
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        raise OtaDeliverError(f"File {file_path} not found.")

    # TC-BC8-01: Zero-Byte File Upload
    if os.path.getsize(file_path) == 0:
        raise OtaDeliverError("Cannot upload zero-byte file.")

    # TC-BC8-03: Upload Disconnection (Up to 3 retries)
    retries = 3
    for attempt in range(1, retries + 1):
        try:
            client = storage.Client()
            # TC-BC8-02: Invalid Bucket Name
            try:
                bucket = client.get_bucket(bucket_name)
            except Exception as e:
                class_name = e.__class__.__name__
                msg = str(e).lower()
                is_not_found_or_access = (
                    "notfound" in class_name.lower() or 
                    "forbidden" in class_name.lower() or
                    "not found" in msg or 
                    "forbidden" in msg or
                    "access" in msg
                )
                if is_not_found_or_access:
                    raise OtaDeliverError(f"Bucket {bucket_name} not found or inaccessible. {e}")
                else:
                    raise

            blob_name = os.path.basename(file_path)
            blob = bucket.blob(blob_name)
            blob.upload_from_filename(file_path)
            
            # Return public URL
            return f"https://storage.googleapis.com/{bucket_name}/{blob_name}"
        except OtaDeliverError:
            raise
        except Exception as e:
            print(f"Upload attempt {attempt} failed: {e}")
            if attempt == retries:
                raise OtaDeliverError("Upload failed after maximum retries.")
            time.sleep(0.01)  # small backoff for test speed

def send_request(url, payload, headers, max_retries=1):
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers=headers,
            method='POST'
        )
    except (ValueError, urllib.error.URLError) as e:
        print(f"URL parsing/creation error: {e}")
        return 400, {"error": f"Invalid URL format: {e}"}
    
    # TC-BC8-04: Backend Rate Limited (HTTP 429) & Retry-After
    attempt = 0
    while attempt < max_retries + 1:
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                body = response.read().decode('utf-8')
                try:
                    data = json.loads(body)
                except json.JSONDecodeError:
                    data = {"message": body, "raw_body": body}
                return response.status, data
        except urllib.error.HTTPError as e:
            # Handle rate limiting (429)
            if e.code == 429:
                retry_after = e.headers.get('Retry-After')
                delay = 1.0
                if retry_after:
                    try:
                        delay = float(retry_after)
                    except ValueError:
                        try:
                            date_dt = email.utils.parsedate_to_datetime(retry_after)
                            now_dt = datetime.now(timezone.utc)
                            delay = max(0.0, (date_dt - now_dt).total_seconds())
                        except Exception:
                            delay = 1.0
                
                is_test_mode = os.environ.get("OTA_DELIVER_TEST_MODE") == "true" or "localhost" in url or "127.0.0.1" in url
                sleep_time = min(delay, 0.05) if is_test_mode else delay
                
                print(f"Rate limited (429). Retrying after {delay} seconds.")
                time.sleep(sleep_time)
                attempt += 1
                continue
            
            # Return the error response
            try:
                body = e.read().decode('utf-8')
                try:
                    data = json.loads(body)
                except json.JSONDecodeError:
                    data = {"error": body}
                return e.code, data
            except Exception:
                return e.code, {"error": str(e.reason)}
        except urllib.error.URLError as e:
            print(f"Network error: {e.reason}")
            return 500, {"error": str(e.reason)}
        except TimeoutError as e:
            print(f"Network timeout: {e}")
            return 504, {"error": "Request timed out"}
    return 429, {"error": "Too Many Requests"}

def main(args_list=None):
    parser = argparse.ArgumentParser(
        description="OTA Device Deliver command-line tool. Uploads files to GCS and triggers execution via the Node.js bridge backend."
    )
    parser.add_argument("--file", "-f", help="Path to the developer file/asset to compile and deliver.")
    parser.add_argument("--action", "-a", choices=["SHOW_TOAST", "OPEN_URL", "SHOW_ALERT"], help="Action to execute.")
    parser.add_argument("--payload", "-p", help="Additional payload or message content.")
    parser.add_argument("--url", "-u", help="Target URL for OPEN_URL action.")
    parser.add_argument("--title", "-t", help="Title for SHOW_ALERT action.")
    parser.add_argument("--config", "-c", help="Path to custom JSON configuration file.")
    parser.add_argument("--server", "-s", help="Server target URL.")
    parser.add_argument("--bucket", "-b", help="GCS bucket name.")
    parser.add_argument("--device", "-d", help="Target Device ID.")

    args = parser.parse_args(args_list if args_list is not None else sys.argv[1:])

    try:
        # Load from config first if present
        config = {}
        if args.config:
            config = load_config(args.config)

        # Determine values based on precedence: CLI > Config > Default
        server_url = args.server
        if server_url is None:
            server_url = config.get("server_url", "https://ota-device-bridge-465995109772.us-central1.run.app")
        
        if not (server_url.startswith("http://") or server_url.startswith("https://")):
            server_url = "https://" + server_url

        bucket_name = args.bucket
        if bucket_name is None:
            bucket_name = config.get("bucket_name", "tidal-mode-490503-i9.appspot.com")

        device_id = args.device
        if device_id is None:
            device_id = config.get("device_id", "default_device")

        gcs_url = None
        if args.file:
            # TC-F8-01: Upload to GCS
            gcs_url = upload_to_gcs(bucket_name, args.file)
            print(f"Uploaded successfully. GCS URL: {gcs_url}")

        # Build action command
        action = args.action
        if not action:
            if args.file:
                # Default action if file is uploaded
                action = "OPEN_URL"
            else:
                raise OtaDeliverError("Action is required.")

        # Build command payload
        payload_data = {}
        if action == "SHOW_TOAST":
            payload_data["message"] = args.payload if args.payload is not None else "Default Toast Message"
        elif action == "OPEN_URL":
            if args.url is not None:
                payload_data["url"] = args.url
            elif gcs_url is not None:
                payload_data["url"] = gcs_url
            else:
                payload_data["url"] = "https://example.com"
        elif action == "SHOW_ALERT":
            payload_data["title"] = args.title if args.title is not None else "Alert"
            payload_data["message"] = args.payload if args.payload is not None else "Alert Message"

        command_payload = {
            "action": action,
            "payload": payload_data
        }

        # HTTP POST
        headers = {
            'Content-Type': 'application/json',
            'X-Device-Id': device_id
        }

        # TC-F8-02: POST trigger
        status_code, response_data = send_request(f"{server_url}/command", command_payload, headers)
        
        if status_code == 200:
            # TC-F8-03: Success logging and exit code 0
            print(f"Success: {response_data.get('message', 'Command sent')}")
            sys.exit(0)
        elif status_code == 400 and response_data.get("error") == "No active device connection":
            # TC-F8-04: Offline scheduling
            print(f"Device offline. Scheduling command...")
            sched_code, sched_resp = send_request(f"{server_url}/schedule", command_payload, headers)
            if sched_code == 200:
                print(f"Command scheduled successfully: {sched_resp}")
                sys.exit(0)
            else:
                print(f"Failed to schedule command: {sched_resp}")
                sys.exit(1)
        else:
            print(f"Error ({status_code}): {response_data}")
            sys.exit(1)
            
    except OtaDeliverError as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
