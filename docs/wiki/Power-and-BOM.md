# Power and bill of materials

| Part | Required for |
| --- | --- |
| Arduino UNO Q with initialized Debian | Both modes |
| Supported 3.5-inch parallel ILI9486 UNO shield | Portrait handheld display |
| USB data cable and adequate 5 V / 3 A source | Power and installation |
| Supported USB Wi-Fi adapter | Monitor capture; onboard capture remains unverified |
| Powered USB-C hub with DP Alt Mode HDMI, keyboard and mouse | Desk lab |
| Battery or AC UPS | Untethered operation or outage tolerance |
| Enclosure, standoffs, strain relief | Portable assembly |

[Full BOM and actual assembly photos](https://github.com/valleytechsolutions/Q-Marauder/blob/main/docs/BOM.md)

## Suggested power direction

- **Desk:** a region-appropriate AC UPS, such as the CyberPower ST425 120 V model,
  powering the normal USB-C supply, hub and monitor. Size for the measured load.
- **Handheld UPS prototype:** Waveshare UPS Module 3S as a separately enclosed,
  cabled module. It needs suitable cells, the specified charger and verification
  of USB-C negotiation and uninterrupted switchover.
- **Portable battery alternative:** Voltaic V75 is a candidate, but its USB-C PD
  port is not covered by its USB-A Always On feature. Pass-through charging alone
  does not establish seamless UPS operation.

None has been tested with the complete Q-Marauder assembly. Do not stack a
Raspberry Pi UPS HAT on UNO headers or backfeed the 5 V rail. No low-battery
shutdown integration is currently implemented.

See [power specifications, manufacturer sources and acceptance tests](https://github.com/valleytechsolutions/Q-Marauder/blob/main/docs/POWER.md)
before buying. The desktop hub and battery must support the board **and** attached
peripherals; a high headline PD wattage alone does not establish that.
