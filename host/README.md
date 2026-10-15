# Host app: PC → G-code → Marlin on the TinyBee (ESP32)

```
 PC (this folder)                     MKS TinyBee (ESP32, Marlin 2.0.9.2)
 gui.py / marlin_host.py  ──USB 115200──▶  G-code parser ─▶ planner ─▶ STEP/DIR ─▶ TMC2209 ─▶ motors
```

The firmware in `../Marlin` stays on the ESP32 and drives the motors. This app only
sends G-code lines and waits for Marlin's `ok` after each one. Every line goes out with a
line number and checksum, and resend requests are handled.

## Install

```
pip install -r requirements.txt
```

The GUI needs Python with a working Tk. On Windows, python.org Python works.
On macOS, use the python.org installer: Apple's `/usr/bin/python3` ships Tk 8.5, which
crashes on macOS 26.

## Use

GUI:

```
python gui.py
```

The GUI has port selection, base jog (±1/10/45/90°), go-to-angle, speed, set-zero (G92 X0),
motors on/off, M114 position, a console, a G-code file runner, and **STOP**.

Command line:

```
python marlin_host.py --list                         # find the port
python marlin_host.py -p COM3 -c M114                # single command
python marlin_host.py -p COM3 ../TEST-X.gcode        # stream a file
```

From your own Python code:

```python
from marlin_host import MarlinHost
with MarlinHost("COM3") as m:
    m.send("G91")
    m.send("G1 X10 F360")
    print(m.query_position())
```

## Things to know

- **STOP reboots the board** (pulses EN through the USB-serial RTS line). Marlin's
  `EMERGENCY_PARSER` is not supported on ESP32, so `M112`/`M410` would only run after the
  queued moves. After a reboot the motors are released and the position is unknown, so set 0° again.
- No homing (`G28`): no endstops are configured. Zero the base with `G92 X0`.
- X is in degrees of base rotation (M92 X15.80). Y/Z are not configured yet (1 step/unit, A4988).
