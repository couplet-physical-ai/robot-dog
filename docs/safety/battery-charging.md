# Battery and charging

**Status:** attended charging control
**Reviewed:** 2026-08-21

> **Hold:** Do not charge an unidentified, damaged, swollen, wet, leaking, hot, or recently used battery. Follow the delivered unit's actual battery/charger manual before proceeding.

## Rules

- **Official/vendor basis:** use only the battery and charger supplied or explicitly approved by Unitree for that exact Go2 configuration. Do not infer compatibility from voltage, connector fit, a product page, or another unit.
- **Project requirement:** charging is attended. Remove the battery from the robot, switch the battery off, and charge it on a stable, nonflammable surface with clearance from combustibles and a responsible person present.
- Do not charge immediately after use. Allow the battery and robot to cool according to the delivered manual; do not invent a cooling interval.
- Do not charge in the robot, in a vehicle, near water, on soft/flammable material, or while the battery/charger is covered.
- Do not use a damaged cable, altered charger, adapter, extension arrangement, or nonmatching battery. Do not open, modify, parallel, short, or repair the battery.
- Keep charging separate from any network or control session. A powered-off robot has no motion authority, but charging still requires physical supervision.

## Procedure

1. End operation and place the robot in its approved safe state. Disconnect command-capable software.
2. Wait for cooling. Inspect the battery, contacts, charger, cable, and surface. If any condition is uncertain, stop.
3. Power the robot off. Remove the battery and switch it off using the delivered manual's procedure; do not force a latch or connector.
4. Match the battery and official charger to the delivered unit's model/configuration. If the manual or match is unavailable, do not charge.
5. Place the battery on the nonflammable charging surface. Keep the area clear, dry, ventilated, and attended for the entire charge.
6. Connect and observe the official charger indicators and battery behavior. Stop if there is unusual heat, odor, noise, smoke, swelling, leakage, sparking, or a charger fault. Do not handle a damaged or smoking battery; clear the area and follow the site's battery incident procedure.
7. When the delivered manual indicates charging is complete, disconnect the charger, switch the battery off, and allow it to cool before storage or reinstallation.
8. Reinstall only with the robot powered off and after the post-charge inspection passes. Record a sanitized result in the private inventory.

## Vendor facts versus project controls

- **Official:** Unitree publishes Go2 configuration/battery information and charging instructions in its product/manual materials. Exact battery and charger details are configuration- and revision-dependent.
- **Project:** official matched hardware, battery removed and off, attended charging, nonflammable surface, no immediate post-use charging, and a stop on any uncertainty or damage.
- **Not established by this page:** battery chemistry, charge time, temperature limits, charger indicator meanings, or emergency handling for the delivered unit. Inspect its actual manual.

Software health, RPC timeout, or `StopMove` has no authority over a battery fire or charging incident. Use the site's physical battery incident procedure.

## Sources

Official sources, accessed **2026-08-21**:

- [Unitree Go2 User Manual](https://marketing.unitree.com/article/en/Go2/User_Manual.html)
- [Unitree Document Center](https://support.unitree.com/main/en)
- [Unitree Go2 product page](https://www.unitree.com/go2/)

The delivered battery/charger labels and manual take precedence over mutable web material. This page is an **operator safety requirement**, not a substitute for the delivered manual or site emergency procedure.
