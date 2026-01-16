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
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QThread, pyqtSignal

# ==================================================
# SPI PARSER
# ==================================================
class SPIParser:
    def __init__(self, emit_cb, log_cb, clear_cb):
        self.emit_cb = emit_cb
        self.log_cb = log_cb
        self.clear_cb = clear_cb
        self.active = False
        self.expected = 0
        self.buffer = []

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

        # info
        if self.active and line.startswith("Read"):
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

                self.log_cb("[SPI] Read completed")
                self.active = False

            return True

        return False

# ==================================================
# I2C EEPROM PARSER
# ==================================================
class I2CParser:
    def __init__(self, emit_cb, log_cb, clear_cb):
        self.emit_cb = emit_cb
        self.log_cb = log_cb
        self.clear_cb = clear_cb
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
        # 2. info header
        # ==========================
        if self.active and line.startswith("EEPROM read"):
            return True

        # ==========================
        # 3. data
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

            return True

        return False

# ==================================================
# UART THREAD
# ==================================================
class UARTThread(QThread):
    log_signal = pyqtSignal(str)
    spi_data = pyqtSignal(int, int)
    i2c_data = pyqtSignal(int, int)
    spi_clear = pyqtSignal()
    i2c_clear = pyqtSignal()

    def __init__(self, name):
        super().__init__()
        self.name = name
        self.running = False
        self.ser = None
        self.spi_parser = SPIParser(self.spi_data.emit, self.log_signal.emit, self.spi_clear.emit)
        self.i2c_parser = I2CParser(self.i2c_data.emit, self.log_signal.emit, self.i2c_clear.emit)

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

        self.uart_dut.log_signal.connect(self.append_dut_log)
        self.uart_hil.log_signal.connect(self.append_hil_log)

        self.uart_dut.spi_data.connect(self.update_spi)
        self.uart_dut.spi_clear.connect(self.clear_spi_table)

        self.uart_dut.i2c_data.connect(self.update_i2c)
        self.uart_dut.i2c_clear.connect(self.clear_i2c_table)

        splitter.addWidget(self.build_left())
        splitter.addWidget(self.build_center())

        splitter.setSizes([350, 1450])

    # ==================================================
    # LEFT PANEL
    # ==================================================
    def build_left(self):
        w = QWidget()
        lay = QVBoxLayout(w)

        lay.addWidget(self.create_uart_control("DUT", self.uart_dut))
        lay.addWidget(self.create_uart_control("HIL", self.uart_hil))

        test_box = QGroupBox("Test Cases")
        tlay = QVBoxLayout(test_box)
        tlay.addWidget(QCheckBox("SPI Flash Test"))
        tlay.addWidget(QCheckBox("I2C EEPROM Test"))
        tlay.addStretch()
        tlay.addWidget(QPushButton("Run Selected Tests"))

        lay.addWidget(test_box)
        lay.addStretch()
        return w

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
        main_splitter.setSizes([1100, 450])

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
        text.setStyleSheet("background:white;font-family:Consolas;font-size:9pt;")

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

    def update_spi(self, addr, val):
        if 0 <= addr < 1024:
            r, c = divmod(addr, 16)
            self.spi_table[1].setItem(r, c, QTableWidgetItem(f"{val:02X}"))

    def update_i2c(self, addr, val):
        if 0 <= addr < 1024:
            r, c = divmod(addr, 16)
            self.i2c_table[1].setItem(r, c, QTableWidgetItem(f"{val:02X}"))

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
# MAIN
# ==================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.showMaximized()
    sys.exit(app.exec_())
