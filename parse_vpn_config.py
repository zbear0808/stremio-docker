#!/usr/bin/env python3
"""
parse_vpn_config.py

Parses a WireGuard / AirVPN .conf file and generates/updates a .env file
for use with Docker Compose and Gluetun.
"""

import sys
import os
import re
import glob
from pathlib import Path


def parse_conf_file(conf_path: Path):
    if not conf_path.is_file():
        raise FileNotFoundError(f"Config file not found: {conf_path}")

    data = {}
    current_section = None

    with open(conf_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Section header [Interface] or [Peer]
            section_match = re.match(r"^\[(\w+)\]$", line)
            if section_match:
                current_section = section_match.group(1).lower()
                continue

            # Key-value pairs
            if "=" in line:
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip()
                data[key.lower()] = val

    return data


def extract_ipv4(address_str: str) -> str:
    """Extract IPv4 address with subnet mask from comma-separated list."""
    for addr in address_str.split(","):
        addr = addr.strip()
        # Simple IPv4 check: contains dots and no colons
        if "." in addr and ":" not in addr:
            return addr
    return address_str.split(",")[0].strip()


def infer_region_or_country(filename: str, endpoint: str) -> dict:
    results = {}
    lower_str = f"{filename} {endpoint}".lower()

    if "america" in lower_str or "us" in lower_str or "usa" in lower_str:
        results["SERVER_REGIONS"] = "America"
    elif "europe" in lower_str:
        results["SERVER_REGIONS"] = "Europe"
    elif "asia" in lower_str:
        results["SERVER_REGIONS"] = "Asia"

    return results


def main():
    repo_dir = Path(__file__).resolve().parent

    # Determine which config file to use
    if len(sys.argv) > 1:
        conf_file = Path(sys.argv[1])
        if not conf_file.is_absolute():
            conf_file = repo_dir / conf_file
    else:
        # Search for .conf files in the directory
        conf_files = list(repo_dir.glob("*.conf"))
        if not conf_files:
            print("Error: No .conf files found in the current directory.")
            print("Usage: python3 parse_vpn_config.py <path_to_conf_file>")
            sys.exit(1)
        # Prefer AirVPN conf if present
        airvpn_confs = [c for c in conf_files if "airvpn" in c.name.lower()]
        conf_file = airvpn_confs[0] if airvpn_confs else conf_files[0]

    print(f"Parsing WireGuard configuration from: {conf_file.name}")
    config_data = parse_conf_file(conf_file)

    private_key = config_data.get("privatekey", "")
    preshared_key = config_data.get("presharedkey", "")
    addresses_raw = config_data.get("address", "")
    public_key = config_data.get("publickey", "")
    endpoint = config_data.get("endpoint", "")
    dns = config_data.get("dns", "")

    ipv4_address = extract_ipv4(addresses_raw) if addresses_raw else ""

    inferred_geo = infer_region_or_country(conf_file.name, endpoint)
    server_regions = inferred_geo.get("SERVER_REGIONS", "America")

    if not private_key:
        print("Warning: No PrivateKey found in config file.")
    if not preshared_key:
        print("Warning: No PresharedKey found in config file.")
    if not ipv4_address:
        print("Warning: No IPv4 Address found in config file.")

    env_path = repo_dir / ".env"
    env_content = f"""# ==========================================
# AirVPN & Gluetun Docker Environment Secrets
# Auto-generated from {conf_file.name}
# ==========================================

# VPN Provider Settings
VPN_SERVICE_PROVIDER=airvpn
VPN_TYPE=wireguard

# WireGuard Credentials
WIREGUARD_PRIVATE_KEY={private_key}
WIREGUARD_PRESHARED_KEY={preshared_key}
WIREGUARD_ADDRESSES={ipv4_address}

# Server Selection
SERVER_REGIONS={server_regions}
SERVER_COUNTRIES=

# Server Peer Details (for reference or custom config)
WIREGUARD_PUBLIC_KEY={public_key}
WIREGUARD_ENDPOINT={endpoint}
VPN_DNS={dns}

# Optional: Inbound forwarded port from AirVPN dashboard
# FIREWALL_VPN_INPUT_PORTS=
"""

    with open(env_path, "w", encoding="utf-8") as f:
        f.write(env_content)

    print(f"Successfully generated {env_path.name} with extracted credentials:")
    print(f" - WIREGUARD_ADDRESSES: {ipv4_address}")
    print(f" - WIREGUARD_PRIVATE_KEY: [HIDDEN] ({len(private_key)} chars)")
    print(f" - WIREGUARD_PRESHARED_KEY: [HIDDEN] ({len(preshared_key)} chars)")
    print(f" - SERVER_REGIONS: {server_regions}")
    if endpoint:
        print(f" - Endpoint: {endpoint}")


if __name__ == "__main__":
    main()

