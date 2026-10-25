"""Unit and schema validation tests for inventory_loader.py.

Uses small, synthetic fixtures to rigorously test edge cases, schema violations,
duplicate IDs, referential integrity failures, and IP address errors.
"""

from __future__ import annotations

import copy
from pathlib import Path
import pytest

from inventory_loader import (
    load_inventory,
    validate_inventory,
    get_inventory_summary,
    SchemaError,
    DuplicateIdError,
    ReferentialIntegrityError,
    InvalidIPAddressError,
)

# Small synthetic baseline fixture for testing validator behavior
MINIMAL_VALID_FIXTURE = {
    "metadata": {
        "network_name": "Test Toy Network",
        "version": "0.1.0",
        "total_devices": 2,
        "total_links": 1,
    },
    "devices": [
        {
            "device_id": "TEST-R1",
            "hostname": "Test-Router",
            "device_type": "Router",
            "branch": "Test Branch",
            "role": "Gateway",
            "management_ip": "192.168.1.1",
            "vlans": [10],
            "interfaces": [
                {
                    "name": "Gig0/0",
                    "ip_address": "192.168.1.1",
                    "cidr": "192.168.1.0/24",
                }
            ],
            "status": "active",
        },
        {
            "device_id": "TEST-SW1",
            "hostname": "Test-Switch",
            "device_type": "Switch",
            "branch": "Test Branch",
            "role": "Access",
            "management_ip": "192.168.1.2",
            "vlans": [10],
            "interfaces": [{"name": "Fa0/1", "mode": "Access"}],
            "status": "active",
        },
    ],
    "links": [
        {
            "link_id": "LINK-TEST-1",
            "source_device": "TEST-R1",
            "source_interface": "Gig0/0",
            "target_device": "TEST-SW1",
            "target_interface": "Fa0/1",
            "link_type": "Access",
            "bandwidth_mbps": 100,
            "subnet": "192.168.1.0/24",
            "status": "up",
        }
    ],
}


def test_load_real_network_inventory():
    """Verify that the production network.json loads and passes all validation checks."""
    inv = load_inventory()
    assert inv is not None
    assert "devices" in inv
    assert "links" in inv
    assert len(inv["devices"]) == 22
    assert len(inv["links"]) == 24
    summary = get_inventory_summary(inv)
    assert summary["total_devices"] == 22
    assert summary["total_links"] == 24
    assert len(summary["branches"]) == 5


def test_missing_file_raises_error():
    """Verify that attempting to load a non-existent file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_inventory("non_existent_network_file.json")


def test_missing_root_key_raises_schema_error():
    """Verify missing required top-level keys triggers SchemaError."""
    bad_data = copy.deepcopy(MINIMAL_VALID_FIXTURE)
    del bad_data["metadata"]
    with pytest.raises(SchemaError, match="Missing required root key"):
        validate_inventory(bad_data)


def test_missing_device_id_raises_schema_error():
    """Verify missing or blank device_id triggers SchemaError."""
    bad_data = copy.deepcopy(MINIMAL_VALID_FIXTURE)
    bad_data["devices"][0]["device_id"] = "   "
    with pytest.raises(SchemaError, match="missing a non-empty 'device_id'"):
        validate_inventory(bad_data)


def test_duplicate_device_id_raises_duplicate_error():
    """Verify duplicate device IDs are detected and rejected."""
    bad_data = copy.deepcopy(MINIMAL_VALID_FIXTURE)
    bad_data["devices"].append(copy.deepcopy(bad_data["devices"][0]))
    with pytest.raises(DuplicateIdError, match="Duplicate device_id detected"):
        validate_inventory(bad_data)


def test_duplicate_link_id_raises_duplicate_error():
    """Verify duplicate link IDs are detected and rejected."""
    bad_data = copy.deepcopy(MINIMAL_VALID_FIXTURE)
    dup_link = copy.deepcopy(bad_data["links"][0])
    bad_data["links"].append(dup_link)
    with pytest.raises(DuplicateIdError, match="Duplicate link_id detected"):
        validate_inventory(bad_data)


def test_referential_integrity_unknown_source():
    """Verify that a link referencing an unknown source_device triggers ReferentialIntegrityError."""
    bad_data = copy.deepcopy(MINIMAL_VALID_FIXTURE)
    bad_data["links"][0]["source_device"] = "GHOST-DEVICE-99"
    with pytest.raises(ReferentialIntegrityError, match="references unknown source_device"):
        validate_inventory(bad_data)


def test_referential_integrity_unknown_target():
    """Verify that a link referencing an unknown target_device triggers ReferentialIntegrityError."""
    bad_data = copy.deepcopy(MINIMAL_VALID_FIXTURE)
    bad_data["links"][0]["target_device"] = "GHOST-DEVICE-99"
    with pytest.raises(ReferentialIntegrityError, match="references unknown target_device"):
        validate_inventory(bad_data)


def test_self_loop_link_rejected():
    """Verify that a link connecting a device to itself is rejected."""
    bad_data = copy.deepcopy(MINIMAL_VALID_FIXTURE)
    bad_data["links"][0]["target_device"] = "TEST-R1"
    with pytest.raises(SchemaError, match="Self-loops not permitted"):
        validate_inventory(bad_data)


def test_invalid_ip_address_raises_error():
    """Verify that malformed IP addresses raise InvalidIPAddressError."""
    bad_data = copy.deepcopy(MINIMAL_VALID_FIXTURE)
    bad_data["devices"][0]["management_ip"] = "999.888.777.666"
    with pytest.raises(InvalidIPAddressError, match="Invalid IPv4 address"):
        validate_inventory(bad_data)


def test_invalid_cidr_notation_raises_error():
    """Verify that invalid CIDR subnets raise InvalidIPAddressError."""
    bad_data = copy.deepcopy(MINIMAL_VALID_FIXTURE)
    bad_data["links"][0]["subnet"] = "192.168.1.0/35"
    with pytest.raises(InvalidIPAddressError, match="Invalid CIDR block"):
        validate_inventory(bad_data)


def test_invalid_vlan_id_raises_schema_error():
    """Verify that out-of-range VLAN IDs (> 4094) trigger SchemaError."""
    bad_data = copy.deepcopy(MINIMAL_VALID_FIXTURE)
    bad_data["devices"][0]["vlans"] = [5000]
    with pytest.raises(SchemaError, match="invalid 802.1Q VLAN ID"):
        validate_inventory(bad_data)


def test_invalid_bandwidth_raises_schema_error():
    """Verify that non-positive bandwidth values trigger SchemaError."""
    bad_data = copy.deepcopy(MINIMAL_VALID_FIXTURE)
    bad_data["links"][0]["bandwidth_mbps"] = 0
    with pytest.raises(SchemaError, match="must be a positive number"):
        validate_inventory(bad_data)
