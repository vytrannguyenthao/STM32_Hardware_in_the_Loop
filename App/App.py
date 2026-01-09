import tkinter as tk
from tkinter import ttk, scrolledtext
from tkinter import *
import serial
import serial.tools.list_ports
import threading
import subprocess
import time

# ===============================
#  SERIAL TERMINAL CLASS
# ===============================
class SerialTerminal:
    def __init__(self, frame, name):
        self.name = name
        self.ser = None
        self.reader_thread = None
        self.running = False

        # --- UI ---
        control_frame = ttk.Frame(frame)
        control_frame.pack(fill="x")

        self.port_var = tk.StringVar()
        self.baud_var = tk.StringVar(value="115200")

        ttk.Label(control_frame, text="Port:").pack(side="left", padx=2)
        self.port_combo = ttk.Combobox(control_frame, textvariable=self.port_var, width=10)
        self.port_combo.pack(side="left", padx=2)
        ttk.Button(control_frame, text="Refresh", command=self.refresh_ports).pack(side="left", padx=2)

        ttk.Label(control_frame, text="Baud:").pack(side="left", padx=2)
        self.baud_entry = ttk.Entry(control_frame, textvariable=self.baud_var, width=8)
        self.baud_entry.pack(side="left", padx=2)

        self.connect_btn = ttk.Button(control_frame, text="Connect", command=self.toggle_connection)
        self.connect_btn.pack(side="left", padx=5)

        # --- Terminal output ---
        self.text = scrolledtext.ScrolledText(frame, height=15, width=80, bg="black", fg="lime")
        self.text.pack(fill="both", expand=True)

        # --- Input ---
        self.entry = tk.Entry(frame)
        self.entry.pack(fill="x")
        self.entry.bind("<Return>", self.send_manual)

        self.refresh_ports()

    # --- Port list ---
    def refresh_ports(self):
        ports = serial.tools.list_ports.comports()
        self.port_combo["values"] = [p.device for p in ports]

    # --- Connect / Disconnect ---
    def toggle_connection(self):
        if self.ser and self.ser.is_open:
            self.disconnect()
        else:
            self.connect()

    def connect(self):
        port = self.port_var.get().strip()
        baud = int(self.baud_var.get())
        if not port:
            self.log("Please select a COM port.\n")
            return
        try:
            self.ser = serial.Serial(port, baud, timeout=1)
            self.running = True
            self.reader_thread = threading.Thread(target=self.read_thread, daemon=True)
            self.reader_thread.start()
            self.connect_btn.config(text="Disconnect")
            self.log(f"Connected to {port} @ {baud}\n")
        except serial.SerialException as e:
            self.log(f"Failed to open {port}: {e}\n")

    def disconnect(self):
        self.running = False
        if self.ser and self.ser.is_open:
            self.ser.close()
            self.log(f"Disconnected from {self.ser.port}\n")
        self.connect_btn.config(text="Connect")

    # --- Reading thread ---
    def read_thread(self):
        while self.running:
            try:
                if self.ser.in_waiting:
                    data = self.ser.readline().decode(errors='ignore').strip()
                    if data:
                        self.log(data + "\n")
            except serial.SerialException:
                self.log(f"\nLost connection to {self.ser.port}\n")
                break
            except Exception as e:
                self.log(f"\nError reading: {e}\n")
                break
            time.sleep(0.05)

    # --- Send manual command ---
    def send_manual(self, event=None):
        if not self.ser or not self.ser.is_open:
            self.log("No serial port connected.\n")
            return
        cmd = self.entry.get().strip()
        if cmd:
            self.ser.write((cmd + "\r\n").encode())
            self.log(f"> {cmd}\n")
            self.entry.delete(0, "end")
            
    # --- Logging to text box ---
    def log(self, msg):
        self.text.insert("end", msg)
        self.text.see("end")

# ===============================
#  SYSTEM TERMINAL CLASS
# ===============================
class SystemTerminal:
    def __init__(self, frame, app):
        self.app = app
        self.test_vars = {}  # Lưu trạng thái checkbox
        self.tests = {}      # Lưu hàm test tương ứng

        # --- Top control ---
        control_frame = ttk.Frame(frame)
        control_frame.pack(fill="x", pady=3)

        ttk.Label(control_frame, text="Select Tests:").pack(side="left", padx=5)

        # --- Danh sách test case ---
        self.test_cases = {
            "SPI Flash Test": self.test_spi_flash_all,
            "I2C EEPROM Test": self.test_i2c_eeprom_all,
        }

        for name in self.test_cases.keys():
            var = tk.BooleanVar()
            chk = ttk.Checkbutton(control_frame, text=name, variable=var)
            chk.pack(side="left", padx=5)
            self.test_vars[name] = var

        ttk.Button(control_frame, text="Run Selected Tests", command=self.start_selected_tests).pack(side="left", padx=8)

        # --- Terminal output ---
        self.text = scrolledtext.ScrolledText(frame, height=15, width=80, bg="black", fg="white")
        self.text.pack(fill="both", expand=True, pady=3)

        # --- Input line for PC terminal ---
        self.entry = tk.Entry(frame)
        self.entry.pack(fill="x")
        self.entry.bind("<Return>", self.run_command)

    # ==================================================
    #  Run Selected Tests (in separate thread)
    # ==================================================
    def start_selected_tests(self):
        thread = threading.Thread(target=self.run_selected_tests_thread, daemon=True)
        thread.start()

    def run_selected_tests_thread(self):
        selected = [name for name, var in self.test_vars.items() if var.get()]
        if not selected:
            self.log("⚠️ No tests selected.\n")
            return

        self.log(f"🚀 Starting {len(selected)} selected tests...\n")
        for name in selected:
            func = self.test_cases.get(name)
            if func:
                self.log(f"\n=== Running: {name} ===\n")
                try:
                    func()
                except Exception as e:
                    self.log(f"❌ Error in {name}: {e}\n")
                self.log(f"✅ Completed: {name}\n")
                self.log("-" * 50 + "\n")
        self.log("\n🎯 All selected tests completed!\n")

    # ==================================================
    #  Example Test Cases
    # ==================================================
    def test_spi_flash_all(self):
        term1 = getattr(self.app, "term1", None)
        term2 = getattr(self.app, "term2", None)

        if not term1 or not term1.ser or not term1.ser.is_open:
            self.log("⚠️ DUT not connected.\n")
            return
        if not term2 or not term2.ser or not term2.ser.is_open:
            self.log("⚠️ HIL not connected.\n")
            return

        sequence = [
            (term1, "w25q_ID"),
            (term2, "w25q_prepare_mem 256"),
            (term1, "w25q_read 256"),
            (term2, "w25q_prepare_mem 512"),
            (term1, "w25q_read 512"),
            (term1, "w25q_write 1024"),
            (term1, "w25q_read 1024"),
            (term1, "w25q_erasechip"),
            (term1, "w25q_read 1024"),
        ]

        for target, cmd in sequence:
            self.log(f"[{target.name}] → {cmd}\n")
            try:
                target.ser.write((cmd + "\r\n").encode())
            except Exception as e:
                self.log(f"❌ Error sending to {target.name}: {e}\n")
            time.sleep(1.5)
        self.log("✅ SPI Flash coordinated test done!\n")

    def test_i2c_eeprom_all(self):
        term1 = getattr(self.app, "term1", None)
        term2 = getattr(self.app, "term2", None)

        if not term1 or not term1.ser or not term1.ser.is_open:
            self.log("⚠️ DUT not connected.\n")
            return
        if not term2 or not term2.ser or not term2.ser.is_open:
            self.log("⚠️ HIL not connected.\n")
            return

        sequence = [
            (term2, "eeprom_init 0x50 1024 256"),
            (term1, "eeprom_init 0x50 1024 256"),
            (term2, "i2c_dev_active 0x50"),
            (term1, "eeprom_fill 0x0000 128"),
            (term1, "eeprom_read 0x0000 128"),
            (term2, "eeprom_deinit 0x50"),
        ]

        for target, cmd in sequence:
            self.log(f"[{target.name}] → {cmd}\n")
            try:
                target.ser.write((cmd + "\r\n").encode())
            except Exception as e:
                self.log(f"❌ Error sending to {target.name}: {e}\n")
            time.sleep(1.5)
        self.log("✅ I2C EEPROM coordinated test done!\n")

    # ==================================================
    #  Helper Functions
    # ==================================================
    def log(self, msg):
        self.text.after(0, lambda: (
            self.text.insert("end", msg),
            self.text.see("end")
        ))

    def run_command(self, event=None):
        cmd = self.entry.get().strip()
        if not cmd:
            return
        self.log(f"$ {cmd}\n")

        # ==== CUSTOM COMMANDS ====
        if cmd.startswith("clear_ser"):
            parts = cmd.split()
            target = parts[1] if len(parts) > 1 else ""
            self.handle_clear_ser(target)
            self.entry.delete(0, "end")
            return
        
        elif cmd == "clear_ter":
            self.text.delete("1.0", "end")
            self.log("🧹 Cleared PC Terminal.\n")
            self.entry.delete(0, "end")
            return
        # =====================================

        # --- Run shell command as usual ---
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.stdout:
                self.log(result.stdout)
            if result.stderr:
                self.log(result.stderr)
        except Exception as e:
            self.log(f"[Error running command: {e}]\n")
        self.entry.delete(0, "end")

    # ==================================================
    #  Handle clear_ser command
    # ==================================================
    def handle_clear_ser(self, target):
        term1 = getattr(self.app, "term1", None)
        term2 = getattr(self.app, "term2", None)

        if target in ["1", "a", "A"]:
            if term1:
                term1.text.delete("1.0", "end")
            self.log("🧹 Cleared STM32 #1 terminal.\n")

        if target in ["2", "a", "A"]:
            if term2:
                term2.text.delete("1.0", "end")
            self.log("🧹 Cleared STM32 #2 terminal.\n")

        if target not in ["1", "2", "a", "A"]:
            self.log("⚠️ Usage: clear_ser [1|2|a]\n")

# ===============================
#  MAIN APP
# ===============================
class DualSerialApp:
    def __init__(self, root):
        root.title("HIL UI")
        logo_icon = PhotoImage(file='image/logoBK.png')
        root.iconphoto(True, logo_icon)

        nb = ttk.Notebook(root)
        nb.pack(fill="both", expand=True)

        frame1 = ttk.Frame(nb)
        frame2 = ttk.Frame(nb)
        frame3 = ttk.Frame(nb)

        nb.add(frame1, text="DUT")
        nb.add(frame2, text="HIL")
        nb.add(frame3, text="PC Terminal")

        self.term1 = SerialTerminal(frame1, "DUT")
        self.term2 = SerialTerminal(frame2, "HIL")
        self.term3 = SystemTerminal(frame3, self)


if __name__ == "__main__":
    root = tk.Tk()
    app = DualSerialApp(root)
    root.state("zoomed")
    root.mainloop()
