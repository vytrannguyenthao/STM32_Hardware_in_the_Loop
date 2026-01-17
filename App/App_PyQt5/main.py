from html import parser
import sys
import time
import serial
import serial.tools.list_ports

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QHBoxLayout, QVBoxLayout, QGroupBox,
    QPushButton, QTextEdit, QLineEdit,
    QTableWidget, QTableWidgetItem,
    QHeaderView, QSplitter, QLabel,
    QComboBox, QCheckBox, QTabWidget
)
from PyQt5.QtGui import QIcon, QBrush, QColor
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer

# ==================================================
# SPI PARSER
# ==================================================
class SPIParser:
    def __init__(self, emit_cb, log_cb, clear_cb, pc_log_cb, test_complete_cb=None, highlight_error_cb=None):
        self.emit_cb = emit_cb
        self.log_cb = log_cb
        self.clear_cb = clear_cb
        self.pc_log_cb = pc_log_cb
        self.test_complete_cb = test_complete_cb
        self.highlight_error_cb = highlight_error_cb

        self.active = False
        self.expected = 0
        self.buffer = []

        self.wait_id = False # support for Read ID Flash
        
        # SPI Write Test
        self.write_test_data = None  # Data chuẩn bị để test write
        self.write_test_addr = 0
        self.write_test_size = 0
        self.write_test_pending = False  # Flag để theo dõi write test

    def feed(self, line):
        # echo command
        if line.startswith("w25q_read"):
            try:
                _, n = line.split()
                self.expected = int(n)
                self.buffer.clear()
                self.active = True
                self.clear_cb() # Clear table
                return True
            except:
                return True
        elif line.startswith("w25q_write"):
            try:
                _, n = line.split()
                addr = int(n)
                # Prepare write test data
                self.prepare_write_test_data(addr)
                self.write_test_pending = True
                return True
            except:
                return True
        elif line.startswith("w25q_prepare_mem"):
            try:
                _, n = line.split()
                addr = int(n)
                # Prepare memory test data (same as write test)
                self.prepare_write_test_data(addr)
                self.pc_log_cb(f"Memory prepared at 0x{addr:04X}, size={self.write_test_size}")
                return True
            except:
                return True
        elif line.startswith("w25q_ID"):
            self.wait_id = True
            return True   # skip echo

        # info
        if self.active and line.startswith("Read"):
            return True
        
        # Check for Invalid length
        if self.write_test_pending and "invalid length" in line.lower():
            self.pc_log_cb("FAIL (Invalid length)")
            self.write_test_pending = False
            if self.test_complete_cb:
                self.test_complete_cb("spi")
            return True
        
        if self.wait_id and line.startswith("W25Q ID:"):
            try:
                raw = line.split("0x")[1]
                flash_id = raw[-6:].upper()

                if flash_id == "EF4018":
                    self.pc_log_cb(f"PASS (ID = {flash_id})")
                else:
                    self.pc_log_cb(f"FAIL (ID = {flash_id})")

            except:
                self.pc_log_cb("Flash ID PARSE ERROR")

            self.wait_id = False
            if self.test_complete_cb:
                self.test_complete_cb("spi")
            return True

        # data
        if self.active:
            for p in line.split():
                if p.startswith("0x"):
                    try:
                        self.buffer.append(int(p, 16))
                    except:
                        pass

            if len(self.buffer) >= self.expected:
                for addr, val in enumerate(self.buffer[:1024]):
                    self.emit_cb(addr, val)

                # Compare with write test data if available
                if self.write_test_data:
                    self.compare_write_test()
                    self.write_test_pending = False
                
                self.active = False
                if self.test_complete_cb:
                    self.test_complete_cb("spi")

            return True

        return False
    
    def prepare_write_test_data(self, addr):
        """Prepare test data: 00 01 02 ... FF 00 01 ... repeat (flexible size)"""
        self.write_test_data = [(i % 256) for i in range(addr)]
        self.write_test_addr = addr
        self.write_test_size = addr
    
    def compare_write_test(self):
        """Compare received data with prepared write test data"""
        if not self.write_test_data or len(self.buffer) != len(self.write_test_data):
            self.pc_log_cb("FAIL (size mismatch)")
            return
        
        # Compare data
        mismatches = []
        for i, (expected, received) in enumerate(zip(self.write_test_data, self.buffer)):
            if expected != received:
                mismatches.append((i, expected, received))
        
        if not mismatches:
            self.pc_log_cb("PASS")
        else:
            # Highlight error cells
            if self.highlight_error_cb:
                for addr, exp, rcv in mismatches:
                    self.highlight_error_cb(addr)
            
            # Show first few mismatches
            msg = f"FAIL ({len(mismatches)} mismatches)"
            for i, exp, rcv in mismatches[:5]:
                msg += f"\n  [0x{i:04X}] expected 0x{exp:02X}, got 0x{rcv:02X}"
            if len(mismatches) > 5:
                msg += f"\n  ... and {len(mismatches) - 5} more"
            self.pc_log_cb(msg)
    
    def reset(self):
        """Reset all test parameters"""
        self.active = False
        self.expected = 0
        self.buffer = []
        self.wait_id = False
        self.write_test_data = None
        self.write_test_addr = 0
        self.write_test_size = 0
        self.write_test_pending = False

    def set_prepare_mem_size(self, size):
        """Set size for prepare_mem test (called from MainWindow)"""
        self.prepare_write_test_data(size)

    def set_erase_test_data(self):
        """Set test data for erase chip test (1024 bytes of 0xFF)"""
        self.write_test_data = [0xFF] * 1024
        self.write_test_addr = 0
        self.write_test_size = 1024

# ==================================================
# I2C EEPROM PARSER
# ==================================================
class I2CParser:
    def __init__(self, emit_cb, log_cb, clear_cb, test_complete_cb=None):
        self.emit_cb = emit_cb
        self.log_cb = log_cb
        self.clear_cb = clear_cb
        self.test_complete_cb = test_complete_cb
        self.active = False
        self.base_addr = 0
        self.expected = 0
        self.buffer = []

    def feed(self, line):
        # ==========================
        # 1. detect echo command
        # ==========================
        if line.startswith("eeprom_read"):
            try:
                _, addr, n = line.split()
                self.base_addr = int(addr, 16)
                self.expected = int(n)
                self.buffer.clear()
                self.active = True
                self.clear_cb() # Clear table
                return True
            except:
                return True

        # ==========================
        # 2. check for FAIL
        # ==========================
        if self.active and "FAIL" in line.upper():
            self.log_cb("[I2C] EEPROM read FAILED")
            self.active = False
            if self.test_complete_cb:
                self.test_complete_cb("i2c")
            return True

        # ==========================
        # 3. info header
        # ==========================
        if self.active and line.startswith("EEPROM read"):
            return True

        # ==========================
        # 4. data
        # ==========================
        if self.active:
            for p in line.split():
                try:
                    self.buffer.append(int(p, 16))
                except:
                    pass

            if len(self.buffer) >= self.expected:
                for i, val in enumerate(self.buffer):
                    addr = self.base_addr + i
                    self.emit_cb(addr, val)

                self.log_cb("[I2C] EEPROM read completed")
                self.active = False
                if self.test_complete_cb:
                    self.test_complete_cb("i2c")

            return True

        return False

    def reset(self):
        """Reset all test parameters"""
        self.active = False
        self.base_addr = 0
        self.expected = 0
        self.buffer = []

# ==================================================
# UART THREAD
# ==================================================
class UARTThread(QThread):
    log_signal = pyqtSignal(str)
    spi_data = pyqtSignal(int, int)
    i2c_data = pyqtSignal(int, int)
    spi_clear = pyqtSignal()
    i2c_clear = pyqtSignal()
    pc_log_signal = pyqtSignal(str)
    test_completed = pyqtSignal(str)  # Signal để thông báo test hoàn thành

    def __init__(self, name):
        super().__init__()
        self.name = name
        self.running = False
        self.ser = None
        self.spi_parser = SPIParser(self.spi_data.emit, self.log_signal.emit, self.spi_clear.emit, self.pc_log_signal.emit, self.test_completed.emit)
        self.i2c_parser = I2CParser(self.i2c_data.emit, self.log_signal.emit, self.i2c_clear.emit, self.test_completed.emit)

    def open(self, port, baud):
        self.port = port
        self.baud = baud
        self.running = True
        self.start()

    def run(self):
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=0.1)
            self.log_signal.emit(f"[{self.name}] Connected {self.port} @ {self.baud}")

            while self.running:
                if self.ser.in_waiting:
                    line = self.ser.readline().decode(errors="ignore").strip()
                    if line:
                        self.handle_line(line)
                time.sleep(0.01)

        except Exception as e:
            self.log_signal.emit(f"[{self.name}] ERROR: {e}")

        finally:
            if self.ser:
                self.ser.close()
            self.log_signal.emit(f"[{self.name}] Disconnected")

    def close(self):
        self.running = False

    def send(self, text):
        if self.ser and self.ser.is_open:
            self.ser.write((text + "\r\n").encode())
            # self.log_signal.emit(f"[{self.name} TX] {text}")

    def handle_line(self, line):
        # self.log_signal.emit(f"[{self.name} RX] {line}")
        self.log_signal.emit(f"{line}")
        line = line.strip()

        if self.spi_parser.feed(line):
            return
        if self.i2c_parser.feed(line):
            return

        # try:
        #     t, addr, val = line.split()
        #     addr = int(addr, 0)
        #     val = int(val, 0)

        #     if t.upper() == "SPI":
        #         self.spi_data.emit(addr, val)
        #     elif t.upper() == "I2C":
        #         self.i2c_data.emit(addr, val)
        # except:
        #     pass


# ==================================================
# MAIN WINDOW
# ==================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HIL Simulation UI")
        self.setWindowIcon(QIcon("App_PyQt5/img/logoBK.png"))

        splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(splitter)

        self.uart_dut = UARTThread("DUT")
        self.uart_hil = UARTThread("HIL")

        # Initialize test queue
        self.test_queue = []
        self.current_test = None
        self.is_running_tests = False  # Flag để theo dõi xem có đang chạy tests hay không

        self.uart_dut.log_signal.connect(self.append_dut_log)
        self.uart_hil.log_signal.connect(self.append_hil_log)

        self.uart_dut.spi_data.connect(self.update_spi)
        self.uart_dut.spi_clear.connect(self.clear_spi_table)

        self.uart_dut.i2c_data.connect(self.update_i2c)
        self.uart_dut.i2c_clear.connect(self.clear_i2c_table)

        self.uart_dut.pc_log_signal.connect(self.pc_log_append)
        self.uart_dut.test_completed.connect(self.on_test_completed)
        
        # Set highlight callback for SPI parser
        self.uart_dut.spi_parser.highlight_error_cb = self.highlight_spi_error

        splitter.addWidget(self.build_left())
        splitter.addWidget(self.build_center())

        splitter.setSizes([350, 1450])

    # ==================================================
    # LEFT PANEL
    # ==================================================
    def build_left(self):
        main_splitter = QSplitter(Qt.Vertical)

        # ================= TOP: CONTROLS + TEST =================
        top = QWidget()
        top_lay = QVBoxLayout(top)

        top_lay.addWidget(self.create_uart_control("DUT", self.uart_dut))
        top_lay.addWidget(self.create_uart_control("HIL", self.uart_hil))

        # ---------- Test cases ----------
        test_box = QGroupBox("Test Cases")
        tlay = QVBoxLayout(test_box)

        self.cb_spi = QCheckBox("SPI Flash Test")
        self.cb_i2c = QCheckBox("I2C EEPROM Test")

        btn_run = QPushButton("Run Selected Tests")
        btn_run.clicked.connect(self.run_tests)

        tlay.addWidget(self.cb_spi)
        tlay.addWidget(self.cb_i2c)
        tlay.addStretch()
        tlay.addWidget(btn_run)

        top_lay.addWidget(test_box)
        top_lay.addStretch()

        # ================= BOTTOM: PC LOG =================
        bottom = QWidget()
        bottom_lay = QVBoxLayout(bottom)

        self.pc_log = self.create_pc_log_box("PC Test Log")
        bottom_lay.addWidget(self.pc_log[0])

        # ================= SPLIT =================
        main_splitter.addWidget(top)
        main_splitter.addWidget(bottom)
        main_splitter.setSizes([300, 700])
        return main_splitter
    
    def create_pc_log_box(self, title):
        box = QGroupBox(title)
        lay = QVBoxLayout(box)

        text = QTextEdit()
        text.setReadOnly(True)
        text.setStyleSheet(
            "background: white;"
            "font-family:Consolas;"
            "font-size:8pt;"
        )

        btn_clear = QPushButton("Clear")
        btn_clear.clicked.connect(text.clear)

        lay.addWidget(text)
        lay.addWidget(btn_clear)
        return box, text

    def create_uart_control(self, name, uart):
        box = QGroupBox(f"{name} UART")
        lay = QVBoxLayout(box)

        cb_port = QComboBox()
        cb_baud = QComboBox()
        cb_baud.addItems(["9600", "19200", "38400", "57600", "115200"])
        cb_baud.setCurrentText("115200")

        def refresh_ports():
            cb_port.clear()
            cb_port.addItems([p.device for p in serial.tools.list_ports.comports()])

        refresh_ports()

        btn_refresh = QPushButton("Refresh COM")
        btn_connect = QPushButton("Connect")

        def toggle():
            if uart.isRunning():
                uart.close()
                uart.wait()
                btn_connect.setText("Connect")
            else:
                uart.open(cb_port.currentText(), int(cb_baud.currentText()))
                btn_connect.setText("Disconnect")

        btn_refresh.clicked.connect(refresh_ports)
        btn_connect.clicked.connect(toggle)

        lay.addWidget(QLabel("COM Port"))
        lay.addWidget(cb_port)
        lay.addWidget(btn_refresh)
        lay.addWidget(QLabel("Baudrate"))
        lay.addWidget(cb_baud)
        lay.addWidget(btn_connect)

        return box

    # ==================================================
    # CENTER PANEL
    # ==================================================
    def build_center(self):
        tabs = QTabWidget()
        tabs.addTab(self.build_memory_tab(), "Memory")
        tabs.addTab(self.build_logic_tab(), "Logic Analyzer")
        tabs.addTab(self.build_peripheral_tab(), "Peripherals")
        return tabs

    # ================= Memory Tab ====================
    def build_memory_tab(self):
        w = QWidget()

        # ============ MAIN SPLITTER (LEFT | RIGHT) ============
        main_splitter = QSplitter(Qt.Horizontal)

        # ================= LEFT: MEMORY TABLES =================
        left_splitter = QSplitter(Qt.Vertical)

        self.spi_table = self.create_mem_table("SPI Flash")
        self.i2c_table = self.create_mem_table("I2C EEPROM")

        left_splitter.addWidget(self.spi_table[0])
        left_splitter.addWidget(self.i2c_table[0])
        left_splitter.setSizes([500, 500])

        # ================= RIGHT: LOGS =================
        right = QWidget()
        right_lay = QVBoxLayout(right)

        self.dut_log = self.create_log_box("DUT Log", self.uart_dut)
        self.hil_log = self.create_log_box("HIL Log", self.uart_hil)

        right_lay.addWidget(self.dut_log[0])
        right_lay.addWidget(self.hil_log[0])

        # ================= ASSEMBLE =================
        main_splitter.addWidget(left_splitter)
        main_splitter.addWidget(right)
        main_splitter.setSizes([900, 650])

        layout = QVBoxLayout(w)
        layout.addWidget(main_splitter)

        return w

    # ================= Logic Tab =====================
    def build_logic_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lbl = QLabel("Logic Analyzer / Oscilloscope (Coming soon)")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("font-size:18px;color:gray;")
        lay.addWidget(lbl)
        return w

    # ================= Peripheral Tab ================
    def build_peripheral_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lbl = QLabel("Peripherals tab (Coming soon)")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("font-size:18px;color:gray;")
        lay.addWidget(lbl)
        return w

    def create_mem_table(self, title):
        box = QGroupBox(title)
        lay = QVBoxLayout(box)

        table = QTableWidget(64, 16)
        table.setHorizontalHeaderLabels([f"{i:X}" for i in range(16)])
        table.setVerticalHeaderLabels([f"{i*16:04X}" for i in range(64)])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        lay.addWidget(table)
        return box, table

    # ==================================================
    # RIGHT PANEL (LOG + COMMAND)
    # ==================================================
    def build_right(self):
        w = QWidget()
        lay = QVBoxLayout(w)

        self.dut_log = self.create_log_box("DUT UART", self.uart_dut)
        self.hil_log = self.create_log_box("HIL UART", self.uart_hil)

        lay.addWidget(self.dut_log[0])
        lay.addWidget(self.hil_log[0])
        return w

    def create_log_box(self, title, uart):
        box = QGroupBox(title)
        lay = QVBoxLayout(box)

        btn_clear = QPushButton("Clear")
        text = QTextEdit()
        text.setReadOnly(True)
        text.setStyleSheet("background:white;font-family:Consolas;font-size:8pt;")

        bottom = QHBoxLayout()

        input_line = QLineEdit()
        input_line.setPlaceholderText("Enter command and press Enter")

        btn_clear = QPushButton("Clear")
        btn_clear.setFixedWidth(70)

        btn_clear.clicked.connect(text.clear)
        input_line.returnPressed.connect(
            lambda: (uart.send(input_line.text()), input_line.clear())
        )

        bottom.addWidget(input_line)
        bottom.addWidget(btn_clear)

        lay.addWidget(text)
        lay.addLayout(bottom)

        return box, text

    # ==================================================
    # SLOTS
    # ==================================================
    def append_dut_log(self, text):
        self.dut_log[1].append(text)
        self.dut_log[1].moveCursor(self.dut_log[1].textCursor().End)

    def append_hil_log(self, text):
        self.hil_log[1].append(text)
        self.hil_log[1].moveCursor(self.hil_log[1].textCursor().End)

    def pc_log_append(self, text, newline=True):
        cursor = self.pc_log[1].textCursor()
        cursor.movePosition(cursor.End)

        if newline:
            cursor.insertText(text + "\n")
        else:
            cursor.insertText(text)

        self.pc_log[1].setTextCursor(cursor)

    def update_spi(self, addr, val):
        if 0 <= addr < 1024:
            r, c = divmod(addr, 16)
            self.spi_table[1].setItem(r, c, QTableWidgetItem(f"{val:02X}"))

    def update_i2c(self, addr, val):
        if 0 <= addr < 1024:
            r, c = divmod(addr, 16)
            self.i2c_table[1].setItem(r, c, QTableWidgetItem(f"{val:02X}"))

    def highlight_spi_error(self, addr):
        """Highlight SPI table cell with error in red"""
        if 0 <= addr < 1024:
            r, c = divmod(addr, 16)
            item = self.spi_table[1].item(r, c)
            if item:
                item.setBackground(QBrush(QColor(255, 0, 0, 200)))  # Red with alpha

    def closeEvent(self, e):
        self.uart_dut.close()
        self.uart_hil.close()
        self.uart_dut.wait()
        self.uart_hil.wait()
        e.accept()

    # ==================================================
    # CLEAR TABLE
    # ==================================================
    def clear_spi_table(self):
        table = self.spi_table[1]
        table.clearContents()

    def clear_i2c_table(self):
        table = self.i2c_table[1]
        table.clearContents()

    # ==================================================
    # TEST
    # ==================================================
    def run_tests(self):
        self.test_queue = []
        self.is_running_tests = True  # Set flag để indicate đang chạy tests

        if self.cb_spi.isChecked():
            self.test_queue.append(self.spi_flash_test_id)
            self.test_queue.append(self.spi_flash_test_prepare_mem)
            self.test_queue.append(self.spi_flash_test_erase)
            self.test_queue.append(self.spi_flash_test_write)
            # self.test_queue.append(self.spi_flash_test_read)

        if self.cb_i2c.isChecked():
            self.test_queue.append(self.run_i2c_eeprom_test)

        if not self.test_queue:
            self.pc_log_append("No test selected")
            self.is_running_tests = False
            return
        self.run_next_test()

    def run_next_test(self):
        if not self.test_queue:
            self.pc_log_append("=== ALL TESTS DONE ===")
            self.is_running_tests = False  # Reset flag khi tests kết thúc
            return

        self.current_test = self.test_queue.pop(0)
        self.current_test()

    def run_next_test_delayed(self, delay_ms=5000):
        """Schedule next test after delay"""
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(delay_ms, self.run_next_test)

    def spi_flash_test_id(self):
        self.pc_log_append("=== SPI Flash Test ===")
        self.pc_log_append("[DUT] Read ID -> ", newline=False)
        self.uart_dut.send("w25q_ID")

    def spi_flash_test_write(self):
        # self.pc_log_append("=== SPI Flash Test: Write & Verify ===")
        self.pc_log_append("[DUT] Write Test -> ", newline=False)
        self.uart_dut.send("w25q_write 1024")
        # After write complete, send read command
        self.pc_log_append("[DUT] Read Test -> ", newline=False)
        self.uart_dut.send("w25q_read 1024")

    def spi_flash_test_prepare_mem(self):
        # self.pc_log_append("=== SPI Flash Test: Prepare Memory ===")
        self.pc_log_append("[HIL] Prepare Memory -> ", newline=False)
        # Prepare test data in DUT parser before sending command
        self.uart_dut.spi_parser.set_prepare_mem_size(256)
        self.uart_hil.send("w25q_prepare_mem 256")
        # Wait a bit then read from DUT
        time.sleep(0.5)
        self.pc_log_append("[DUT] Read & Verify -> ", newline=False)
        self.uart_dut.send("w25q_read 256")

    def spi_flash_test_erase(self):
        self.pc_log_append("[DUT] Erase Chip -> ", newline=False)
        # Prepare test data: all 0xFF (erased state)
        self.uart_dut.spi_parser.set_erase_test_data()
        self.uart_dut.send("w25q_erasechip")
        # Wait for erase to complete
        time.sleep(0.5)
        self.pc_log_append("[DUT] Read & Verify -> ", newline=False)
        self.uart_dut.send("w25q_read 1024")

    def run_i2c_eeprom_test(self):
        self.pc_log_append("=== I2C EEPROM TEST START ===")
        self.i2c_devices = [0x50, 0x51]
        self.i2c_dev_index = 0
        self.i2c_step = 0
        self.run_i2c_step()

    def run_i2c_step(self):
        if self.i2c_dev_index >= len(self.i2c_devices):
            self.pc_log_append("=== I2C EEPROM TEST DONE ===")
            self.run_next_test()
            return

        dev = self.i2c_devices[self.i2c_dev_index]

        if self.i2c_step == 0:
            self.pc_log_append(f"[HIL] Init EEPROM 0x{dev:02X}")
            self.uart_hil.send(f"eeprom_init 0x{dev:02X} 1024 256")
            QTimer.singleShot(2000, self.run_i2c_step)

        elif self.i2c_step == 1:
            self.pc_log_append(f"[HIL] Active EEPROM 0x{dev:02X}")
            self.uart_hil.send(f"i2c_dev_active 0x{dev:02X}")
            QTimer.singleShot(2000, self.run_i2c_step)

        elif self.i2c_step == 2:
            self.pc_log_append(f"[DUT] Init EEPROM 0x{dev:02X}")
            self.uart_dut.send(f"eeprom_init 0x{dev:02X} 1024 256")
            QTimer.singleShot(2000, self.run_i2c_step)

        elif self.i2c_step == 3:
            self.pc_log_append(f"[DUT] Fill EEPROM 0x{dev:02X}")
            self.uart_dut.send(f"eeprom_fill 0 256")
            QTimer.singleShot(2000, self.run_i2c_step)

        elif self.i2c_step == 4:
            self.pc_log_append(f"[DUT] Read EEPROM 0x{dev:02X}")
            self.uart_dut.send(f"eeprom_read 0 256")

        elif self.i2c_step == 5:
            self.pc_log_append(f"[HIL] Deinit EEPROM 0x{dev:02X}")
            self.uart_hil.send(f"eeprom_deinit 0x{dev:02X}")
            self.i2c_dev_index += 1
            self.i2c_step = -1
            QTimer.singleShot(2000, self.run_i2c_step)

        self.i2c_step += 1


    def on_test_completed(self, test_type):
        if not self.is_running_tests:
            return

        if test_type == "i2c":
            parser = self.uart_dut.i2c_parser

            if not parser.buffer:
                self.pc_log_append("FAIL (no data)")
            elif len(parser.buffer) != parser.expected:
                self.pc_log_append("FAIL (size mismatch)")
            else:
                self.pc_log_append("PASS")

            parser.reset()
            self.run_i2c_step()
            return

        # ===== SPI =====
        # Reset SPI parser
        self.uart_dut.spi_parser.reset()
        
        if (
            hasattr(self, 'current_test')
            and self.current_test
            and self.current_test.__name__ in ['spi_flash_test_prepare_mem', 'spi_flash_test_erase']
        ):
            # self.pc_log_append("Wait 5s before next test...")
            self.run_next_test_delayed(5000)
        else:
            self.run_next_test()


# ==================================================
# MAIN
# ==================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Global fixed font sizes for UI labels, buttons, groupboxes, etc.
    app.setStyleSheet("""
    QLabel, QPushButton, QGroupBox, QCheckBox, QComboBox, QTabWidget, QLineEdit {
        font-size: 10pt;
    }
    QTableWidget, QHeaderView::section {
        font-size: 9pt;
    }
    QTextEdit {
        font-family: Consolas;
        font-size: 8pt;
    }
    """)

    win = MainWindow()
    win.showMaximized()
    sys.exit(app.exec_())
