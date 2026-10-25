"""Command-Line Interface and Interactive Demonstration for ML Digital Twin.

Provides commands to train models, evaluate telemetry, predict failure risks,
simulate what-if failures, and generate Cisco IOS self-healing recovery scripts.
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

import argparse
from typing import Any, Dict

from ml.config import ALL_DEVICE_IDS, ALL_LINK_IDS
from ml.digital_twin import NetworkDigitalTwin
from ml.train import NetworkModelTrainer


def print_banner() -> None:
    """Print ASCII art and module information banner."""
    print("=" * 72)
    print("    AI-DRIVEN NETWORK DIGITAL TWIN: FAILURE PREDICTION & RECOVERY    ")
    print("        Machine Learning Core & Prescriptive Self-Healing Engine     ")
    print("=" * 72)


def handle_train_pipeline() -> None:
    """Run full training pipeline."""
    trainer = NetworkModelTrainer()
    trainer.run_full_pipeline()


def handle_summary(twin: NetworkDigitalTwin) -> None:
    """Display enterprise health summary KPIs."""
    matrix = twin.get_enterprise_health_matrix()
    kpis = matrix["kpis"]
    topo = twin.get_topology_overview()

    print("\n" + "=" * 60)
    print(f" ENTERPRISE DIGITAL TWIN HEALTH DASHBOARD")
    print("=" * 60)
    print(f"Network Name              : {topo['network_name']}")
    print(f"Overall Network Health    : {matrix['overall_health_score']:.1f} / 100")
    print(f"Total Monitored Devices   : {topo['total_nodes']} ({kpis['device_counts']['healthy']} Healthy, {kpis['device_counts']['warning']} Warning, {kpis['device_counts']['critical']} Critical)")
    print(f"Total Monitored Links     : {topo['total_edges']} ({kpis['link_counts']['healthy']} Healthy, {kpis['link_counts']['warning']} Warning, {kpis['link_counts']['critical']} Critical)")
    
    print("\nTop 3 At-Risk Links:")
    for l in kpis["top_vulnerable_links"]:
        print(f"  - {l['link_id']:14s} ({l['link_type']:6s}) | Risk: {l['risk_level']:6s} | P(Fail): {l['failure_probability']:.1%} | Health: {l['health_score']:.1f}")

    print("\nTop 3 At-Risk Devices:")
    for d in kpis["top_vulnerable_devices"]:
        print(f"  - {d['device_id']:10s} ({d['device_type']:7s} in {d['branch']:20s}) | State: {d['health_state']:8s} | Health: {d['health_score']:.1f}")
    print("=" * 60)


def handle_matrix(twin: NetworkDigitalTwin) -> None:
    """Print full tabular status for all 22 devices and 24 links."""
    matrix = twin.get_enterprise_health_matrix()

    print("\n" + "=" * 80)
    print(" ALL 22 NETWORK DEVICES HEALTH MATRIX")
    print("=" * 80)
    print(f"{'Device ID':10s} {'Type':8s} {'Branch':22s} {'State':8s} {'Risk':6s} {'Health':6s} {'Blast Radius'}")
    print("-" * 80)
    for d in matrix["devices"]:
        print(
            f"{d['device_id']:10s} {d['device_type']:8s} {d['branch']:22s} "
            f"{d['health_state']:8s} {d['risk_level']:6s} {d['health_score']:5.1f}  "
            f"{d['predicted_blast_radius']} device(s)"
        )

    print("\n" + "=" * 80)
    print(" ALL 24 NETWORK LINKS HEALTH MATRIX")
    print("=" * 80)
    print(f"{'Link ID':15s} {'Type':8s} {'Endpoints':24s} {'Risk':6s} {'P(Fail)':8s} {'Health':6s} {'Redundancy'}")
    print("-" * 80)
    for l in matrix["links"]:
        endpoints = f"{l['source_device']} <-> {l['target_device']}"
        redundancy = f"Alt: {l['alternate_path_hops']} hops" if l['alternate_path_exists'] else "NO BYPASS (Bridge)"
        print(
            f"{l['link_id']:15s} {l['link_type']:8s} {endpoints:24s} "
            f"{l['risk_level']:6s} {l['failure_probability']:7.1%} {l['health_score']:5.1f}  "
            f"{redundancy}"
        )
    print("=" * 80)


def handle_diagnose(twin: NetworkDigitalTwin, target_id: str) -> None:
    """Run diagnosis and print self-healing recovery prescription."""
    report = twin.predict_and_mitigate(target_id)
    pred = report["prediction"]
    rec = report["recovery_plan"]

    print("\n" + "=" * 70)
    print(f" AI-DRIVEN DIAGNOSIS & RECOVERY PLAN: {target_id}")
    print("=" * 70)
    print(f"Summary           : {report['summary']}")
    print(f"Target Type       : {report['target_type']}")
    print(f"Action Title      : {rec['action_title'] if 'action_title' in rec else rec['recovery_strategy']}")
    print(f"Priority Level    : {rec['priority']}")
    print(f"Restoration Est.  : {rec.get('traffic_restored_pct', 100.0)}% Traffic Recovery")
    print(f"Estimated MTTR    : {rec['mttr_estimated_minutes']} minute(s)")

    if pred.get("risk_factors"):
        print("\nIdentified Risk Factors:")
        for rf in pred["risk_factors"]:
            print(f"  [!] {rf}")

    print("\nOperational Playbook Steps:")
    for step in rec["playbook_steps"]:
        print(f"  {step}")

    print("\nCisco IOS Automated Configuration Snippet:")
    print("-" * 60)
    for line in rec["cisco_ios_commands"]:
        print(f"  {line}")
    print("-" * 60)


def handle_simulate(twin: NetworkDigitalTwin, target_id: str) -> None:
    """Execute what-if failure simulation in digital twin sandbox."""
    sim = twin.simulate_what_if_scenario(target_id)
    print("\n" + "=" * 70)
    print(f" DIGITAL TWIN WHAT-IF SIMULATION: {target_id}")
    print("=" * 70)
    if sim["scenario_type"] == "LINK_FAILURE":
        res = sim["simulation"]
        print(f"Failed Link       : {res['failed_link_id']}")
        print(f"Severed Endpoints : {res['endpoints'][0]} <--> {res['endpoints'][1]}")
        print(f"Alternate Path    : {' -> '.join(res['alternate_path']) if res['alternate_path'] else 'None'}")
        print(f"Network Partition : {'YES (Bridge broken)' if res['is_bridge'] else 'NO (Redundant route active)'}")
    else:
        res = sim["simulation"]
        print(f"Failed Device     : {res['failed_device_id']} ({res['device_info']['device_type']})")
        print(f"Severed Links     : {res['severed_links_count']}")
        print(f"Isolated Devices  : {', '.join(res['isolated_devices']) if res['isolated_devices'] else 'None'}")
        print(f"Network Partition : {'YES (Disjoint islands)' if res['is_partitioned'] else 'NO'}")

    rec = sim["recovery_prescription"]
    print(f"\nPrescribed Action : {rec.get('action_title', rec.get('recovery_strategy'))}")
    print(f"Estimated MTTR    : {rec['mttr_estimated_minutes']} mins")
    print("=" * 70)


def interactive_menu(twin: NetworkDigitalTwin) -> None:
    """Present interactive console menu."""
    while True:
        print_banner()
        print(" 1. View Enterprise Health Dashboard Summary")
        print(" 2. View Complete 22-Device and 24-Link Health Matrix")
        print(" 3. Predict & Prescribe Recovery for Link (e.g. WAN-HQ-BR1)")
        print(" 4. Predict & Prescribe Recovery for Device (e.g. HQ-R1)")
        print(" 5. Simulate What-If Failure Scenario")
        print(" 6. Re-Train All Machine Learning Models")
        print(" 0. Exit")
        print("-" * 72)
        choice = input("Select an option [0-6]: ").strip()

        if choice == "0":
            print("Exiting Digital Twin ML Console.")
            break
        elif choice == "1":
            handle_summary(twin)
        elif choice == "2":
            handle_matrix(twin)
        elif choice == "3":
            lid = input("Enter Link ID (e.g. WAN-HQ-BR1): ").strip()
            if lid:
                handle_diagnose(twin, lid)
        elif choice == "4":
            did = input("Enter Device ID (e.g. HQ-R1): ").strip()
            if did:
                handle_diagnose(twin, did)
        elif choice == "5":
            tid = input("Enter Link or Device ID to fail: ").strip()
            if tid:
                handle_simulate(twin, tid)
        elif choice == "6":
            handle_train_pipeline()
        else:
            print("[!] Invalid option. Please enter 0 through 6.")

        input("\nPress Enter to return to main menu...")


def main() -> None:
    """Main CLI entrypoint parsing flags or initiating interactive mode."""
    parser = argparse.ArgumentParser(
        description="AI-Driven Network Digital Twin - ML Core and Recovery Engine"
    )
    parser.add_argument("--train", action="store_true", help="Run model training pipeline")
    parser.add_argument("--summary", action="store_true", help="Display health KPI summary")
    parser.add_argument("--matrix", action="store_true", help="Display full device & link matrix")
    parser.add_argument("--diagnose", type=str, metavar="TARGET_ID", help="Predict and prescribe recovery for link/device")
    parser.add_argument("--simulate", type=str, metavar="TARGET_ID", help="Simulate what-if failure for link/device")

    args = parser.parse_args()

    if args.train:
        handle_train_pipeline()
        return

    # Initialize twin facade
    twin = NetworkDigitalTwin()

    if args.summary:
        handle_summary(twin)
    elif args.matrix:
        handle_matrix(twin)
    elif args.diagnose:
        handle_diagnose(twin, args.diagnose)
    elif args.simulate:
        handle_simulate(twin, args.simulate)
    else:
        interactive_menu(twin)


if __name__ == "__main__":
    main()
