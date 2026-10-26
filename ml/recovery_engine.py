"""Prescriptive Self-Healing and Network Failure Recovery Engine.

Evaluates digital twin network state and prescribes automated recovery playbooks,
optimal rerouting paths, OSPF dynamic cost dampening, and Cisco IOS configuration
remediation scripts to achieve self-healing network resilience.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root and python/ to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
PYTHON_DIR = PROJECT_ROOT / "python"
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

from typing import Any, Dict, List, Optional, Tuple
import networkx as nx

from inventory_loader import load_inventory
from topology import build_graph, get_device_details, get_link_by_id
from graph_analysis import (
    find_alternative_paths,
    simulate_device_failure,
    simulate_link_failure,
)
from ml.config import NETWORK_JSON_PATH, SERIAL_LINKS, WAN_LINK_IDS


class PrescriptiveRecoveryEngine:
    """Prescribes self-healing recovery actions, rerouting paths, and Cisco IOS commands."""

    def __init__(self, inventory_path: Optional[Path] = None):
        """Initialize recovery engine with baseline NetworkX graph."""
        self.inventory_path = inventory_path or NETWORK_JSON_PATH
        self.inventory = load_inventory(self.inventory_path)
        self.graph = build_graph(self.inventory)

    def _calculate_path_metrics(
        self,
        path: List[str],
    ) -> Dict[str, Any]:
        """Compute bottleneck bandwidth and estimated latency along an alternate path."""
        G = self.graph
        min_bw = float("inf")
        total_latency = 0.0
        hops = len(path) - 1

        for i in range(len(path) - 1):
            u = path[i]
            v = path[i + 1]
            if G.has_edge(u, v):
                edge_data = G.edges[u, v]
                bw = float(edge_data.get("bandwidth_mbps", 100.0))
                min_bw = min(min_bw, bw)

                # Estimate hop latency
                link_id = edge_data.get("link_id", "")
                if link_id in SERIAL_LINKS:
                    total_latency += 35.0
                elif edge_data.get("link_type") == "WAN":
                    total_latency += 12.0
                else:
                    total_latency += 1.0

        return {
            "path": path,
            "hop_count": hops,
            "bottleneck_bandwidth_mbps": min_bw if min_bw != float("inf") else 0.0,
            "estimated_latency_ms": round(total_latency, 1),
        }

    def _select_optimal_path(
        self,
        candidate_paths: List[List[str]],
    ) -> Optional[Dict[str, Any]]:
        """Rank and select the optimal alternative path based on bandwidth, hops, and latency."""
        if not candidate_paths:
            return None

        evaluated = [self._calculate_path_metrics(p) for p in candidate_paths]

        # Sorting strategy: prioritize higher bottleneck bandwidth, then fewer hops, then lowest latency
        evaluated.sort(
            key=lambda x: (-x["bottleneck_bandwidth_mbps"], x["hop_count"], x["estimated_latency_ms"])
        )
        return evaluated[0]

    def _generate_link_ios_commands(
        self,
        link_id: str,
        source: str,
        target: str,
        alternate_path: Optional[List[str]],
    ) -> List[str]:
        """Generate exact Cisco IOS configuration remediation commands for link failure."""
        G = self.graph
        edge_data = dict(G.edges[source, target])
        src_iface = edge_data.get("source_interface", "Gig0/1")
        tgt_iface = edge_data.get("target_interface", "Gig0/1")

        commands = [
            f"! === CISCO IOS AUTOMATED RECOVERY SCRIPT FOR LINK: {link_id} ===",
            f"! Endpoints: {source} ({src_iface}) <--> {target} ({tgt_iface})",
            "!",
        ]

        if alternate_path:
            # Graceful traffic dampening and OSPF cost escalation
            commands.extend([
                f"! 1. Prevent black-holing: Escalate OSPF metric on {source} interface {src_iface}",
                f"{source}# configure terminal",
                f"{source}(config)# interface {src_iface}",
                f"{source}(config-if)# ip ospf cost 65535",
                f"{source}(config-if)# description [AI-DIGITAL-TWIN-FAILOVER] Deprecating link {link_id}",
                f"{source}(config-if)# exit",
                "!",
                f"! 2. Administratively isolate flapping or degraded interface on {source}",
                f"{source}(config)# interface {src_iface}",
                f"{source}(config-if)# shutdown",
                f"{source}(config-if)# exit",
                "!",
                f"! 3. Mirror shutdown on peer device {target}",
                f"{target}# configure terminal",
                f"{target}(config)# interface {tgt_iface}",
                f"{target}(config-if)# ip ospf cost 65535",
                f"{target}(config-if)# shutdown",
                f"{target}(config-if)# exit",
                "!",
                f"! 4. Force OSPF Dijkstra recalculation and clear routing cache",
                f"{source}# clear ip ospf process",
                f"{target}# clear ip ospf process",
                "!",
                f"! 5. Verify convergence onto alternate path: {' -> '.join(alternate_path)}",
                f"{source}# show ip route ospf",
                f"{source}# show ip ospf neighbor",
            ])
        else:
            commands.extend([
                f"! CRITICAL NOTICE: No topological alternative path exists (Access or Bridge link)",
                f"! 1. Administratively reset interface to clear transceiver state on {source}",
                f"{source}# configure terminal",
                f"{source}(config)# interface {src_iface}",
                f"{source}(config-if)# shutdown",
                f"{source}(config-if)# no shutdown",
                f"{source}(config-if)# exit",
                "!",
                f"! 2. Check physical cable/transceiver diagnostics",
                f"{source}# show interfaces {src_iface} status",
                f"{source}# show interfaces {src_iface} counters errors",
            ])

        return commands

    def _generate_device_ios_commands(
        self,
        device_id: str,
        device_type: str,
        severed_links: List[Dict[str, Any]],
    ) -> List[str]:
        """Generate Cisco IOS remediation commands for device outage."""
        commands = [
            f"! === CISCO IOS INCIDENT PLAYBOOK FOR FAILED DEVICE: {device_id} ({device_type}) ===",
            "!",
        ]

        if device_type == "Router":
            commands.extend([
                f"! 1. Quorum and OSPF neighbor dampening across neighboring peers",
            ])
            for link in severed_links:
                nbr = link["neighbor"]
                commands.extend([
                    f"! Neighbor {nbr}: Terminate stale OSPF adjacency to {device_id}",
                    f"{nbr}# configure terminal",
                    f"{nbr}(config)# router ospf 1",
                    f"{nbr}(config-router)# passive-interface default",
                    f"{nbr}(config-router)# exit",
                    f"{nbr}# clear ip ospf neighbor",
                    "!",
                ])
            commands.extend([
                f"! 2. Activate Standby Default Gateway (HSRP/VRRP) on secondary branch router if available",
                f"! 3. Re-route critical traffic via surviving branch cross-tie links",
            ])
        elif device_type == "Switch":
            commands.extend([
                f"! Access/Distribution Switch Failure: All connected access hosts and trunks down",
                f"! 1. Verify spanning-tree root bridge re-election on adjacent core router",
                f"! 2. Migrate high-priority server/admin cables to spare rack switch",
            ])
        elif device_type == "Server":
            commands.extend([
                f"! Central Server Failure: {device_id}",
                f"! 1. Update Core Gateway DNS/DHCP forwarding helper-address to standby server (HQ-SRV2)",
                f"HQ-R1# configure terminal",
                f"HQ-R1(config)# interface GigabitEthernet0/0.30",
                f"HQ-R1(config-subif)# ip helper-address 10.10.30.20",
                f"HQ-R1(config-subif)# exit",
            ])
        else:
            commands.extend([
                f"! Host PC failure: {device_id}. Non-critical leaf node.",
                f"! Verify DHCP lease and physical Ethernet link state.",
            ])

        return commands

    def recommend_link_recovery(
        self,
        link_id: str,
        prediction_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Prescribe a complete self-healing recovery plan for a degraded or failed link.

        Args:
            link_id: The link identifier (e.g. 'WAN-HQ-BR1').
            prediction_result: Optional prediction dictionary from FailurePredictor.

        Returns:
            Structured recovery plan dictionary.
        """
        # Run non-destructive failure simulation from python/graph_analysis.py
        sim_res = simulate_link_failure(self.graph, link_id=link_id)
        u, v = sim_res["endpoints"]

        # Search all alternate paths
        alt_paths = find_alternative_paths(self.graph, source_id=u, target_id=v, excluded_link=(u, v))
        optimal_route = self._select_optimal_path(alt_paths)

        has_alt = optimal_route is not None
        is_wan = link_id in WAN_LINK_IDS

        if has_alt:
            alt_path_str = " -> ".join(optimal_route["path"])
            action_title = f"Dynamic OSPF Reroute via {alt_path_str}"
            strategy = "DYNAMIC_REROUTE"
            traffic_restored_pct = 100.0
            mttr_minutes = 0.5  # Sub-minute automated OSPF convergence
            priority = "P2-HIGH" if is_wan else "P3-MEDIUM"
            operational_summary = (
                f"Link '{link_id}' connecting {u} and {v} has an active redundant bypass. "
                f"Traffic can be immediately rerouted along the {optimal_route['hop_count']}-hop path: "
                f"[{alt_path_str}] with {optimal_route['bottleneck_bandwidth_mbps']} Mbps bottleneck capacity "
                f"and ~{optimal_route['estimated_latency_ms']}ms estimated latency."
            )
        else:
            alt_path_str = "None (Isolated Segment)"
            action_title = f"Emergency Physical Dispatch: Replace Link {link_id}"
            strategy = "MANUAL_DISPATCH"
            traffic_restored_pct = 0.0
            mttr_minutes = 45.0  # Physical replacement / patch panel required
            priority = "P1-CRITICAL"
            operational_summary = (
                f"CRITICAL WARNING: Link '{link_id}' is a topological bridge with NO redundant path. "
                f"Failure will partition endpoint {v} from the enterprise backbone. "
                f"Immediate field technician dispatch required to inspect cable, SFP transceiver, or switch port."
            )

        ios_commands = self._generate_link_ios_commands(
            link_id=link_id,
            source=u,
            target=v,
            alternate_path=optimal_route["path"] if optimal_route else None,
        )

        playbook_steps = [
            f"Step 1 [Pre-Emptive Drain]: Escalate OSPF metric on {u} and {v} to shed transit traffic.",
            f"Step 2 [Isolation]: Administratively shut down {link_id} to avoid BGP/OSPF route flapping.",
            f"Step 3 [Path Validation]: Verify dynamic routing convergence onto {alt_path_str}.",
            f"Step 4 [Diagnostic]: Initiate hardware and interface loopback diagnostics on {link_id}.",
            f"Step 5 [Post-Recovery]: Re-enable interface and restore default OSPF costs after 5-minute soak test.",
        ]

        return {
            "target_type": "LINK",
            "target_id": link_id,
            "endpoints": [u, v],
            "priority": priority,
            "recovery_strategy": strategy,
            "action_title": action_title,
            "traffic_restored_pct": traffic_restored_pct,
            "mttr_estimated_minutes": mttr_minutes,
            "mttr_reduction_vs_manual_pct": 98.9 if has_alt else 0.0,
            "optimal_alternate_path": optimal_route,
            "candidate_paths_count": len(alt_paths),
            "operational_summary": operational_summary,
            "playbook_steps": playbook_steps,
            "cisco_ios_commands": ios_commands,
        }

    def recommend_device_recovery(
        self,
        device_id: str,
        prediction_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Prescribe a complete recovery and disaster mitigation plan for a failing device.

        Args:
            device_id: The device identifier (e.g. 'HQ-R1').
            prediction_result: Optional prediction dictionary from FailurePredictor.

        Returns:
            Structured recovery plan dictionary.
        """
        sim_res = simulate_device_failure(self.graph, failed_device_id=device_id)
        dev_info = sim_res["device_info"]
        dev_type = dev_info.get("device_type", "Unknown")
        role = dev_info.get("role", "Unknown")
        branch = dev_info.get("branch", "Unknown")

        is_partitioned = sim_res["is_partitioned"]
        post_components = sim_res["post_failure_components_count"]
        severed = sim_res["severed_links"]
        isolated = sim_res["isolated_devices"]

        # Formulate disaster recovery strategy
        if dev_type == "Router":
            priority = "P1-CRITICAL"
            strategy = "GATEWAY_FAILOVER_AND_RING_DEFLECTION"
            mttr_minutes = 2.0
            summary = (
                f"Core/Branch Gateway '{device_id}' failure severs {len(severed)} links and splits the enterprise "
                f"into {post_components} disjoint partitions, isolating devices: {', '.join(isolated) if isolated else 'None'}. "
                f"Mitigation requires diverting inter-branch traffic through adjacent branch cross-tie routers."
            )
        elif dev_type == "Switch":
            priority = "P1-CRITICAL"
            strategy = "DISTRIBUTION_SWITCH_REDUNDANCY"
            mttr_minutes = 15.0
            summary = (
                f"Distribution Switch '{device_id}' in {branch} collapsed. All {len(isolated)} downstream branch hosts "
                f"are isolated. Recommend failover to redundant access switch stack."
            )
        elif dev_type == "Server":
            priority = "P2-HIGH"
            strategy = "SERVICE_FAILOVER_TO_SECONDARY"
            mttr_minutes = 1.0
            summary = (
                f"Application/DNS Server '{device_id}' failure detected. Redirecting corporate DNS/DHCP requests "
                f"to secondary host HQ-SRV2."
            )
        else:
            priority = "P3-MEDIUM"
            strategy = "WORKSTATION_REBOOT_OR_REPLACE"
            mttr_minutes = 30.0
            summary = f"End-user PC '{device_id}' in {branch} offline. No core services impacted."

        ios_commands = self._generate_device_ios_commands(
            device_id=device_id,
            device_type=dev_type,
            severed_links=severed,
        )

        playbook_steps = [
            f"Step 1 [Containment]: Sever stale OSPF adjacencies on {len(severed)} neighboring devices.",
            f"Step 2 [Reroute]: Divert traffic via surviving branch cross-ties (BR1-BR2, BR2-BR3, BR3-BR4).",
            f"Step 3 [Service Migration]: Point DNS/DHCP helper-addresses to surviving HQ servers.",
            f"Step 4 [Device Recovery]: Trigger remote power-cycle (PoE / PDU) or dispatch field replacement.",
            f"Step 5 [Verification]: Validate that all 5 branches regain end-to-end routing convergence.",
        ]

        return {
            "target_type": "DEVICE",
            "target_id": device_id,
            "device_type": dev_type,
            "branch": branch,
            "role": role,
            "priority": priority,
            "recovery_strategy": strategy,
            "is_partitioned": is_partitioned,
            "severed_links_count": len(severed),
            "isolated_devices_count": len(isolated),
            "isolated_devices": isolated,
            "mttr_estimated_minutes": mttr_minutes,
            "operational_summary": summary,
            "playbook_steps": playbook_steps,
            "cisco_ios_commands": ios_commands,
        }
