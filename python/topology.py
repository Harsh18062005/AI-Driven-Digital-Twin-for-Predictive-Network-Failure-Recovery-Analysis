"""Network Topology Graph Builder using NetworkX.

Constructs an undirected NetworkX graph from validated network inventory data.
Provides query and inspection utilities for devices, links, branches, and topology metadata.

MODEL LIMITATIONS AND ASSUMPTIONS:
1. Physical vs. Logical: An edge in this graph represents a physical or Layer 2/3 link.
   Topological connectivity in the graph is a necessary condition for network communication,
   but NOT a sufficient condition. Real IP communication depends on VLAN tagging,
   subnet matching, default gateways, dynamic routing convergence (OSPF), interface states,
   and Access Control Lists (ACLs).
2. Undirected Representation: Ethernet and point-to-point serial communication is bi-directional
   at the physical link layer. Directional traffic filtering (e.g. firewalls/asymmetric ACLs)
   is not modeled in this Layer-1/2 topology graph.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple
import networkx as nx

from inventory_loader import load_inventory, InventoryValidationError


class TopologyError(Exception):
    """Base exception for topology graph operations."""
    pass


class DeviceNotFoundError(TopologyError):
    """Raised when an operation queries a device ID that does not exist in the graph."""
    pass


class LinkNotFoundError(TopologyError):
    """Raised when an operation queries a link that does not exist in the graph."""
    pass


def build_graph(inventory: Dict[str, Any]) -> nx.Graph:
    """Build an undirected NetworkX graph from a validated network inventory dictionary.

    Args:
        inventory: Validated dictionary containing 'metadata', 'devices', and 'links'.

    Returns:
        An nx.Graph instance with node and edge attributes populated.

    Raises:
        TopologyError: If inventory structure is invalid or cannot be converted to a graph.
    """
    if not isinstance(inventory, dict) or "devices" not in inventory or "links" not in inventory:
        raise TopologyError("Invalid inventory structure: must contain 'devices' and 'links'")

    graph = nx.Graph()

    # Attach graph-level metadata
    metadata = inventory.get("metadata", {})
    graph.graph["network_name"] = metadata.get("network_name", "Enterprise Network")
    graph.graph["version"] = metadata.get("version", "1.0.0")
    graph.graph["status"] = metadata.get("status", "draft")

    # Add Nodes
    for dev in inventory["devices"]:
        dev_id = dev["device_id"]
        # Store all device attributes on the node
        graph.add_node(
            dev_id,
            device_id=dev_id,
            hostname=dev.get("hostname", dev_id),
            device_type=dev.get("device_type", "Unknown"),
            branch=dev.get("branch", "Unknown"),
            role=dev.get("role", "Unknown"),
            model=dev.get("model", "Generic"),
            management_ip=dev.get("management_ip"),
            vlans=dev.get("vlans", []),
            interfaces=dev.get("interfaces", []),
            status=dev.get("status", "active"),
        )

    # Add Edges
    for link in inventory["links"]:
        u = link["source_device"]
        v = link["target_device"]
        link_id = link["link_id"]

        graph.add_edge(
            u,
            v,
            link_id=link_id,
            source_device=u,
            source_interface=link.get("source_interface", ""),
            target_device=v,
            target_interface=link.get("target_interface", ""),
            link_type=link.get("link_type", "Access"),
            media=link.get("media", "Copper Straight-Through"),
            subnet=link.get("subnet"),
            bandwidth_mbps=link.get("bandwidth_mbps", 100),
            status=link.get("status", "up"),
            role=link.get("role", "General Link"),
        )

    return graph


def device_exists(graph: nx.Graph, device_id: str) -> bool:
    """Check whether a device ID exists as a node in the graph."""
    return graph.has_node(device_id)


def link_exists(graph: nx.Graph, device_a: str, device_b: str) -> bool:
    """Check whether an edge exists between two device IDs."""
    return graph.has_edge(device_a, device_b)


def get_device_details(graph: nx.Graph, device_id: str) -> Dict[str, Any]:
    """Retrieve all metadata attributes for a given device.

    Args:
        graph: The network graph.
        device_id: Unique device identifier.

    Returns:
        Dictionary of device metadata attributes.

    Raises:
        DeviceNotFoundError: If the device does not exist in the graph.
    """
    if not device_exists(graph, device_id):
        raise DeviceNotFoundError(f"Device '{device_id}' does not exist in the network topology.")
    return dict(graph.nodes[device_id])


def get_link_details(graph: nx.Graph, device_a: str, device_b: str) -> Dict[str, Any]:
    """Retrieve metadata for the link between two connected devices.

    Args:
        graph: The network graph.
        device_a: First endpoint device ID.
        device_b: Second endpoint device ID.

    Returns:
        Dictionary of link metadata attributes.

    Raises:
        LinkNotFoundError: If no edge exists between the two devices.
    """
    if not graph.has_edge(device_a, device_b):
        raise LinkNotFoundError(f"No direct link exists between '{device_a}' and '{device_b}'.")
    return dict(graph.edges[device_a, device_b])


def get_link_by_id(graph: nx.Graph, link_id: str) -> Tuple[str, str, Dict[str, Any]]:
    """Find and return an edge by its link_id attribute.

    Returns:
        Tuple of (source_device, target_device, link_attributes).

    Raises:
        LinkNotFoundError: If no link matches the link_id.
    """
    for u, v, data in graph.edges(data=True):
        if data.get("link_id") == link_id:
            return (u, v, dict(data))
    raise LinkNotFoundError(f"Link ID '{link_id}' was not found in the topology.")


def list_devices_by_branch(graph: nx.Graph, branch_name: Optional[str] = None) -> Dict[str, List[str]]:
    """Group device IDs by branch.

    Args:
        graph: The network graph.
        branch_name: Optional branch filter. If provided, returns only devices in that branch.

    Returns:
        Dictionary mapping branch names to lists of device IDs.
    """
    branch_map: Dict[str, List[str]] = {}
    for node, data in graph.nodes(data=True):
        branch = data.get("branch", "Unknown")
        if branch_name is not None and branch.lower() != branch_name.lower():
            continue
        if branch not in branch_map:
            branch_map[branch] = []
        branch_map[branch].append(node)

    for b in branch_map:
        branch_map[b].sort()
    return branch_map


def get_node_and_edge_counts(graph: nx.Graph) -> Tuple[int, int]:
    """Return the total number of nodes and edges in the graph."""
    return graph.number_of_nodes(), graph.number_of_edges()


def validate_graph(graph: nx.Graph) -> bool:
    """Validate that the constructed graph is non-empty and well-formed.

    Returns:
        True if valid.

    Raises:
        TopologyError: If graph has no nodes or contains invalid data.
    """
    if graph.number_of_nodes() == 0:
        raise TopologyError("Topology graph contains zero nodes.")
    for node, data in graph.nodes(data=True):
        if not data.get("device_type"):
            raise TopologyError(f"Node '{node}' is missing 'device_type' attribute.")
    for u, v, data in graph.edges(data=True):
        if not data.get("link_id"):
            raise TopologyError(f"Edge ({u}, {v}) is missing 'link_id' attribute.")
    return True


def get_topology_summary(graph: nx.Graph) -> Dict[str, Any]:
    """Generate a structured summary of the topology graph."""
    node_count, edge_count = get_node_and_edge_counts(graph)
    branches = list_devices_by_branch(graph)
    
    device_type_counts: Dict[str, int] = {}
    for _, data in graph.nodes(data=True):
        dtype = data.get("device_type", "Unknown")
        device_type_counts[dtype] = device_type_counts.get(dtype, 0) + 1

    link_type_counts: Dict[str, int] = {}
    for _, _, data in graph.edges(data=True):
        ltype = data.get("link_type", "Unknown")
        link_type_counts[ltype] = link_type_counts.get(ltype, 0) + 1

    is_connected = nx.is_connected(graph) if node_count > 0 else False
    num_components = nx.number_connected_components(graph) if node_count > 0 else 0

    return {
        "network_name": graph.graph.get("network_name", "Enterprise Network"),
        "node_count": node_count,
        "edge_count": edge_count,
        "is_connected": is_connected,
        "connected_components_count": num_components,
        "device_types": device_type_counts,
        "link_types": link_type_counts,
        "branches": {b: len(devs) for b, devs in branches.items()},
    }


def print_topology_summary(graph: nx.Graph) -> None:
    """Print an eye-readable summary of the topology."""
    summary = get_topology_summary(graph)
    print("=" * 60)
    print(f"NETWORK TOPOLOGY: {summary['network_name']}")
    print("=" * 60)
    print(f"Total Devices (Nodes): {summary['node_count']}")
    print(f"Total Links (Edges)  : {summary['edge_count']}")
    print(f"Fully Connected      : {summary['is_connected']} ({summary['connected_components_count']} component(s))")
    print("\nDevice Breakdown:")
    for dtype, count in sorted(summary['device_types'].items()):
        print(f"  - {dtype:10s}: {count}")
    print("\nLink Breakdown:")
    for ltype, count in sorted(summary['link_types'].items()):
        print(f"  - {ltype:10s}: {count}")
    print("\nBranch Allocations:")
    for branch, count in sorted(summary['branches'].items()):
        print(f"  - {branch:22s}: {count} devices")
    print("=" * 60)


if __name__ == "__main__":
    inv = load_inventory()
    g = build_graph(inv)
    validate_graph(g)
    print_topology_summary(g)
