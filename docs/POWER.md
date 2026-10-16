# Handheld power and desk UPS

Recommendations researched 2026-10-15. These are candidates, not hardware that has
been validated with this particular shield, hub and radio assembly.

## Electrical requirements

The UNO Q accepts **5 V / 3 A over USB-C** and requests the 5 V PD profile. Its
USB-C port also carries DisplayPort Alt Mode. VIN is a separate 7–24 V input;
do not apply that voltage to the 5 V pin or USB-C. See Arduino's
[power specification](https://docs.arduino.cc/tutorials/uno-q/power-specification/)
and [datasheet](https://docs.arduino.cc/resources/datasheets/ABX00162-datasheet.pdf).

Budget for the hub and USB radio as well as the board and TFT. A high wattage
printed on a charger does not prove that its 5 V profile or a hub's downstream
power path is adequate. Use a full-featured USB-C cable for video/data.

## Suggested options

| Use | Candidate | Why / limitation |
| --- | --- | --- |
| Handheld prototype with true UPS intent | [Waveshare UPS Module 3S](https://www.waveshare.com/wiki/UPS_Module_3S) | Manufacturer describes simultaneous charging/discharging and a regulated 5 V output, rated up to 5 A. Requires three suitable 18650 cells, the specified charger, enclosure and power-path validation. Treat it as a **cabled module**, not a UNO shield. USB-C negotiation and switchover with UNO Q are untested. |
| Simple portable battery | [Voltaic V75](https://voltaicsystems.com/v75) | Has a USB-C PD output and pass-through charging. Its documented Always On feature is on USB-A, **not the USB-C PD port**; the USB-A rating does not establish a continuous 3 A UNO Q supply. Do not treat it as a verified seamless UPS. Confirm the exact revision: the vendor page has conflicting capacity descriptions. |
| Desk lab, monitor and hub | [CyberPower ST425](https://www.cyberpower.com/mx/es/product/sku/st425) or an equivalent region-appropriate AC UPS | The manufacturer specifies 425 VA / 260 W and 120 V outlets for this model. Connect the existing USB-C power supply and monitor to battery-backed outlets. Size by the measured total load and desired runtime; verify your regional outlet/voltage version. |

For the first desk build, an **AC UPS powering the normal USB-C supply, hub and
monitor** is the least invasive option. For a portable enclosure, the Waveshare
module is an integration candidate; it is not yet a plug-and-play recommendation.
Avoid the 5 V / 2.5 A UPS Module Mini for a design requiring the board's full 3 A input.

## Acceptance test before relying on a battery

1. Measure the complete system under scanning, display redraw and USB-radio load.
2. Verify sustained 5 V supply and no board reset when charger power is removed
   and restored. Repeat at high and low battery charge.
3. Check battery/charger temperature inside the intended enclosure and follow
   the module manufacturer's cell and charging instructions.
4. Add supported low-battery telemetry and a graceful Debian shutdown before
   treating it as an unattended UPS. Q-Marauder does not yet implement this.

An estimate is `usable battery Wh / measured system W`. For example, **if** a
40 Wh pack delivers 80% usable energy and the build averages 8 W, the estimate is
4 hours. These are example assumptions, not measurements of this build.

Do not stack Raspberry Pi UPS HATs on UNO headers or connect two unverified 5 V
sources together. The TFT already occupies the UNO shield headers.
