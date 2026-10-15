"""
Host-side link to the Marlin firmware running on the MKS TinyBee (ESP32).

Sends G-code over USB serial using Marlin's line-number + checksum protocol
and waits for "ok" after every line, so the firmware queue never overflows.

Library use:
    from marlin_host import MarlinHost
    with MarlinHost("/dev/cu.usbserial-0001") as m:
        m.send("G91")
        m.send("G1 X10 F360")

Command line:
    python3 marlin_host.py --list
    python3 marlin_host.py -p COM3 ../TEST-X.gcode
    python3 marlin_host.py -p COM3 -c "M114"
"""

import argparse
import re
import sys
import threading
import time

import serial
import serial.tools.list_ports

BAUDRATE = 115200          # Configuration.h: BAUDRATE
BOOT_WAIT_S = 3.0          # time for Marlin to print its boot banner
IDLE_TIMEOUT_S = 15.0      # no output at all for this long -> give up
                           # (Marlin sends "busy" keepalives every 2 s during long moves)


class MarlinError(Exception):
    pass


def list_ports():
    return [(p.device, p.description) for p in serial.tools.list_ports.comports()]


def clean_line(line):
    """Strip ';' comments and whitespace. Returns '' for blank/comment lines."""
    return line.split(";", 1)[0].strip()


def checksum(text):
    cs = 0
    for ch in text.encode("ascii"):
        cs ^= ch
    return cs


class MarlinHost:
    def __init__(self, port, baudrate=BAUDRATE, on_line=None):
        self.port = port
        self.baudrate = baudrate
        self.on_line = on_line or (lambda line: None)
        self.ser = None
        self.position = {}

        self._line_no = 0
        self._history = {}
        self._resend_from = None
        self._ok = threading.Event()
        self._last_rx = 0.0
        self._halted = False
        self._send_lock = threading.Lock()
        self._reader = None
        self._running = False

    # -- connection ---------------------------------------------------------

    def connect(self):
        self.ser = serial.Serial()
        self.ser.port = self.port
        self.ser.baudrate = self.baudrate
        self.ser.timeout = 0.2
        # Keep the ESP32 auto-reset lines idle so opening the port doesn't reboot the board.
        self.ser.dtr = False
        self.ser.rts = False
        self.ser.open()

        self._running = True
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()
        self.resync()
        return self

    def resync(self):
        """Wait for the boot banner and reset the line counter (after connect or hard_reset)."""
        time.sleep(BOOT_WAIT_S)
        self._halted = False
        self._resend_from = None
        self._line_no = 0
        self._history.clear()
        self.send("M110 N0", numbered=False)   # reset Marlin's line counter

    def close(self):
        self._running = False
        if self._reader:
            self._reader.join(timeout=1)
        if self.ser and self.ser.is_open:
            self.ser.close()

    def __enter__(self):
        return self.connect()

    def __exit__(self, *exc):
        self.close()

    def hard_reset(self):
        """Reboot the ESP32 via the EN line (RTS). This is the only immediate stop:
        EMERGENCY_PARSER is not available on ESP32 in Marlin 2.0.9.2, so M112/M410
        would wait behind already-queued moves. Steppers are released after the reboot."""
        self.ser.dtr = False
        self.ser.rts = True
        time.sleep(0.1)
        self.ser.rts = False
        self._ok.set()  # wake any blocked sender
        self._halted = True

    # -- sending ------------------------------------------------------------

    def send(self, command, numbered=True):
        """Send one G-code line and block until Marlin answers 'ok'."""
        command = clean_line(command)
        if not command:
            return
        if self._halted:
            raise MarlinError("Board was reset/halted - reconnect first.")

        with self._send_lock:
            if numbered:
                self._line_no += 1
                self._history[self._line_no] = command
                self._history.pop(self._line_no - 100, None)
                self._write(self._line_no, command)
            else:
                self._write_raw(command)
            self._wait_ok()

    def send_many(self, lines, should_stop=None):
        for line in lines:
            if should_stop and should_stop():
                return False
            self.send(line)
        return True

    def send_file(self, path, should_stop=None):
        with open(path, encoding="utf-8", errors="replace") as f:
            return self.send_many(f, should_stop)

    def query_position(self):
        """M114 -> {'X': 10.0, 'Y': 0.0, ...}"""
        self.send("M114")
        return dict(self.position)

    def _write(self, n, command):
        body = "N{} {}".format(n, command)
        self._write_raw("{}*{}".format(body, checksum(body)))

    def _write_raw(self, text):
        self._ok.clear()
        self.ser.write((text + "\n").encode("ascii"))

    def _wait_ok(self):
        self._last_rx = time.time()
        while not self._ok.wait(0.2):
            if not self._running:
                raise MarlinError("Connection closed.")
            if time.time() - self._last_rx > IDLE_TIMEOUT_S:
                raise MarlinError("Timeout: no response from Marlin.")
        if self._halted:
            raise MarlinError("Marlin halted.")

    # -- receiving ----------------------------------------------------------

    def _read_loop(self):
        while self._running:
            try:
                raw = self.ser.readline()
            except (serial.SerialException, OSError):
                self._running = False
                self._ok.set()
                break
            if not raw:
                continue
            line = raw.decode("ascii", errors="replace").strip()
            if not line:
                continue
            self._last_rx = time.time()
            self.on_line(line)
            self._handle(line)

    def _handle(self, line):
        low = line.lower()
        if low.startswith("ok"):
            if self._resend_from is not None:
                n, self._resend_from = self._resend_from, None
                if n in self._history:
                    self._write(n, self._history[n])
                    return
            self._ok.set()
        elif low.startswith("resend:") or low.startswith("rs:"):
            self._resend_from = int(re.findall(r"\d+", line)[0])
        elif "halted" in low or "kill()" in low:
            self._halted = True
            self._ok.set()
        elif line.startswith("X:"):
            # "X:10.00 Y:0.00 Z:0.00 Count X:158 Y:0 Z:0"
            for axis, val in re.findall(r"([XYZEABC]):(-?\d+\.\d+)", line.split("Count")[0]):
                self.position[axis] = float(val)


def main():
    ap = argparse.ArgumentParser(description="Send G-code to Marlin on the TinyBee.")
    ap.add_argument("files", nargs="*", help=".gcode files to stream")
    ap.add_argument("-p", "--port", help="serial port, e.g. COM3 or /dev/cu.usbserial-0001")
    ap.add_argument("-c", "--command", action="append", default=[], help="single G-code line (repeatable)")
    ap.add_argument("--list", action="store_true", help="list serial ports")
    args = ap.parse_args()

    if args.list or not args.port:
        for dev, desc in list_ports():
            print("{:30} {}".format(dev, desc))
        if not args.port:
            print("\nPass the board's port with -p.")
        return

    with MarlinHost(args.port, on_line=lambda l: print("<", l)) as m:
        try:
            for cmd in args.command:
                print(">", cmd)
                m.send(cmd)
            for path in args.files:
                print("== streaming", path)
                m.send_file(path)
        except KeyboardInterrupt:
            print("\nCtrl+C -> resetting board to stop motion")
            m.hard_reset()
            sys.exit(1)


if __name__ == "__main__":
    main()
