"""Graph-Theoretic Analysis and Failure Simulation Engine.

Provides topological query algorithms and non-destructive failure simulations
for enterprise network digital twins.

DISCLAIMER:
These algorithms operate purely at the graph abstraction layer. They model
graph reachability, path existence, and partition consequences upon node/edge
removal. Real-world network behavior also depends on dynamic routing protocol
timers, convergence delays, spanning-tree state transitions, and ACL enforcement.
Baseline graphs are NEVER mutated during simulations.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple
import networkx as nx

from topology import (
    DeviceNotFoundError,
    LinkNotFoundError,
    TopologyError,
    device_exists,
    get_link_by_id,
    list_devices_by_branch,
)


def check_connectivity(graph: nx.Graph, source_id: str, target_id: str) -> bool:
    """Check whether a topological path exists between two network devices.

    Args:
        graph: The network graph.
        source_id: Originating device ID.
        target_id: Destination device ID.

    Returns:
        True if an active path exists between source and target, False otherwise.

    Raises:
        DeviceNotFoundError: If either device ID does not exist in the graph.
    """
    if not device_exists(graph, source_id):
        raise DeviceNotFoundError(f"Source device '{source_id}' does not exist.")
    if not device_exists(graph, target_id):
        raise DeviceNotFoundError(f"Target device '{target_id}' does not exist.")

    if source_id == target_id:
        return True

    return nx.has_path(graph, source_id, target_id)


def find_path(
    graph: nx.Graph,
    source_id: str,
    target_id: str,
    weight: Optional[str] = None
) -> Optional[List[str]]:
    """Find a shortest path between two devices.

    Args:
        graph: The network graph.
        source_id: Originating device ID.
        target_id: Destination device ID.
        weight: Optional edge attribute to use as weight (e.g., 'bandwidth_mbps').

    Returns:
        A list of device IDs representing the path, or None if no path exists.

    Raises:
        DeviceNotFoundError: If either device ID is not found.
    """
    if not device_exists(graph, source_id):
        raise DeviceNotFoundError(f"Source device '{source_id}' does not exist.")
    if not device_exists(graph, target_id):
        raise DeviceNotFoundError(f"Target device '{target_id}' does not exist.")

    if source_id == target_id:
        return [source_id]

    try:
        return list(nx.shortest_path(graph, source=source_id, target=target_id, weight=weight))
    except nx.NetworkXNoPath:
        return None


def find_all_paths(
    graph: nx.Graph,
    source_id: str,
    target_id: str,
    cutoff: Optional[int] = 8
) -> List[List[str]]:
    """Find all simple (loop-free) paths between two devices up to a cutoff length.

    Args:
        graph: The network graph.
        source_id: Originating device ID.
        target_id: Destination device ID.
        cutoff: Maximum path length (depth limit). Defaults to 8.

    Returns:
        List of paths (each path is a list of device IDs).
    """
    if not device_exists(graph, source_id):
        raise DeviceNotFoundError(f"Source device '{source_id}' does not exist.")
    if not device_exists(graph, target_id):
        raise DeviceNotFoundError(f"Target device '{target_id}' does not exist.")

    try:
        return list(nx.all_simple_paths(graph, source=source_id, target=target_id, cutoff=cutoff))
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return []


def find_alternative_paths(
    graph: nx.Graph,
    source_id: str,
    target_id: str,
    excluded_link: Optional[Tuple[str, str]] = None,
    excluded_device: Optional[str] = None,
) -> List[List[str]]:
    """Determine whether alternative paths exist when a specific link or device is removed.

    NOTE: The baseline graph is copied and never modified.

    Args:
        graph: Baseline network graph.
        source_id: Source device ID.
        target_id: Destination device ID.
        excluded_link: Optional tuple (device_a, device_b) of the link to exclude.
        excluded_device: Optional device ID to exclude.

    Returns:
        List of available paths in the simulated failure topology.
    """
    if not device_exists(graph, source_id):
        raise DeviceNotFoundError(f"Source device '{source_id}' does not exist.")
    if not device_exists(graph, target_id):
        raise DeviceNotFoundError(f"Target device '{target_id}' does not exist.")

    # If the excluded device is the source or destination, no path can exist
    if excluded_device and excluded_device in (source_id, target_id):
        return []

    # Create isolated copy for simulation
    sim_graph = graph.copy()

    if excluded_device and sim_graph.has_node(excluded_device):
        sim_graph.remove_node(excluded_device)

    if excluded_link:
        u, v = excluded_link
        if sim_graph.has_edge(u, v):
            sim_graph.remove_edge(u, v)

    if not sim_graph.has_node(source_id) or not sim_graph.has_node(target_id):
        return []

    try:
        return list(nx.all_simple_paths(sim_graph, source=source_id, target=target_id, cutoff=8))
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return []


def get_connected_components(graph: nx.Graph) -> List[Set[str]]:
    """Identify isolated groups of devices (connected components) in the graph.

    Returns:
        A list of sets, where each set contains device IDs in one connected partition,
        sorted in descending order by component size.
    """
    if graph.number_of_nodes() == 0:
        return []
    components = [set(c) for c in nx.connected_components(graph)]
    components.sort(key=len, reverse=True)
    return components


def simulate_device_failure(graph: nx.Graph, failed_device_id: str) -> Dict[str, Any]:
    """Simulate the failure of a single network device on an isolated graph copy.

    Args:
        graph: Baseline network graph (NOT modified).
        failed_device_id: ID of the device to fail.

    Returns:
        Simulation report dictionary detailing:
        - device_id and its role/branch
        - severed_links: List of links lost with the device
        - baseline_components: Component count before failure
        - post_failure_components: Component count after failure
        - partitions: Groupings of reachable nodes post-failure
        - isolated_devices: Devices with degree 0
        - is_partitioned: Whether the failure split the network into disjoint pieces

    Raises:
        DeviceNotFoundError: If failed_device_id does not exist.
    """
    if not device_exists(graph, failed_device_id):
        raise DeviceNotFoundError(f"Cannot simulate failure: device '{failed_device_id}' does not exist.")

    dev_data = dict(graph.nodes[failed_device_id])
    
    # Identify severed links
    severed_links = []
    for neighbor in graph.neighbors(failed_device_id):
        edge_data = dict(graph.edges[failed_device_id, neighbor])
        severed_links.append({
            "neighbor": neighbor,
            "link_id": edge_data.get("link_id"),
            "link_type": edge_data.get("link_type"),
            "role": edge_data.get("role"),
        })

    # Clone graph and remove target node
    sim_graph = graph.copy()
    sim_graph.remove_node(failed_device_id)

    baseline_components = nx.number_connected_components(graph)
    post_components = get_connected_components(sim_graph)
    
    # Detect newly isolated nodes (nodes with 0 remaining connections)
    isolated_devices = [node for node, degree in sim_graph.degree() if degree == 0]

    return {
        "failed_device_id": failed_device_id,
        "device_info": {
            "hostname": dev_data.get("hostname"),
            "device_type": dev_data.get("device_type"),
            "branch": dev_data.get("branch"),
            "role": dev_data.get("role"),
        },
        "severed_links_count": len(severed_links),
        "severed_links": severed_links,
        "baseline_components_count": baseline_components,
        "post_failure_components_count": len(post_components),
        "is_partitioned": len(post_components) > 1,
        "isolated_devices": isolated_devices,
        "partitions": [sorted(list(c)) for c in post_components],
        "remaining_nodes_count": sim_graph.number_of_nodes(),
        "remaining_edges_count": sim_graph.number_of_edges(),
    }


def simulate_link_failure(
    graph: nx.Graph,
    device_a: Optional[str] = None,
    device_b: Optional[str] = None,
    link_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Simulate the failure of a specific network link on an isolated graph copy.

    Args:
        graph: Baseline network graph (NOT modified).
        device_a: First endpoint device ID (optional if link_id is supplied).
        device_b: Second endpoint device ID (optional if link_id is supplied).
        link_id: Unique link identifier (optional if device endpoints are supplied).

    Returns:
        Simulation report dictionary detailing:
        - link_id, endpoints, link_type, bandwidth
        - alternate_path_found: True if traffic between endpoints can still be rerouted
        - alternate_path: Shortest path between endpoints in degraded topology
        - baseline_components: Component count before failure
        - post_failure_components: Component count after failure
        - is_partitioned: Whether this link was a bridge that broke connectivity

    Raises:
        LinkNotFoundError: If the specified link does not exist.
    """
    # Resolve link endpoints
    if link_id is not None:
        u, v, link_data = get_link_by_id(graph, link_id)
    elif device_a is not None and device_b is not None:
        if not graph.has_edge(device_a, device_b):
            raise LinkNotFoundError(f"No link exists between '{device_a}' and '{device_b}'.")
        u, v = device_a, device_b
        link_data = dict(graph.edges[u, v])
        link_id = link_data.get("link_id", f"{u}<->{v}")
    else:
        raise ValueError("Must provide either 'link_id' or both 'device_a' and 'device_b'.")

    # Clone graph and remove the link
    sim_graph = graph.copy()
    sim_graph.remove_edge(u, v)

    # Check whether an alternate path exists between the severed endpoints
    try:
        alt_path = list(nx.shortest_path(sim_graph, source=u, target=v))
        alt_found = True
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        alt_path = None
        alt_found = False

    baseline_components = nx.number_connected_components(graph)
    post_components = get_connected_components(sim_graph)

    return {
        "failed_link_id": link_id,
        "endpoints": [u, v],
        "link_info": {
            "link_type": link_data.get("link_type"),
            "media": link_data.get("media"),
            "subnet": link_data.get("subnet"),
            "bandwidth_mbps": link_data.get("bandwidth_mbps"),
            "role": link_data.get("role"),
        },
        "alternate_path_found": alt_found,
        "alternate_path": alt_path,
        "alternate_path_hop_count": (len(alt_path) - 1) if alt_path else None,
        "baseline_components_count": baseline_components,
        "post_failure_components_count": len(post_components),
        "is_bridge": len(post_components) > baseline_components,
        "partitions": [sorted(list(c)) for c in post_components],
    }


def get_branch_inventory(graph: nx.Graph, branch_name: str) -> Dict[str, Any]:
    """Retrieve detailed inventory and connections for all devices in a specified branch.

    Args:
        graph: The network graph.
        branch_name: Name of the branch (case-insensitive).

    Returns:
        Dictionary containing branch devices, internal links, and external uplink links.
    """
    branch_devices: List[str] = []
    for node, data in graph.nodes(data=True):
        if data.get("branch", "").lower() == branch_name.lower():
            branch_devices.append(node)

    if not branch_devices:
        available_branches = sorted(list(set(d.get("branch", "") for _, d in graph.nodes(data=True))))
        raise ValueError(f"Unknown branch '{branch_name}'. Available branches: {', '.join(available_branches)}")

    branch_set = set(branch_devices)
    internal_links = []
    external_links = []

    for u in branch_devices:
        for v in graph.neighbors(u):
            # To avoid duplicates in undirected edges, ensure u < v for internal
            edge_data = dict(graph.edges[u, v])
            link_entry = {
                "link_id": edge_data.get("link_id"),
                "endpoints": [u, v],
                "link_type": edge_data.get("link_type"),
                "role": edge_data.get("role"),
            }
            if v in branch_set:
                if u < v:
                    internal_links.append(link_entry)
            else:
                link_entry["destination_branch"] = graph.nodes[v].get("branch", "Unknown")
                external_links.append(link_entry)

    return {
        "branch_name": branch_name,
        "device_count": len(branch_devices),
        "devices": [dict(graph.nodes[d]) for d in branch_devices],
        "internal_links_count": len(internal_links),
        "internal_links": internal_links,
        "external_links_count": len(external_links),
        "external_links": external_links,
    }


def get_graph_summary(graph: nx.Graph) -> Dict[str, Any]:
    """Return a comprehensive summary of the baseline graph state."""
    components = get_connected_components(graph)
    branch_map = list_devices_by_branch(graph)
    
    return {
        "network_name": graph.graph.get("network_name", "Enterprise Network"),
        "total_nodes": graph.number_of_nodes(),
        "total_edges": graph.number_of_edges(),
        "is_connected": nx.is_connected(graph) if graph.number_of_nodes() > 0 else False,
        "components_count": len(components),
        "branches_represented": sorted(list(branch_map.keys())),
        "largest_component_size": len(components[0]) if components else 0,
    }


if __name__ == "__main__":
    from inventory_loader import load_inventory
    from topology import build_graph

    inv = load_inventory()
    g = build_graph(inv)

    print("Testing Graph Analysis Functions...")
    # 1. Path test
    p = find_path(g, "BR1-PC1", "HQ-SRV1")
    print(f"Path BR1-PC1 -> HQ-SRV1: {' -> '.join(p)}")

    # 2. Simulate Link Failure on Primary WAN link WAN-HQ-BR1
    print("\nSimulating failure on primary link 'WAN-HQ-BR1'...")
    res = simulate_link_failure(g, link_id="WAN-HQ-BR1")
    print(f"Alternate path found: {res['alternate_path_found']}")
    print(f"New path between endpoints: {' -> '.join(res['alternate_path'])}")
    print(f"Network partitioned: {res['is_bridge']}")

    # 3. Simulate Node Failure on Core Router HQ-R1
    print("\nSimulating failure on core router 'HQ-R1'...")
    n_res = simulate_device_failure(g, "HQ-R1")
    print(f"Severed links: {n_res['severed_links_count']}")
    print(f"Post-failure components: {n_res['post_failure_components_count']}")
    print(f"Network partitioned: {n_res['is_partitioned']}")
