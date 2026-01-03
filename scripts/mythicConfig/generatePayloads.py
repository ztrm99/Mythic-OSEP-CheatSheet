#!/usr/bin/env python3
"""
generatePayloads.py
Usage:
    python3 generatePayloads.py <IP> <PORT> [apollo|poseidon|both]

The script logs into Mythic, reads payload build configurations from JSON files,
creates the requested payload(s), waits until the build finishes, and downloads
the resulting file(s). Each payload is saved using its payload filename.
Expected config files in current directory:
    - apollo.exe.json
    - poseidon.bin.json
"""

import asyncio
import sys
import json
import os
from mythic import mythic

# ==========================
# Mythic Connection Settings
# ==========================
MYTHIC_USERNAME = "mythic_admin"
MYTHIC_PASSWORD = "2UaVvruwS7SqCpp5MNaKZyIqL9KSnC"
MYTHIC_SERVER_IP = "127.0.0.1"
MYTHIC_SERVER_PORT = 7443
MYTHIC_TIMEOUT = -1  # no timeout

# ==========================
# Path Handling
# ==========================
# Directory where this Python script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# JSON config file paths (always relative to script location)
APOLLO_JSON_PATH = os.path.join(SCRIPT_DIR, "apollo.exe.json")
POSEIDON_JSON_PATH = os.path.join(SCRIPT_DIR, "poseidon.bin.json")
APOLLO_SERVICE_JSON_PATH = os.path.join(SCRIPT_DIR, "apollo.bin.json")


# ==========================
# Utility Functions
# ==========================
async def login_mythic():
    """Authenticate to Mythic and return a session instance."""
    print("[*] Logging into Mythic...")
    return await mythic.login(
        username=MYTHIC_USERNAME,
        password=MYTHIC_PASSWORD,
        server_ip=MYTHIC_SERVER_IP,
        server_port=MYTHIC_SERVER_PORT,
        timeout=MYTHIC_TIMEOUT
    )


def load_payload_config(path):
    """Load a payload configuration JSON file from disk."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"[*] Loaded payload configuration from {path}")
        return data
    except Exception as e:
        print(f"[!] Failed to load config {path}: {e}")
        sys.exit(1)


async def create_payload(mythic_instance, cfg):
    """Submit payload creation to Mythic and wait until build completes."""
    print(f"[*] Creating payload: {cfg.get('filename')} ({cfg.get('payload_type')})")
    response = await mythic.create_payload(
        mythic=mythic_instance,
        payload_type_name=cfg.get("payload_type"),
        filename=cfg.get("filename"),
        operating_system=cfg.get("selected_os"),
        commands=cfg.get("commands"),
        c2_profiles=cfg.get("c2_profiles"),
        build_parameters=cfg.get("build_parameters"),
        return_on_complete=True  # wait until build completes
    )
    print("[+] Build completed for", cfg.get("filename"))
    return response


async def download_and_save(mythic_instance, payload_response, cfg):
    """
    Download built payload using its UUID and save to disk using the payload filename.
    If Mythic response lacks filename, fallback to the one from the config.
    """
    uuid = payload_response.get("uuid")
    if not uuid:
        print("[!] No UUID in payload response; cannot download.")
        return None

    print(f"[*] Downloading payload UUID {uuid} ...")
    payload_bytes = await mythic.download_payload(mythic=mythic_instance, payload_uuid=uuid)
    if not payload_bytes:
        print("[!] No payload bytes returned.")
        return None

    # Use filename from response, fall back to config JSON
    raw_name = (
        payload_response.get("filename")
        or payload_response.get("file_name")
        or cfg.get("filename")
        or "payload.bin"
    )

    safe_name = os.path.basename(raw_name)
    out_file = safe_name

    try:
        with open(out_file, "wb") as f:
            f.write(payload_bytes)
        print(f"[+] Saved payload to {out_file}")
        return out_file
    except Exception as e:
        print(f"[!] Failed to save payload {out_file}: {e}")
        return None


# ==========================
# Payload-specific Functions
# ==========================
async def create_apollo(mythic_instance, callback_host, callback_port):
    """Load Apollo config, adjust callback settings, build and download."""
    cfg = load_payload_config(APOLLO_JSON_PATH)
    for profile in cfg.get("c2_profiles", []):
        params = profile.get("c2_profile_parameters", {})
        params["callback_host"] = callback_host
        params["callback_port"] = callback_port
    resp = await create_payload(mythic_instance, cfg)
    return await download_and_save(mythic_instance, resp, cfg)


async def create_apollo_service(mythic_instance, callback_host, callback_port):
    """Load Apollo config, adjust callback settings, build and download."""
    cfg = load_payload_config(APOLLO_SERVICE_JSON_PATH)
    for profile in cfg.get("c2_profiles", []):
        params = profile.get("c2_profile_parameters", {})
        params["callback_host"] = callback_host
        params["callback_port"] = callback_port
    resp = await create_payload(mythic_instance, cfg)
    return await download_and_save(mythic_instance, resp, cfg)


async def create_poseidon(mythic_instance, callback_host, callback_port):
    """Load Poseidon config, adjust callback settings, build and download."""
    cfg = load_payload_config(POSEIDON_JSON_PATH)
    for profile in cfg.get("c2_profiles", []):
        params = profile.get("c2_profile_parameters", {})
        params["callback_host"] = callback_host
        params["callback_port"] = callback_port
    resp = await create_payload(mythic_instance, cfg)
    return await download_and_save(mythic_instance, resp, cfg)


# ==========================
# Main Entry Point
# ==========================
async def main():
    if len(sys.argv) < 3:
        print("Usage: python3 generatePayloads.py <IP> <PORT> [apollo|poseidon|both]")
        sys.exit(1)

    callback_host = sys.argv[1]
    try:
        callback_port = int(sys.argv[2])
    except ValueError:
        print("[!] PORT must be an integer.")
        sys.exit(1)

    mode = "both"
    if len(sys.argv) >= 4:
        mode = sys.argv[3].lower()
        if mode not in ("apollo", "poseidon", "both"):
            print("[!] Invalid mode, defaulting to both.")
            mode = "both"

    print(f"[*] Callback host: {callback_host}")
    print(f"[*] Callback port: {callback_port}")
    print(f"[*] Mode: {mode}")

    mythic_instance = await login_mythic()

    results = {}
    if mode in ("apollo", "both"):
        results["apollo"] = await create_apollo(mythic_instance, callback_host, callback_port)
        results["apollo_service"] = await create_apollo_service(mythic_instance, callback_host, callback_port)
    if mode in ("poseidon", "both"):
        results["poseidon"] = await create_poseidon(mythic_instance, callback_host, callback_port)

    print("\n========== Summary ==========")
    for k, v in results.items():
        print(f"{k}: {v}")
    print("=============================")


if __name__ == "__main__":
    asyncio.run(main())
