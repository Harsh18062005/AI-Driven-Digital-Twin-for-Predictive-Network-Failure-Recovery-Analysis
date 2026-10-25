"""Command-Line Interface Demonstration for Network Digital Twin Graph Engine.

Allows interactive inspection and automated CLI execution of:
1. Inventory loading and schema validation
2. NetworkX graph construction
3. Topology summaries and branch audits
4. End-to-end device connectivity checks
5. Shortest path finding
6. Device failure simulation (what-if analysis)
7. Link failure simulation and alternate path recalculation
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Optional

from inventory_loader import load_inventory, InventoryValidationError
from topology import (
    build_graph,
    get_topology_summary,
    list_devices_by_branch,
    device_exists,
    get_device_details,
    print_topology_summary,
    TopologyError,
)
from graph_analysis import (
    check_connectivity,
    find_path,
    find_all_paths,
    find_alternative_paths,
    simulate_device_failure,
    simulate_link_failure,
    get_connected_components,
    get_branch_inventory,
)


def display_menu() -> None:
    """Print the interactive demonstration menu."""
    print("\n" + "=" * 65)
    print("   AI DIGITAL TWIN: NETWORK TOPOLOGY & GRAPH ANALYSIS ENGINE   ")
    print("=" * 65)
    print(" [1]  View Topology Summary (Nodes, Edges, Types, Components)")
    print(" [2]  List Network Devices by Branch")
    print(" [3]  Inspect Specific Device Details")
    print(" [4]  Inspect Branch Inventory & Inter-Branch Uplinks")
    print(" [5]  Check Connectivity between Two Devices")
    print(" [6]  Find Shortest Path between Two Devices")
    print(" [7]  Find All Alternative Paths between Two Devices")
    print(" [8]  Simulate Device Failure (Node Failure & Partition Analysis)")
    print(" [9]  Simulate Link Failure (Edge Failure & Rerouting Analysis)")
    print(" [10] View All Disconnected Components in Current Graph")
    print(" [0]  Exit")
    print("=" * 65)


def run_interactive(inventory_path: Optional[str] = None) -> None:
    """Run the interactive menu loop."""
    print("\nLoading and validating enterprise network inventory...")
    try:
        inv = load_inventory(inventory_path)
        g = build_graph(inv)
        summary = get_topology_summary(g)
        print(f"Loaded: '{summary['network_name']}'")
        print(f"Status: {inv.get('metadata', {}).get('status', 'draft')}")
        print(f"Nodes: {summary['node_count']} | Links: {summary['edge_count']} | Connected: {summary['is_connected']}")
    except Exception as exc:
        print(f"\nCRITICAL ERROR: Failed to load inventory: {exc}")
        sys.exit(1)

    while True:
        display_menu()
        choice = input("Enter option [0-10]: ").strip()

        if choice == "0":
            print("\nExiting Network Digital Twin CLI. Goodbye!")
            break

        elif choice == "1":
            print()
            print_topology_summary(g)

        elif choice == "2":
            branches = list_devices_by_branch(g)
            print("\nDEVICES BY BRANCH:")
            for branch, devices in branches.items():
                print(f"\n* {branch} ({len(devices)} devices):")
                for d in devices:
                    d_data = g.nodes[d]
                    print(f"    - {d:10s} [{d_data.get('device_type'):6s}] {d_data.get('hostname'):15s} (Role: {d_data.get('role')})")

        elif choice == "3":
            dev_id = input("\nEnter Device ID (e.g. HQ-R1, BR1-PC1): ").strip()
            if not device_exists(g, dev_id):
                print(f"Error: Device '{dev_id}' not found.")
                continue
            details = get_device_details(g, dev_id)
            print(f"\nDEVICE DETAILS FOR {dev_id}:")
            for k, v in details.items():
                print(f"  {k:15s}: {v}")

        elif choice == "4":
            branch = input("\nEnter Branch Name (e.g. Headquarters, Branch 1 (North)): ").strip()
            try:
                res = get_branch_inventory(g, branch)
                print(f"\nBRANCH: {res['branch_name']}")
                print(f"Total Devices: {res['device_count']}")
                print(f"Internal Links: {res['internal_links_count']}")
                for l in res['internal_links']:
                    print(f"  - {l['link_id']}: {l['endpoints'][0]} <-> {l['endpoints'][1]} ({l['role']})")
                print(f"External Uplinks: {res['external_links_count']}")
                for l in res['external_links']:
                    print(f"  - {l['link_id']}: {l['endpoints'][0]} <-> {l['endpoints'][1]} (Dest: {l.get('destination_branch')})")
            except Exception as exc:
                print(f"Error: {exc}")

        elif choice == "5":
            src = input("\nEnter Source Device ID (e.g. BR1-PC1): ").strip()
            dst = input("Enter Target Device ID (e.g. HQ-SRV1): ").strip()
            try:
                connected = check_connectivity(g, src, dst)
                print(f"\nConnectivity from '{src}' to '{dst}': {'CONNECTED (Path exists)' if connected else 'DISCONNECTED (No path)'}")
            except Exception as exc:
                print(f"Error: {exc}")

        elif choice == "6":
            src = input("\nEnter Source Device ID (e.g. BR1-PC1): ").strip()
            dst = input("Enter Target Device ID (e.g. HQ-SRV1): ").strip()
            try:
                path = find_path(g, src, dst)
                if path:
                    print(f"\nShortest Path ({len(path) - 1} hops):")
                    print("  " + " -> ".join(path))
                else:
                    print(f"\nNo path exists between '{src}' and '{dst}'.")
            except Exception as exc:
                print(f"Error: {exc}")

        elif choice == "7":
            src = input("\nEnter Source Device ID (e.g. BR1-PC1): ").strip()
            dst = input("Enter Target Device ID (e.g. HQ-SRV1): ").strip()
            try:
                paths = find_all_paths(g, src, dst)
                print(f"\nFound {len(paths)} loop-free path(s) between '{src}' and '{dst}':")
                for i, p in enumerate(paths, 1):
                    print(f"  Path {i} ({len(p) - 1} hops): {' -> '.join(p)}")
            except Exception as exc:
                print(f"Error: {exc}")

        elif choice == "8":
            dev_id = input("\nEnter Device ID to simulate failure on (e.g. HQ-R1, BR1-R1): ").strip()
            try:
                sim = simulate_device_failure(g, dev_id)
                print(f"\n--- SIMULATION RESULTS: FAILURE OF {dev_id} ---")
                print(f"Device Role       : {sim['device_info']['role']} in {sim['device_info']['branch']}")
                print(f"Severed Links     : {sim['severed_links_count']}")
                for l in sim['severed_links']:
                    print(f"  - Cut link to '{l['neighbor']}' (Link ID: {l['link_id']})")
                print(f"Network Partitioned: {sim['is_partitioned']}")
                print(f"Components Before : {sim['baseline_components_count']} -> After: {sim['post_failure_components_count']}")
                if sim['isolated_devices']:
                    print(f"Newly Isolated Nodes: {', '.join(sim['isolated_devices'])}")
                print(f"Surviving Partitions ({len(sim['partitions'])}):")
                for i, part in enumerate(sim['partitions'], 1):
                    print(f"  Group {i} ({len(part)} devices): {', '.join(part[:6])}{'...' if len(part) > 6 else ''}")
            except Exception as exc:
                print(f"Error: {exc}")

        elif choice == "9":
            link_input = input("\nEnter Link ID (e.g. WAN-HQ-BR1) OR 'src dst': ").strip()
            try:
                if " " in link_input:
                    src, dst = link_input.split(maxsplit=1)
                    sim = simulate_link_failure(g, device_a=src, device_b=dst)
                else:
                    sim = simulate_link_failure(g, link_id=link_input)
                
                print(f"\n--- SIMULATION RESULTS: FAILURE OF LINK '{sim['failed_link_id']}' ---")
                print(f"Severed Endpoints   : {sim['endpoints'][0]} <--> {sim['endpoints'][1]}")
                print(f"Link Type & Role    : {sim['link_info']['link_type']} ({sim['link_info']['role']})")
                print(f"Is Bridge (Breaks Net): {sim['is_bridge']}")
                print(f"Alternate Path Found: {sim['alternate_path_found']}")
                if sim['alternate_path_found']:
                    print(f"Alternate Reroute   : {' -> '.join(sim['alternate_path'])} ({sim['alternate_path_hop_count']} hops)")
                else:
                    print("Endpoints are completely isolated from one another!")
            except Exception as exc:
                print(f"Error: {exc}")

        elif choice == "10":
            components = get_connected_components(g)
            print(f"\nCONNECTED COMPONENTS ({len(components)} total):")
            for idx, comp in enumerate(components, 1):
                print(f"  Partition {idx} ({len(comp)} devices): {', '.join(sorted(list(comp)))}")

        else:
            print("Invalid option. Please enter a number between 0 and 10.")


def main() -> None:
    """Parse CLI arguments or launch interactive mode."""
    parser = argparse.ArgumentParser(
        description="Network Digital Twin Topology & Graph Analysis Tool"
    )
    parser.add_argument("--inventory", type=str, default=None, help="Path to network.json inventory file")
    parser.add_argument("--summary", action="store_true", help="Print topology summary and exit")
    parser.add_argument("--devices", action="store_true", help="List all devices by branch and exit")
    parser.add_argument("--path", nargs=2, metavar=("SRC", "DST"), help="Find shortest path between SRC and DST")
    parser.add_argument("--fail-device", type=str, metavar="DEV_ID", help="Simulate failure of device DEV_ID")
    parser.add_argument("--fail-link", type=str, metavar="LINK_ID", help="Simulate failure of link LINK_ID")

    args = parser.parse_args()

    # If flags were provided, run non-interactively
    if args.summary or args.devices or args.path or args.fail_device or args.fail_link:
        try:
            inv = load_inventory(args.inventory)
            g = build_graph(inv)
        except Exception as exc:
            print(f"Error loading network inventory: {exc}", file=sys.stderr)
            sys.exit(1)

        if args.summary:
            print_topology_summary(g)
        if args.devices:
            branches = list_devices_by_branch(g)
            for b, devs in branches.items():
                print(f"{b}: {', '.join(devs)}")
        if args.path:
            p = find_path(g, args.path[0], args.path[1])
            if p:
                print(f"Path from {args.path[0]} to {args.path[1]}: {' -> '.join(p)}")
            else:
                print(f"No path found between {args.path[0]} and {args.path[1]}")
        if args.fail_device:
            res = simulate_device_failure(g, args.fail_device)
            print(f"Failure of {args.fail_device}: Partitioned={res['is_partitioned']}, Post-Components={res['post_failure_components_count']}")
        if args.fail_link:
            res = simulate_link_failure(g, link_id=args.fail_link)
            print(f"Failure of {args.fail_link}: AlternatePathFound={res['alternate_path_found']}, IsBridge={res['is_bridge']}")
    else:
        run_interactive(args.inventory)


if __name__ == "__main__":
    main()
