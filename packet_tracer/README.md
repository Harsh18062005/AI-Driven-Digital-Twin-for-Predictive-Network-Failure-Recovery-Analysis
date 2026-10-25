# Enterprise Five-Branch Network (Packet Tracer Module)

**Project:** AI-Driven Network Digital Twin for Failure Prediction and Recovery  
**Target Environment:** Cisco Packet Tracer 9.0.0  
**Authors:** Networking Team Member  

---

## 1. Network Purpose and Architecture

This module designs and documents an enterprise network architecture spanning five locations:
- **Headquarters (HQ):** Central management, executive operations, and primary data center hosting DNS, DHCP, and Web/App services.
- **Branch 1 (North Branch):** Regional operations and field terminal subnet.
- **Branch 2 (South Branch):** Engineering software and hardware R&D laboratories.
- **Branch 3 (East Branch):** Commercial enterprise sales and marketing teams.
- **Branch 4 (West Branch):** Warehouse logistics, supply chain distribution, and customer support.

### WAN Topology & High Availability
To support the project's **Digital Twin Failure Simulator and Recovery Comparison**, the WAN employs a **partial mesh topology**:
- **Primary Hub-to-Spoke links:** Connect `HQ-R1` directly to each branch router (`BR1-R1`, `BR2-R1`, `BR3-R1`, `BR4-R1`).
- **Redundant Inter-Branch links:**
  - `BR1-R1` <--> `BR2-R1` (`172.16.12.0/30`)
  - `BR3-R1` <--> `BR4-R1` (`172.16.34.0/30`)
  - `BR2-R1` <--> `BR3-R1` (`172.16.23.0/30`)
This ring structure ensures that if any primary hub-and-spoke link is severed, OSPFv2 automatically re-converges traffic through neighboring branches rather than leaving the branch permanently disconnected.

---

## 2. Inventory Files Reference

All structured network tables are maintained in this directory:
- [device_inventory.csv](device_inventory.csv) — Hostnames, device models, branch roles, and management IPs.
- [ip_addressing.csv](ip_addressing.csv) — Interface-level IP assignments, subnet masks, and CIDR blocks.
- [vlan_plan.csv](vlan_plan.csv) — VLAN IDs, subnet definitions, default gateways, and DHCP pools.
- [link_inventory.csv](link_inventory.csv) — All 24 physical and logical connections (trunks, access, and WAN).
- [routing_plan.md](routing_plan.md) — OSPF process configuration, Router-IDs, passive interfaces, and metric costs.
- [validation_results.md](validation_results.md) — Comprehensive verification tests and expected outputs.

---

## 3. Step-by-Step Packet Tracer Construction Guide

Follow these steps to assemble and save the actual `.pkt` file in Cisco Packet Tracer:

### Step 1: Place Network Devices
1. Launch **Cisco Packet Tracer 9.0.0** (located at `C:\Program Files\Cisco Packet Tracer 9.0.0\bin\PacketTracer.exe`).
2. Add **5 Routers** using the **Cisco 2911** model:
   - Rename them: `HQ-R1`, `BR1-R1`, `BR2-R1`, `BR3-R1`, `BR4-R1`.
3. Add **HWIC-2T Serial Cards**:
   - For `HQ-R1`, `BR2-R1`, `BR3-R1`, and `BR4-R1`:
     - Click the router -> Physical Tab.
     - Power off the router switch (green power toggle).
     - Drag the **HWIC-2T** module from the left list into slot **EHWIC 1** (upper right slot).
     - For `HQ-R1`, drag a second **HWIC-2T** into slot **EHWIC 2** if needed, or use slot 1 (`Serial0/1/0` and `Serial0/1/1`).
     - Power on the router switch.
4. Add **5 Switches** using the **Cisco Catalyst 2960-24TT** model:
   - Rename them: `HQ-SW1`, `BR1-SW1`, `BR2-SW1`, `BR3-SW1`, `BR4-SW1`.
5. Add **2 Servers** (Generic `Server-PT`):
   - `HQ-SRV1` (DNS/DHCP)
   - `HQ-SRV2` (App Server)
6. Add **10 PCs** (Generic `PC-PT`):
   - HQ: `HQ-PC1`, `HQ-PC2`
   - BR1: `BR1-PC1`, `BR1-PC2`
   - BR2: `BR2-PC1`, `BR2-PC2`
   - BR3: `BR3-PC1`, `BR3-PC2`
   - BR4: `BR4-PC1`, `BR4-PC2`

---

### Step 2: Cable Connections
Using standard cables in Packet Tracer:
- **Router to Switch:** Copper Straight-Through cable from Router `Gig0/0` to Switch `Gig0/1`.
- **Switch to End Devices:** Copper Straight-Through cables:
  - `HQ-SW1`: `Fa0/1` -> `HQ-PC1`, `Fa0/2` -> `HQ-PC2`, `Fa0/3` -> `HQ-SRV1`, `Fa0/4` -> `HQ-SRV2`.
  - `BR1-SW1`: `Fa0/1` -> `BR1-PC1`, `Fa0/2` -> `BR1-PC2`.
  - `BR2-SW1`: `Fa0/1` -> `BR2-PC1`, `Fa0/2` -> `BR2-PC2`.
  - `BR3-SW1`: `Fa0/1` -> `BR3-PC1`, `Fa0/2` -> `BR3-PC2`.
  - `BR4-SW1`: `Fa0/1` -> `BR4-PC1`, `Fa0/2` -> `BR4-PC2`.
- **Ethernet WAN Links (Copper Cross-Over or Auto-MDIX):**
  - `HQ-R1:Gig0/1` <--> `BR1-R1:Gig0/1`
  - `HQ-R1:Gig0/2` <--> `BR2-R1:Gig0/1`
  - `BR1-R1:Gig0/2` <--> `BR2-R1:Gig0/2`
  - `BR3-R1:Gig0/1` <--> `BR4-R1:Gig0/1`
- **Serial WAN Links (Serial DCE Cable):**
  - `HQ-R1:Serial0/1/0` (DCE) <--> `BR3-R1:Serial0/1/0`
  - `HQ-R1:Serial0/1/1` (DCE) <--> `BR4-R1:Serial0/1/0`
  - `BR2-R1:Serial0/1/0` (DCE) <--> `BR3-R1:Serial0/1/1`

---

### Step 3: Copy-Paste Cisco IOS Configurations

Open the **CLI tab** for each device and paste the corresponding script block:

#### Router: `HQ-R1`
```ios
enable
configure terminal
hostname HQ-R1
no ip domain-lookup

! Inter-VLAN Routing Subinterfaces
interface GigabitEthernet0/0
 no shutdown
!
interface GigabitEthernet0/0.10
 encapsulation dot1Q 10
 ip address 10.10.10.1 255.255.255.0
 description HQ Management Gateway
!
interface GigabitEthernet0/0.20
 encapsulation dot1Q 20
 ip address 10.10.20.1 255.255.255.0
 description HQ Corporate Gateway
!
interface GigabitEthernet0/0.30
 encapsulation dot1Q 30
 ip address 10.10.30.1 255.255.255.0
 description HQ DataCenter Gateway
!
! WAN Interfaces
interface GigabitEthernet0/1
 ip address 172.16.1.1 255.255.255.252
 description WAN to BR1
 no shutdown
!
interface GigabitEthernet0/2
 ip address 172.16.2.1 255.255.255.252
 description WAN to BR2
 no shutdown
!
interface Serial0/1/0
 ip address 172.16.3.1 255.255.255.252
 clock rate 64000
 description WAN to BR3
 no shutdown
!
interface Serial0/1/1
 ip address 172.16.4.1 255.255.255.252
 clock rate 64000
 description WAN to BR4
 no shutdown
!
! OSPF Dynamic Routing
router ospf 1
 router-id 1.1.1.1
 network 10.10.10.0 0.0.0.255 area 0
 network 10.10.20.0 0.0.0.255 area 0
 network 10.10.30.0 0.0.0.255 area 0
 network 172.16.1.0 0.0.0.3 area 0
 network 172.16.2.0 0.0.0.3 area 0
 network 172.16.3.0 0.0.0.3 area 0
 network 172.16.4.0 0.0.0.3 area 0
 passive-interface GigabitEthernet0/0.10
 passive-interface GigabitEthernet0/0.20
 passive-interface GigabitEthernet0/0.30
!
end
write memory
```

#### Switch: `HQ-SW1`
```ios
enable
configure terminal
hostname HQ-SW1

vlan 10
 name HQ-Management
vlan 20
 name HQ-Corporate
vlan 30
 name HQ-DataCenter
exit

! Trunk uplink to Router
interface GigabitEthernet0/1
 switchport mode trunk
 switchport trunk allowed vlan 10,20,30
 no shutdown

! Access Ports
interface FastEthernet0/1
 switchport mode access
 switchport access vlan 10
 spanning-tree portfast
 no shutdown

interface FastEthernet0/2
 switchport mode access
 switchport access vlan 20
 spanning-tree portfast
 no shutdown

interface range FastEthernet0/3 - 4
 switchport mode access
 switchport access vlan 30
 spanning-tree portfast
 no shutdown

! Management SVI
interface vlan 10
 ip address 10.10.10.2 255.255.255.0
 no shutdown
ip default-gateway 10.10.10.1

end
write memory
```

#### Router: `BR1-R1`
```ios
enable
configure terminal
hostname BR1-R1
no ip domain-lookup

interface GigabitEthernet0/0
 no shutdown
!
interface GigabitEthernet0/0.110
 encapsulation dot1Q 110
 ip address 10.20.10.1 255.255.255.0
 description BR1 Office Gateway
!
interface GigabitEthernet0/0.120
 encapsulation dot1Q 120
 ip address 10.20.20.1 255.255.255.0
 description BR1 Guest-IoT Gateway
!
interface GigabitEthernet0/1
 ip address 172.16.1.2 255.255.255.252
 description WAN to HQ
 no shutdown
!
interface GigabitEthernet0/2
 ip address 172.16.12.1 255.255.255.252
 description Backup WAN to BR2
 no shutdown
!
router ospf 1
 router-id 2.2.2.2
 network 10.20.10.0 0.0.0.255 area 0
 network 10.20.20.0 0.0.0.255 area 0
 network 172.16.1.0 0.0.0.3 area 0
 network 172.16.12.0 0.0.0.3 area 0
 passive-interface GigabitEthernet0/0.110
 passive-interface GigabitEthernet0/0.120
!
end
write memory
```

#### Switch: `BR1-SW1`
```ios
enable
configure terminal
hostname BR1-SW1

vlan 110
 name BR1-Office
vlan 120
 name BR1-Guest-IoT
exit

interface GigabitEthernet0/1
 switchport mode trunk
 switchport trunk allowed vlan 110,120
 no shutdown

interface FastEthernet0/1
 switchport mode access
 switchport access vlan 110
 spanning-tree portfast
 no shutdown

interface FastEthernet0/2
 switchport mode access
 switchport access vlan 120
 spanning-tree portfast
 no shutdown

interface vlan 110
 ip address 10.20.10.2 255.255.255.0
 no shutdown
ip default-gateway 10.20.10.1

end
write memory
```

#### Router: `BR2-R1`
```ios
enable
configure terminal
hostname BR2-R1
no ip domain-lookup

interface GigabitEthernet0/0
 no shutdown
!
interface GigabitEthernet0/0.210
 encapsulation dot1Q 210
 ip address 10.30.10.1 255.255.255.0
 description BR2 Eng Gateway
!
interface GigabitEthernet0/0.220
 encapsulation dot1Q 220
 ip address 10.30.20.1 255.255.255.0
 description BR2 Lab Gateway
!
interface GigabitEthernet0/1
 ip address 172.16.2.2 255.255.255.252
 description WAN to HQ
 no shutdown
!
interface GigabitEthernet0/2
 ip address 172.16.12.2 255.255.255.252
 description Backup WAN to BR1
 no shutdown
!
interface Serial0/1/0
 ip address 172.16.23.1 255.255.255.252
 clock rate 64000
 description Backup WAN to BR3
 no shutdown
!
router ospf 1
 router-id 3.3.3.3
 network 10.30.10.0 0.0.0.255 area 0
 network 10.30.20.0 0.0.0.255 area 0
 network 172.16.2.0 0.0.0.3 area 0
 network 172.16.12.0 0.0.0.3 area 0
 network 172.16.23.0 0.0.0.3 area 0
 passive-interface GigabitEthernet0/0.210
 passive-interface GigabitEthernet0/0.220
!
end
write memory
```

#### Switch: `BR2-SW1`
```ios
enable
configure terminal
hostname BR2-SW1

vlan 210
 name BR2-Engineering
vlan 220
 name BR2-Lab
exit

interface GigabitEthernet0/1
 switchport mode trunk
 switchport trunk allowed vlan 210,220
 no shutdown

interface FastEthernet0/1
 switchport mode access
 switchport access vlan 210
 spanning-tree portfast
 no shutdown

interface FastEthernet0/2
 switchport mode access
 switchport access vlan 220
 spanning-tree portfast
 no shutdown

interface vlan 210
 ip address 10.30.10.2 255.255.255.0
 no shutdown
ip default-gateway 10.30.10.1

end
write memory
```

#### Router: `BR3-R1`
```ios
enable
configure terminal
hostname BR3-R1
no ip domain-lookup

interface GigabitEthernet0/0
 no shutdown
!
interface GigabitEthernet0/0.310
 encapsulation dot1Q 310
 ip address 10.40.10.1 255.255.255.0
 description BR3 Sales Gateway
!
interface GigabitEthernet0/0.320
 encapsulation dot1Q 320
 ip address 10.40.20.1 255.255.255.0
 description BR3 Marketing Gateway
!
interface Serial0/1/0
 ip address 172.16.3.2 255.255.255.252
 description WAN to HQ
 no shutdown
!
interface Serial0/1/1
 ip address 172.16.23.2 255.255.255.252
 description Backup WAN to BR2
 no shutdown
!
interface GigabitEthernet0/1
 ip address 172.16.34.1 255.255.255.252
 description Backup WAN to BR4
 no shutdown
!
router ospf 1
 router-id 4.4.4.4
 network 10.40.10.0 0.0.0.255 area 0
 network 10.40.20.0 0.0.0.255 area 0
 network 172.16.3.0 0.0.0.3 area 0
 network 172.16.23.0 0.0.0.3 area 0
 network 172.16.34.0 0.0.0.3 area 0
 passive-interface GigabitEthernet0/0.310
 passive-interface GigabitEthernet0/0.320
!
end
write memory
```

#### Switch: `BR3-SW1`
```ios
enable
configure terminal
hostname BR3-SW1

vlan 310
 name BR3-Sales
vlan 320
 name BR3-Marketing
exit

interface GigabitEthernet0/1
 switchport mode trunk
 switchport trunk allowed vlan 310,320
 no shutdown

interface FastEthernet0/1
 switchport mode access
 switchport access vlan 310
 spanning-tree portfast
 no shutdown

interface FastEthernet0/2
 switchport mode access
 switchport access vlan 320
 spanning-tree portfast
 no shutdown

interface vlan 310
 ip address 10.40.10.2 255.255.255.0
 no shutdown
ip default-gateway 10.40.10.1

end
write memory
```

#### Router: `BR4-R1`
```ios
enable
configure terminal
hostname BR4-R1
no ip domain-lookup

interface GigabitEthernet0/0
 no shutdown
!
interface GigabitEthernet0/0.410
 encapsulation dot1Q 410
 ip address 10.50.10.1 255.255.255.0
 description BR4 Logistics Gateway
!
interface GigabitEthernet0/0.420
 encapsulation dot1Q 420
 ip address 10.50.20.1 255.255.255.0
 description BR4 Support Gateway
!
interface Serial0/1/0
 ip address 172.16.4.2 255.255.255.252
 description WAN to HQ
 no shutdown
!
interface GigabitEthernet0/1
 ip address 172.16.34.2 255.255.255.252
 description Backup WAN to BR3
 no shutdown
!
router ospf 1
 router-id 5.5.5.5
 network 10.50.10.0 0.0.0.255 area 0
 network 10.50.20.0 0.0.0.255 area 0
 network 172.16.4.0 0.0.0.3 area 0
 network 172.16.34.0 0.0.0.3 area 0
 passive-interface GigabitEthernet0/0.410
 passive-interface GigabitEthernet0/0.420
!
end
write memory
```

#### Switch: `BR4-SW1`
```ios
enable
configure terminal
hostname BR4-SW1

vlan 410
 name BR4-Logistics
vlan 420
 name BR4-Support
exit

interface GigabitEthernet0/1
 switchport mode trunk
 switchport trunk allowed vlan 410,420
 no shutdown

interface FastEthernet0/1
 switchport mode access
 switchport access vlan 410
 spanning-tree portfast
 no shutdown

interface FastEthernet0/2
 switchport mode access
 switchport access vlan 420
 spanning-tree portfast
 no shutdown

interface vlan 410
 ip address 10.50.10.2 255.255.255.0
 no shutdown
ip default-gateway 10.50.10.1

end
write memory
```

---

### Step 4: Configure End Hosts & Servers

In Packet Tracer, click each host -> **Desktop Tab** -> **IP Configuration**:

| Device | IPv4 Address | Subnet Mask | Default Gateway | DNS Server |
| :--- | :--- | :--- | :--- | :--- |
| `HQ-SRV1` | `10.10.30.10` | `255.255.255.0` | `10.10.30.1` | `127.0.0.1` |
| `HQ-SRV2` | `10.10.30.20` | `255.255.255.0` | `10.10.30.1` | `10.10.30.10` |
| `HQ-PC1` | `10.10.10.50` | `255.255.255.0` | `10.10.10.1` | `10.10.30.10` |
| `HQ-PC2` | `10.10.20.50` | `255.255.255.0` | `10.10.20.1` | `10.10.30.10` |
| `BR1-PC1` | `10.20.10.50` | `255.255.255.0` | `10.20.10.1` | `10.10.30.10` |
| `BR1-PC2` | `10.20.20.50` | `255.255.255.0` | `10.20.20.1` | `10.10.30.10` |
| `BR2-PC1` | `10.30.10.50` | `255.255.255.0` | `10.30.10.1` | `10.10.30.10` |
| `BR2-PC2` | `10.30.20.50` | `255.255.255.0` | `10.30.20.1` | `10.10.30.10` |
| `BR3-PC1` | `10.40.10.50` | `255.255.255.0` | `10.40.10.1` | `10.10.30.10` |
| `BR3-PC2` | `10.40.20.50` | `255.255.255.0` | `10.40.20.1` | `10.10.30.10` |
| `BR4-PC1` | `10.50.10.50` | `255.255.255.0` | `10.50.10.1` | `10.10.30.10` |
| `BR4-PC2` | `10.50.20.50` | `255.255.255.0` | `10.50.20.1` | `10.10.30.10` |

---

### Step 5: Save Project and Screenshot
1. Click **File -> Save As...** in Packet Tracer.
2. Save the project to:
   `d:\3yproject\mini project\AI-Driven-Digital-Twin-for-Predictive-Network-Failure-Recovery-Analysis\packet_tracer\organisation_network.pkt`
3. Take a clean screenshot of the Packet Tracer workspace and save it as:
   `packet_tracer/topology_screenshot.png`

---

## 4. Known Limitations
- Graph models in `python/` represent topological reachability and path availability. They do not simulate Layer 4 TCP handshakes, QoS queuing delays, or dynamic ACL packet inspection.
- The `.pkt` file format is Cisco proprietary and can only be opened and simulated inside Cisco Packet Tracer.
