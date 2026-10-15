"""
Desktop control panel for the robotic arm (Marlin on MKS TinyBee / ESP32).

    python3 gui.py

X = robot base, in degrees (firmware: M92 X15.80, no soft limits on X).
"""

import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from marlin_host import MarlinError, MarlinHost, clean_line, list_ports

JOG_STEPS = (1, 10, 45, 90)
DEFAULT_FEED = 360     # deg/min = 6 deg/s (firmware max is 30 deg/s = F1800)
MAX_FEED = 1800


class App:
    def __init__(self, root):
        self.root = root
        self.host = None
        self.jobs = queue.Queue()        # callables run on the worker thread
        self.rx = queue.Queue()          # lines from Marlin -> console
        self.stop_flag = threading.Event()

        root.title("Robotic Hand - Marlin control")
        root.minsize(640, 480)
        self._build()
        threading.Thread(target=self._worker, daemon=True).start()
        self._poll_rx()
        self._refresh_ports()

    # -- UI -----------------------------------------------------------------

    def _build(self):
        pad = {"padx": 4, "pady": 4}

        top = ttk.Frame(self.root)
        top.pack(fill="x", **pad)
        ttk.Label(top, text="Port:").pack(side="left")
        self.port_var = tk.StringVar()
        self.port_box = ttk.Combobox(top, textvariable=self.port_var, width=32)
        self.port_box.pack(side="left", **pad)
        ttk.Button(top, text="Refresh", command=self._refresh_ports).pack(side="left")
        self.conn_btn = ttk.Button(top, text="Connect", command=self._toggle_connect)
        self.conn_btn.pack(side="left", **pad)
        self.status = ttk.Label(top, text="disconnected", foreground="gray")
        self.status.pack(side="left", **pad)

        stop = tk.Button(top, text="STOP", bg="#c62828", fg="white", font=("", 12, "bold"),
                         command=self._stop)
        stop.pack(side="right", **pad)

        base = ttk.LabelFrame(self.root, text="Base (X, degrees)")
        base.pack(fill="x", **pad)

        row = ttk.Frame(base)
        row.pack(fill="x", **pad)
        for step in reversed(JOG_STEPS):
            ttk.Button(row, text="-{}°".format(step), width=6,
                       command=lambda s=step: self._jog(-s)).pack(side="left")
        self.pos_label = ttk.Label(row, text="X: ?", width=14, anchor="center", font=("", 12))
        self.pos_label.pack(side="left", padx=10)
        for step in JOG_STEPS:
            ttk.Button(row, text="+{}°".format(step), width=6,
                       command=lambda s=step: self._jog(s)).pack(side="left")

        row2 = ttk.Frame(base)
        row2.pack(fill="x", **pad)
        ttk.Label(row2, text="Go to angle:").pack(side="left")
        self.target = ttk.Entry(row2, width=8)
        self.target.insert(0, "0")
        self.target.pack(side="left", **pad)
        ttk.Button(row2, text="Go", command=self._goto).pack(side="left")
        ttk.Label(row2, text="   Speed (deg/min):").pack(side="left")
        self.feed = tk.IntVar(value=DEFAULT_FEED)
        ttk.Spinbox(row2, from_=10, to=MAX_FEED, increment=60, textvariable=self.feed,
                    width=6).pack(side="left", **pad)

        row3 = ttk.Frame(base)
        row3.pack(fill="x", **pad)
        ttk.Button(row3, text="Set here as 0° (G92)", command=lambda: self._queue_cmds(["G92 X0"], True)).pack(side="left")
        ttk.Button(row3, text="Motors ON (M17)", command=lambda: self._queue_cmds(["M17"])).pack(side="left", **pad)
        ttk.Button(row3, text="Motors OFF (M18)", command=self._motors_off).pack(side="left")
        ttk.Button(row3, text="Read position (M114)", command=lambda: self._queue_cmds([], True)).pack(side="left", **pad)
        ttk.Button(row3, text="Run .gcode file…", command=self._run_file).pack(side="right")

        con = ttk.LabelFrame(self.root, text="Console")
        con.pack(fill="both", expand=True, **pad)
        self.log = scrolledtext.ScrolledText(con, height=12, state="disabled", font=("Courier", 11))
        self.log.pack(fill="both", expand=True, **pad)
        entry_row = ttk.Frame(con)
        entry_row.pack(fill="x", **pad)
        self.cmd = ttk.Entry(entry_row)
        self.cmd.pack(side="left", fill="x", expand=True)
        self.cmd.bind("<Return>", lambda e: self._send_entry())
        ttk.Button(entry_row, text="Send", command=self._send_entry).pack(side="left", **pad)

    def _print(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _poll_rx(self):
        while not self.rx.empty():
            self._print(self.rx.get())
        if self.host and "X" in self.host.position:
            self.pos_label.config(text="X: {:.2f}°".format(self.host.position["X"]))
        self.root.after(100, self._poll_rx)

    def _refresh_ports(self):
        ports = list_ports()
        self.port_box["values"] = [p[0] for p in ports]
        if ports and not self.port_var.get():
            # TinyBee shows up as a CH340 / USB-serial device
            likely = [p[0] for p in ports if "usb" in (p[0] + p[1]).lower() or "ch34" in p[1].lower()]
            self.port_var.set((likely or [ports[0][0]])[0])

    # -- connection -----------------------------------------------------------

    def _toggle_connect(self):
        if self.host:
            self.host.close()
            self.host = None
            self._set_status("disconnected", "gray")
            self.conn_btn.config(text="Connect")
            return
        port = self.port_var.get().strip()
        if not port:
            messagebox.showerror("Port", "Choose a serial port.")
            return
        self._set_status("connecting…", "orange")

        def job():
            host = MarlinHost(port, on_line=lambda l: self.rx.put("< " + l))
            host.connect()
            self.host = host
            host.send("M115")
            host.send("M92")                      # shows steps/unit - expect X15.80
            host.query_position()
            self.root.after(0, lambda: (self._set_status("connected", "green"),
                                        self.conn_btn.config(text="Disconnect")))
        self.jobs.put(job)

    def _set_status(self, text, color):
        self.status.config(text=text, foreground=color)

    # -- actions --------------------------------------------------------------

    def _queue_cmds(self, cmds, then_position=False):
        if not self.host:
            messagebox.showwarning("Not connected", "Connect to the board first.")
            return

        def job():
            for c in cmds:
                if self.stop_flag.is_set():
                    return
                self.rx.put("> " + c)
                self.host.send(c)
            if then_position:
                self.host.query_position()
        self.jobs.put(job)

    def _feed(self):
        return max(1, min(MAX_FEED, int(self.feed.get())))

    def _jog(self, degrees):
        self._queue_cmds(["G91", "G1 X{} F{}".format(degrees, self._feed()), "G90", "M400"], True)

    def _goto(self):
        try:
            angle = float(self.target.get())
        except ValueError:
            messagebox.showerror("Angle", "Enter a number.")
            return
        self._queue_cmds(["G90", "G1 X{} F{}".format(angle, self._feed()), "M400"], True)

    def _motors_off(self):
        if messagebox.askyesno("Motors off", "Release holding torque? The arm may move freely."):
            self._queue_cmds(["M18"])

    def _send_entry(self):
        text = clean_line(self.cmd.get())
        self.cmd.delete(0, "end")
        if text:
            self._queue_cmds([text], text.upper().startswith(("G0", "G1", "G92")))

    def _run_file(self):
        path = filedialog.askopenfilename(filetypes=[("G-code", "*.gcode *.gco *.g *.nc"), ("All", "*")])
        if not path or not self.host:
            return

        def job():
            self.rx.put("== running " + path)
            done = self.host.send_file(path, should_stop=self.stop_flag.is_set)
            self.rx.put("== finished" if done else "== aborted")
            self.host.query_position()
        self.jobs.put(job)

    def _stop(self):
        """Drop everything queued and reboot the board (only immediate stop on ESP32 Marlin)."""
        self.stop_flag.set()
        while not self.jobs.empty():
            self.jobs.get_nowait()
        if not self.host:
            self.stop_flag.clear()
            return
        self.rx.put("!! STOP - resetting board, motors will be released")
        self.host.hard_reset()
        self._set_status("resetting…", "orange")

        def job():
            self.stop_flag.clear()
            self.host.resync()
            self.host.position.clear()
            self.rx.put("!! board restarted - position is unknown, set 0° again (G92)")
            self.root.after(0, lambda: (self._set_status("connected", "green"),
                                        self.pos_label.config(text="X: ?")))
        self.jobs.put(job)

    # -- worker ---------------------------------------------------------------

    def _worker(self):
        while True:
            job = self.jobs.get()
            try:
                job()
            except (MarlinError, OSError) as e:
                self.rx.put("!! " + str(e))
                if self.host is None or "connect" in str(e).lower():
                    self.root.after(0, lambda: self._set_status("error", "red"))
            except Exception as e:  # keep the worker alive
                self.rx.put("!! {}: {}".format(type(e).__name__, e))


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
