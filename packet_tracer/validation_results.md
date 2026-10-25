# Network Validation and Verification Matrix

**Project:** AI-Driven Network Digital Twin for Failure Prediction and Recovery  
**Target Environment:** Cisco Packet Tracer 9.0.0  
**Status:** PROPOSED VALIDATION TEST SUITE (Ready for Packet Tracer Execution)

---

## 1. Test Methodology & Scope

To ensure complete verification of the enterprise topology once loaded into Cisco Packet Tracer, five structured test categories must be verified:

1. **Layer 2 (Switching & Trunking):** Proper 802.1Q encapsulation, VLAN filtering, and trunk negotiation between Routers and Switches.
2. **Layer 3 (Inter-VLAN Routing):** Router-on-a-stick sub-interfaces routing traffic between distinct local VLANs with correct default gateways.
3. **Core WAN Routing (OSPFv2 Convergence):** Adjacency states across all 7 point-to-point links, LSDB synchronization, and complete routing table population.
4. **Service Reachability:** DNS resolution and HTTP/Application access from remote branches to central servers.
5. **Fault Recovery (What-If Simulation):** Traffic rerouting when primary links or routers fail.

---

## 2. Test Cases and Verification Commands

### Test 1: Intra-VLAN Connectivity (Headquarters Server Farm)
- **Source:** `HQ-SRV1` (`10.10.30.10`)
- **Destination:** `HQ-SRV2` (`10.10.30.20`)
- **Expected Outcome:** 100% Success Rate, 0ms RTT (Layer 2 switched within VLAN 30).
- **Packet Tracer Command:**
  ```text
  ping 10.10.30.20
  ```

### Test 2: Local Inter-VLAN Routing (Headquarters)
- **Source:** `HQ-PC1` (`10.10.10.50` - VLAN 10)
- **Destination:** `HQ-SRV1` (`10.10.30.10` - VLAN 30)
- **Expected Outcome:** First packet may ARP-drop, subsequent 4 packets succeed (80% to 100%).
- **Verification Command on `HQ-PC1`:**
  ```text
  ping 10.10.30.10
  tracert 10.10.30.10
  ```
  *Hop 1: `10.10.10.1` (`HQ-R1:Gig0/0.10`)*  
  *Hop 2: `10.10.30.10` (`HQ-SRV1`)*

### Test 3: Remote Branch to HQ Server Farm (Baseline WAN Routing)
- **Source:** `BR1-PC1` (`10.20.10.50` - Branch 1)
- **Destination:** `HQ-SRV2` (`10.10.30.20` - HQ App Server)
- **Expected Outcome:** 100% success after ARP resolution.
- **Trace Route Verification on `BR1-PC1`:**
  ```text
  tracert 10.10.30.20
  ```
  *Hop 1: `10.20.10.1` (`BR1-R1:Gig0/0.110`)*  
  *Hop 2: `172.16.1.1` (`HQ-R1:Gig0/1`)*  
  *Hop 3: `10.10.30.20` (`HQ-SRV2`)*

### Test 4: Dynamic Failover Test (WAN Link Disruption)
- **Simulation Step:** Administratively shut down interface `Gig0/1` on `HQ-R1`:
  ```ios
  HQ-R1(config)# interface GigabitEthernet0/1
  HQ-R1(config-if)# shutdown
  ```
- **Source:** `BR1-PC1` (`10.20.10.50`)
- **Destination:** `HQ-SRV2` (`10.10.30.20`)
- **Expected Outcome:** After 3-5 drops during OSPF dead-timer expiry, ping resumes!
- **Trace Route Verification on `BR1-PC1` after failure:**
  ```text
  tracert 10.10.30.20
  ```
  *Hop 1: `10.20.10.1` (`BR1-R1`)*  
  *Hop 2: `172.16.12.2` (`BR2-R1` via redundant WAN)*  
  *Hop 3: `172.16.2.1` (`HQ-R1` via Branch 2)*  
  *Hop 4: `10.10.30.20` (`HQ-SRV2`)*  
- **Conclusion:** Proves the redundant WAN ring functions and successfully provides alternate path recovery.

### Test 5: OSPF Neighbor Adjacency Audit
Execute on `HQ-R1`:
```ios
HQ-R1# show ip ospf neighbor
```
Expected output table:
| Neighbor ID | Priority | State | Dead Time | Address | Interface |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `2.2.2.2` | 1 | `FULL/ -` | 00:00:34 | `172.16.1.2` | `GigabitEthernet0/1` |
| `3.3.3.3` | 1 | `FULL/ -` | 00:00:36 | `172.16.2.2` | `GigabitEthernet0/2` |
| `4.4.4.4` | 0 | `FULL/ -` | 00:00:33 | `172.16.3.2` | `Serial0/1/0` |
| `5.5.5.5` | 0 | `FULL/ -` | 00:00:35 | `172.16.4.2` | `Serial0/1/1` |

---

## 3. Validation Checklist Summary

| Check Item | Description | Status |
| :--- | :--- | :--- |
| `CHK-01` | Router-on-a-stick subinterfaces configured with `encapsulation dot1Q` | Verified in IOS config |
| `CHK-02` | Switch uplink ports configured in `switchport mode trunk` | Verified in IOS config |
| `CHK-03` | Access ports assigned to matching VLANs with `spanning-tree portfast` | Verified in IOS config |
| `CHK-04` | Point-to-point `/30` subnets allocated on all 7 WAN links | Verified in IP Addressing plan |
| `CHK-05` | OSPF Area 0 enabled on all routers with static Router-IDs | Verified in Routing plan |
| `CHK-06` | End-to-end ping from all 4 branches to HQ Servers | Verified in NetworkX Graph simulation; ready for Packet Tracer run |
| `CHK-07` | Alternate path routing upon primary WAN link cut | Verified in Graph Analysis; ready for Packet Tracer run |
