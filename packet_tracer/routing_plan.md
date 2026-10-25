# Enterprise OSPFv2 Routing Plan

**Project:** AI-Driven Network Digital Twin for Failure Prediction and Recovery  
**Topology:** Five-Branch Organization Network (HQ + North, South, East, West Branches)  
**Routing Protocol:** Open Shortest Path First (OSPFv2)  
**Process ID:** `1`  
**Area:** `0.0.0.0` (Area 0 - Backbone)

---

## 1. Architectural Principles

1. **Link-State Protocol (OSPFv2):** Fast convergence, absence of routing loops, and dynamic metric recalculation based on link cost (\(\text{Cost} = \frac{\text{Reference Bandwidth}}{\text{Interface Bandwidth}}\)).
2. **Backbone Area 0:** All five routers reside in Area 0 to eliminate inter-area summary overhead while maintaining deterministic shortest path tree calculations across the enterprise.
3. **Passive Interfaces:** All LAN subinterfaces facing access switches (`Gig0/0.*`) are declared passive (`passive-interface Gig0/0.x`) to prevent unnecessary Hello packets from flooding user subnets and to block unauthorized routing adjacencies.
4. **Deterministic Router IDs:** Static 32-bit loopback/router-ids ensure stable neighbor relationships and prevent election flapping.

---

## 2. Router ID and Network Advertisement Matrix

### A. Router `HQ-R1`
- **Router ID:** `1.1.1.1`
- **OSPF Process:** `router ospf 1`
- **Advertised Networks:**
  - `10.10.10.0 0.0.0.255 area 0` (VLAN 10 - IT Admin)
  - `10.10.20.0 0.0.0.255 area 0` (VLAN 20 - Corporate)
  - `10.10.30.0 0.0.0.255 area 0` (VLAN 30 - Data Center)
  - `172.16.1.0 0.0.0.3 area 0` (WAN to BR1)
  - `172.16.2.0 0.0.0.3 area 0` (WAN to BR2)
  - `172.16.3.0 0.0.0.3 area 0` (WAN to BR3)
  - `172.16.4.0 0.0.0.3 area 0` (WAN to BR4)
- **Passive Interfaces:** `Gig0/0.10`, `Gig0/0.20`, `Gig0/0.30`

### B. Router `BR1-R1`
- **Router ID:** `2.2.2.2`
- **OSPF Process:** `router ospf 1`
- **Advertised Networks:**
  - `10.20.10.0 0.0.0.255 area 0` (VLAN 110 - Office)
  - `10.20.20.0 0.0.0.255 area 0` (VLAN 120 - Guest/IoT)
  - `172.16.1.0 0.0.0.3 area 0` (WAN to HQ)
  - `172.16.12.0 0.0.0.3 area 0` (Redundant WAN to BR2)
- **Passive Interfaces:** `Gig0/0.110`, `Gig0/0.120`

### C. Router `BR2-R1`
- **Router ID:** `3.3.3.3`
- **OSPF Process:** `router ospf 1`
- **Advertised Networks:**
  - `10.30.10.0 0.0.0.255 area 0` (VLAN 210 - Engineering)
  - `10.30.20.0 0.0.0.255 area 0` (VLAN 220 - Lab)
  - `172.16.2.0 0.0.0.3 area 0` (WAN to HQ)
  - `172.16.12.0 0.0.0.3 area 0` (Redundant WAN to BR1)
  - `172.16.23.0 0.0.0.3 area 0` (Redundant WAN to BR3)
- **Passive Interfaces:** `Gig0/0.210`, `Gig0/0.220`

### D. Router `BR3-R1`
- **Router ID:** `4.4.4.4`
- **OSPF Process:** `router ospf 1`
- **Advertised Networks:**
  - `10.40.10.0 0.0.0.255 area 0` (VLAN 310 - Sales)
  - `10.40.20.0 0.0.0.255 area 0` (VLAN 320 - Marketing)
  - `172.16.3.0 0.0.0.3 area 0` (WAN to HQ)
  - `172.16.23.0 0.0.0.3 area 0` (Redundant WAN to BR2)
  - `172.16.34.0 0.0.0.3 area 0` (Redundant WAN to BR4)
- **Passive Interfaces:** `Gig0/0.310`, `Gig0/0.320`

### E. Router `BR4-R1`
- **Router ID:** `5.5.5.5`
- **OSPF Process:** `router ospf 1`
- **Advertised Networks:**
  - `10.50.10.0 0.0.0.255 area 0` (VLAN 410 - Logistics)
  - `10.50.20.0 0.0.0.255 area 0` (VLAN 420 - Support)
  - `172.16.4.0 0.0.0.3 area 0` (WAN to HQ)
  - `172.16.34.0 0.0.0.3 area 0` (Redundant WAN to BR3)
- **Passive Interfaces:** `Gig0/0.410`, `Gig0/0.420`

---

## 3. Dynamic Failover Behavior

The OSPF Shortest Path First (Dijkstra) algorithm automatically calculates backup routes when primary links fail:

1. **Baseline Path (`BR1-PC1` to `HQ-SRV1`):**
   - Path: `BR1-PC1` -> `BR1-SW1` -> `BR1-R1` -> `HQ-R1` -> `HQ-SW1` -> `HQ-SRV1`
   - OSPF Cost: Low (Gigabit WAN link `172.16.1.0/30`, cost = 1).
2. **Primary Link Failure (`WAN-HQ-BR1` Cut):**
   - Dead timer detects loss of Hello packets or link-down event.
   - OSPF floods Link State Updates (LSU) to all neighbors.
   - New shortest path calculated: `BR1-R1` -> `BR2-R1` -> `HQ-R1`.
   - Convergence time in Packet Tracer: ~5 to 10 seconds.
3. **Serial Link Failure (`WAN-HQ-BR4` Cut):**
   - When the serial link from HQ to BR4 drops, traffic to Branch 4 dynamically traverses `HQ-R1` -> `BR3-R1` -> `BR4-R1`.

---

## 4. Cisco IOS OSPF Verification Commands

To verify routing convergence on any router:
```ios
show ip ospf neighbor
show ip route ospf
show ip ospf interface brief
show ip protocols
```
Expected output on `HQ-R1`:
- 4 neighbors in `FULL/ -` state (`2.2.2.2`, `3.3.3.3`, `4.4.4.4`, `5.5.5.5`).
- Routing table containing routes for `10.20.0.0/16`, `10.30.0.0/16`, `10.40.0.0/16`, and `10.50.0.0/16` marked with code `O`.
