# MITM Attack on IEC 61850 GOOSE – False Command Injection Case Study

## Key Concepts

### Intelligent Electronic Device (IED)
An **IED** is a microprocessor-based controller used in substations and industrial plants.  
IEDs perform protection, control, monitoring, and automation functions (e.g., circuit breakers, protection relays).

In this scenario, the IED publishes and subscribes to **GOOSE messages** to exchange real-time control signals.

---
### Demonstration

https://drive.google.com/drive/folders/1GDA3jNvlEIh01XwkP9DavS5b0ba15fEw?usp=sharing

---

### IEC 61850
IEC 61850 is an international standard for **substation communication and automation**.  
It defines:
- Data models for power system devices
- Communication services
- Engineering workflows

GOOSE is one of its most time-critical services.

---

### GOOSE (Generic Object-Oriented Substation Event)
GOOSE is a **Layer 2 Ethernet multicast protocol** used for **high-speed event-driven messaging** between IEDs.

Key properties:
- No TCP/IP stack
- No authentication by default
- No encryption by default
- Relies on trust and network isolation
- Uses repetition instead of acknowledgments

This makes GOOSE **extremely fast**, but also **highly vulnerable** if network access is obtained.

---

### XCBR and `Pos.stVal`
- **XCBR**: Logical node representing a **circuit breaker**

  
- **Pos.stVal**: Status value indicating breaker position  
  Common interpretations:
  - ON (Closed)
  - OFF (Open)
  - Intermediate
  - Invalid/Bad state

Manipulating this value directly influences physical switching behavior.

---

### Man-in-the-Middle (MITM) in OT Networks
In OT environments, MITM does not require ARP poisoning or session hijacking.

Because GOOSE:
- Is multicast
- Has no session state
- Has no cryptographic validation

An attacker can:
- Observe valid traffic
- Replay messages
- Modify payload values
- Inject higher-priority frames

The **last valid GOOSE message received wins**.

---

## What Is Happening in This Attack (Conceptual Flow)

A legitimate IED continuously publishes GOOSE messages reflecting the real breaker state.  
An attacker captures this traffic and learns the message structure, dataset, and control semantics.

The attacker then injects **modified GOOSE frames** containing altered control values for the same logical node.

Both legitimate and malicious messages coexist on the network.  
The subscriber IED reacts to whichever GOOSE message arrives last, causing the breaker state to **oscillate or settle incorrectly**.

This results in:
- Loss of operator trust
- Control instability
- Potential physical damage
- Safety hazards

No malware is required on the IED itself.

---

## Why This Attack Works

- GOOSE frames are **unauthenticated**
- Network-level trust is assumed
- Multicast traffic is accepted by default
- Sequence numbers and state numbers are predictable
- Legacy substations rely on air-gapping rather than cryptographic security

This is a **design trade-off**.

---

## Tools Used in the Lab

### Wireshark
Purpose:
- Capture and analyze GOOSE frames
  
Download:
- https://www.wireshark.org/download.html

### IEDScout (OMICRON)
Purpose:
- Simulate IEC 61850 IED behavior
- Act as GOOSE publisher and subscriber
- Visualize breaker state changes

Download (trial):
- https://www.omicronenergy.com/en/products/iedscout/

---

### Colasoft Packet Builder
Purpose:
- Edit captured GOOSE frames
- Modify payload values at byte/hex level
- Recalculate checksums

Download:
- https://www.colasoft.com/packet_builder/

Dependency:
- Requires Npcap

---

### Npcap
Purpose:
- Low-level packet capture and injection
- Required by Colasoft and Wireshark

Download:
- https://npcap.com/#download

---

### Bit-Twist
Purpose:
- Replay crafted packets onto the network

Download:
- https://bittwist.sourceforge.io/

Notes:
- CLI-based
- Supports `.pcap` only (not `.pcapng`)

---

## MITRE ATT&CK for ICS – Mapping

### Tactic: Impact

The attacker’s objective is to **manipulate the physical process** by altering control commands.

---

### Technique: Manipulation of Control (T0831)

Description:
> Adversaries may manipulate control logic or command messages to cause unintended physical behavior.

Application in this lab:
- Injection of forged GOOSE messages
- Modification of breaker position values
- Induced oscillation between ON and OFF states

---

## Real-World Relevance

This attack class is realistic and historically validated:
- Similar principles were used in **Stuxnet**
- Multiple substation security advisories warn about unauthenticated GOOSE
- IEC 62351 was introduced specifically to address these weaknesses

Many live substations today still operate without:
- GOOSE authentication
- Network segmentation
- OT intrusion detection

---


## Disclaimer

This material is intended strictly for **educational, defensive, and research purposes** within controlled environments.  
Testing on live industrial systems without authorization is unsafe and illegal.

---

## Reference
[CSPGWorkshop](https://github.com/ksshivran/CSPGWorkshop).
