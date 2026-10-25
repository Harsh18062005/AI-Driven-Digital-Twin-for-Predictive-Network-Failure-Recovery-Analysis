"""Network Inventory Loader and Validator.

Loads, parses, and strictly validates network topology definitions from JSON
inventory files. Ensures schema integrity, uniqueness of device/link IDs,
referential integrity of endpoints, and correctness of IP/CIDR notations.
"""

from __future__ import annotations

import ipaddress
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class InventoryValidationError(ValueError):
    """Base exception for inventory validation failures."""
    pass


class SchemaError(InventoryValidationError):
    """Raised when JSON schema structure is missing required keys or has wrong types."""
    pass


class DuplicateIdError(InventoryValidationError):
    """Raised when duplicate device or link identifiers are detected."""
    pass


class ReferentialIntegrityError(InventoryValidationError):
    """Raised when a link references non-existent device endpoints."""
    pass


class InvalidIPAddressError(InventoryValidationError):
    """Raised when an IP address, subnet mask, or CIDR block is invalid."""
    pass


VALID_DEVICE_TYPES: Set[str] = {"Router", "Switch", "Server", "PC", "Firewall", "AccessPoint"}
VALID_LINK_TYPES: Set[str] = {"Trunk", "Access", "WAN", "Loopback"}
VALID_LINK_STATUSES: Set[str] = {"up", "down", "testing"}
VALID_DEVICE_STATUSES: Set[str] = {"active", "inactive", "maintenance"}


def validate_ip_address(ip_val: Any, field_name: str, context_id: str) -> None:
    """Validate that ip_val is a valid IPv4 address string."""
    if ip_val is None:
        return
    if not isinstance(ip_val, str) or not ip_val.strip():
        raise InvalidIPAddressError(
            f"Invalid IP address format in {context_id} for field '{field_name}': expected non-empty string, got {type(ip_val).__name__}"
        )
    try:
        ipaddress.IPv4Address(ip_val.strip())
    except ValueError as err:
        raise InvalidIPAddressError(
            f"Invalid IPv4 address '{ip_val}' in {context_id} for field '{field_name}': {err}"
        ) from err


def validate_cidr_block(cidr_val: Any, field_name: str, context_id: str) -> None:
    """Validate that cidr_val is a valid IPv4 network in CIDR notation (e.g. 192.168.1.0/24)."""
    if cidr_val is None:
        return
    if not isinstance(cidr_val, str) or not cidr_val.strip():
        raise InvalidIPAddressError(
            f"Invalid CIDR notation in {context_id} for field '{field_name}': expected non-empty string, got {type(cidr_val).__name__}"
        )
    try:
        ipaddress.IPv4Network(cidr_val.strip(), strict=False)
    except ValueError as err:
        raise InvalidIPAddressError(
            f"Invalid CIDR block '{cidr_val}' in {context_id} for field '{field_name}': {err}"
        ) from err


def validate_inventory(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate raw loaded JSON inventory data against the strict network schema.

    Args:
        data: Parsed dictionary from network JSON file.

    Returns:
        The validated dictionary.

    Raises:
        SchemaError: If required top-level keys or fields are missing/malformed.
        DuplicateIdError: If duplicate device_id or link_id entries exist.
        ReferentialIntegrityError: If a link endpoint references an unknown device.
        InvalidIPAddressError: If any IP address or CIDR notation is invalid.
    """
    if not isinstance(data, dict):
        raise SchemaError(f"Inventory root must be a JSON object, got {type(data).__name__}")

    # Top-level required keys
    for required_key in ("metadata", "devices", "links"):
        if required_key not in data:
            raise SchemaError(f"Missing required root key: '{required_key}'")

    devices_raw = data.get("devices")
    if not isinstance(devices_raw, list):
        raise SchemaError(f"'devices' must be a list of device objects, got {type(devices_raw).__name__}")

    links_raw = data.get("links")
    if not isinstance(links_raw, list):
        raise SchemaError(f"'links' must be a list of link objects, got {type(links_raw).__name__}")

    device_ids: Set[str] = set()

    # 1. Validate Devices
    for idx, dev in enumerate(devices_raw):
        if not isinstance(dev, dict):
            raise SchemaError(f"Device at index {idx} must be a dictionary, got {type(dev).__name__}")

        dev_id = dev.get("device_id")
        if not dev_id or not isinstance(dev_id, str) or not dev_id.strip():
            raise SchemaError(f"Device at index {idx} is missing a non-empty 'device_id'")
        dev_id = dev_id.strip()

        if dev_id in device_ids:
            raise DuplicateIdError(f"Duplicate device_id detected: '{dev_id}'")
        device_ids.add(dev_id)

        # Check required device fields
        for field in ("hostname", "device_type", "branch", "role", "status"):
            val = dev.get(field)
            if val is None or not isinstance(val, str) or not val.strip():
                raise SchemaError(f"Device '{dev_id}' is missing required field '{field}'")

        # Validate management IP if present
        if "management_ip" in dev and dev["management_ip"] is not None:
            validate_ip_address(dev["management_ip"], "management_ip", dev_id)

        # Validate VLANs
        vlans = dev.get("vlans", [])
        if not isinstance(vlans, list):
            raise SchemaError(f"Device '{dev_id}' 'vlans' field must be a list of integers")
        for v in vlans:
            if not isinstance(v, int) or v < 1 or v > 4094:
                raise SchemaError(f"Device '{dev_id}' has invalid 802.1Q VLAN ID: {v} (must be 1-4094)")

        # Validate interfaces
        interfaces = dev.get("interfaces", [])
        if not isinstance(interfaces, list):
            raise SchemaError(f"Device '{dev_id}' 'interfaces' field must be a list")
        for iface in interfaces:
            if not isinstance(iface, dict):
                raise SchemaError(f"Device '{dev_id}' contains invalid interface (must be object)")
            iface_name = iface.get("name")
            if not iface_name or not isinstance(iface_name, str):
                raise SchemaError(f"Device '{dev_id}' interface missing 'name'")
            if "ip_address" in iface and iface["ip_address"] is not None:
                validate_ip_address(iface["ip_address"], f"{iface_name}.ip_address", dev_id)
            if "cidr" in iface and iface["cidr"] is not None:
                validate_cidr_block(iface["cidr"], f"{iface_name}.cidr", dev_id)
            if "gateway" in iface and iface["gateway"] is not None:
                validate_ip_address(iface["gateway"], f"{iface_name}.gateway", dev_id)

    # 2. Validate Links
    link_ids: Set[str] = set()
    for idx, link in enumerate(links_raw):
        if not isinstance(link, dict):
            raise SchemaError(f"Link at index {idx} must be a dictionary, got {type(link).__name__}")

        link_id = link.get("link_id")
        if not link_id or not isinstance(link_id, str) or not link_id.strip():
            raise SchemaError(f"Link at index {idx} is missing a non-empty 'link_id'")
        link_id = link_id.strip()

        if link_id in link_ids:
            raise DuplicateIdError(f"Duplicate link_id detected: '{link_id}'")
        link_ids.add(link_id)

        # Check required link fields
        for field in ("source_device", "source_interface", "target_device", "target_interface", "link_type", "status"):
            val = link.get(field)
            if val is None or not isinstance(val, str) or not val.strip():
                raise SchemaError(f"Link '{link_id}' is missing required field '{field}'")

        src = link["source_device"].strip()
        tgt = link["target_device"].strip()

        # Referential integrity check
        if src not in device_ids:
            raise ReferentialIntegrityError(
                f"Link '{link_id}' references unknown source_device: '{src}'"
            )
        if tgt not in device_ids:
            raise ReferentialIntegrityError(
                f"Link '{link_id}' references unknown target_device: '{tgt}'"
            )
        if src == tgt:
            raise SchemaError(
                f"Link '{link_id}' has identical source and target endpoints ('{src}'). Self-loops not permitted."
            )

        # Bandwidth check
        bw = link.get("bandwidth_mbps")
        if bw is None:
            raise SchemaError(f"Link '{link_id}' is missing 'bandwidth_mbps'")
        if not isinstance(bw, (int, float)) or bw <= 0:
            raise SchemaError(f"Link '{link_id}' bandwidth_mbps must be a positive number, got {bw}")

        # Subnet check if provided
        if "subnet" in link and link["subnet"] is not None:
            validate_cidr_block(link["subnet"], "subnet", link_id)

    return data


def load_inventory(file_path: Optional[str | Path] = None) -> Dict[str, Any]:
    """Load and validate network inventory from a JSON file.

    Args:
        file_path: Path to the network.json file. Defaults to python/network.json.

    Returns:
        The validated dictionary containing metadata, devices, and links.

    Raises:
        FileNotFoundError: If the specified file does not exist.
        InventoryValidationError: If validation fails.
    """
    if file_path is None:
        target_path = Path(__file__).resolve().parent / "network.json"
    else:
        target_path = Path(file_path).resolve()

    if not target_path.exists():
        raise FileNotFoundError(f"Network inventory file not found: {target_path}")

    with open(target_path, "r", encoding="utf-8") as f:
        try:
            raw_data = json.load(f)
        except json.JSONDecodeError as err:
            raise SchemaError(f"Failed to parse JSON file {target_path}: {err}") from err

    return validate_inventory(raw_data)


def get_inventory_summary(inventory: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a high-level summary of the loaded inventory."""
    devices = inventory.get("devices", [])
    links = inventory.get("links", [])
    branches: Set[str] = set()
    device_types: Dict[str, int] = {}

    for d in devices:
        branches.add(d.get("branch", "Unknown"))
        dtype = d.get("device_type", "Unknown")
        device_types[dtype] = device_types.get(dtype, 0) + 1

    return {
        "network_name": inventory.get("metadata", {}).get("network_name", "Unnamed Network"),
        "total_devices": len(devices),
        "total_links": len(links),
        "branches": sorted(list(branches)),
        "device_types": device_types,
    }


if __name__ == "__main__":
    try:
        inv = load_inventory()
        summary = get_inventory_summary(inv)
        print("Inventory loaded successfully!")
        print(f"Network Name: {summary['network_name']}")
        print(f"Total Devices: {summary['total_devices']}")
        print(f"Total Links: {summary['total_links']}")
        print(f"Branches: {', '.join(summary['branches'])}")
        print(f"Device Breakdown: {summary['device_types']}")
    except Exception as exc:
        print(f"Error loading inventory: {exc}")
