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

### Xbox controller

Connect the controller by USB or Bluetooth before or after opening the GUI. The panel
shows its name when it's detected. `pygame` is required; without it the GUI works as before.

| Input | Action |
|---|---|
| Left stick ←/→ | rotate base; speed follows how far you push (max = Speed box) |
| D-pad ←/→ | −1° / +1° |
| LB / RB | −10° / +10° |
| A | go to 0° |
| X | set current position as 0° (G92 X0) |
| Y | read position (M114) |
| Menu | motors on (M17) |
| **B** | **STOP** (resets the board, same as the red button) |

Stick moves are sent as short 0.1 s segments, paced in real time, so only a fraction of a
second of motion is queued at once. With the firmware's low acceleration (30°/s²), the
base still needs up to ~15° to stop from full speed (30°/s).

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
