# File: ui/main_window.py
import time
import serial.tools.list_ports
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QGroupBox, 
                             QPushButton, QTextEdit, QSplitter, QLabel, 
                             QComboBox, QCheckBox, QTabWidget)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon

from core.uart_thread import UARTThread
from ui.tabs.memory_tab import MemoryTab
from ui.tabs.logic_tab import LogicTab
from ui.tabs.peripheral_tab import PeripheralTab

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HIL Simulation UI")
        # Ensure path is correct relative to where main.py runs
        self.setWindowIcon(QIcon("./App/App_PyQt5/img/logoBK.png"))

        self.uart_dut = UARTThread("DUT")
        self.uart_hil = UARTThread("HIL")
        self.uart_logic = UARTThread("LOGIC")

        self.test_queue = []
        self.current_test = None
        self.is_running_tests = False  

        # Init UI elements
        splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(splitter)

        # Setup Tabs (Need to be created first so we can connect signals to them)
        self.memory_tab = MemoryTab(self.uart_dut, self.uart_hil)
        self.logic_tab = LogicTab(self.uart_logic)
        self.peripheral_tab = PeripheralTab()

        # Connect Signals -> Tabs
        self.uart_dut.log_signal.connect(self.memory_tab.append_dut_log)
        self.uart_hil.log_signal.connect(self.memory_tab.append_hil_log)
        self.uart_logic.data_signal.connect(self.logic_tab.process_raw_data)
        self.uart_dut.spi_data.connect(self.memory_tab.update_spi)
        self.uart_dut.spi_clear.connect(self.memory_tab.clear_spi_table)
        self.uart_dut.i2c_data.connect(self.memory_tab.update_i2c)
        self.uart_dut.i2c_clear.connect(self.memory_tab.clear_i2c_table)
        self.uart_dut.spi_parser.highlight_error_cb = self.memory_tab.highlight_spi_error

        # Connect Signals -> Main Window (PC Logs & Test flows)
        self.uart_dut.pc_log_signal.connect(self.pc_log_append)
        self.uart_dut.test_completed.connect(self.on_test_completed)

        # Connect UART byte signals to handlers
        self.uart_dut.pc_log_signal.connect(self.handle_dut_uart_byte)
        self.uart_hil.pc_log_signal.connect(self.handle_hil_uart_byte)

        # Build Main View
        splitter.addWidget(self.build_left())
        splitter.addWidget(self.build_center())
        splitter.setSizes([350, 1450])

    def build_left(self):
        left_tabs = QTabWidget()

        # TAB 1: COM
        tab_com = QWidget()
        lay_com = QVBoxLayout(tab_com)
        lay_com.addWidget(self.create_uart_control("DUT", self.uart_dut))
        lay_com.addWidget(self.create_uart_control("HIL", self.uart_hil))
        lay_com.addWidget(self.create_uart_control("LOGIC", self.uart_logic))
        lay_com.addStretch()  

        # TAB 2: TEST
        tab_test = QWidget()
        lay_test = QVBoxLayout(tab_test)
        test_splitter = QSplitter(Qt.Vertical)

        test_box = QGroupBox("Test Cases")
        tlay = QVBoxLayout(test_box)
        self.cb_spi = QCheckBox("SPI Flash Test")
        self.cb_i2c = QCheckBox("I2C EEPROM Test")
        self.cb_uart = QCheckBox("UART Test")
        btn_run = QPushButton("Run Selected Tests")
        btn_run.clicked.connect(self.run_tests)

        tlay.addWidget(self.cb_spi)
        tlay.addWidget(self.cb_i2c)
        tlay.addWidget(self.cb_uart)
        tlay.addStretch()
        tlay.addWidget(btn_run)

        bottom_widget = QWidget()
        bottom_lay = QVBoxLayout(bottom_widget)
        bottom_lay.setContentsMargins(0, 0, 0, 0) 
        self.pc_log = self.create_pc_log_box("PC Test Log")
        bottom_lay.addWidget(self.pc_log[0])

        test_splitter.addWidget(test_box)
        test_splitter.addWidget(bottom_widget)
        test_splitter.setSizes([200, 800]) 
        lay_test.addWidget(test_splitter)

        left_tabs.addTab(tab_com, "COM")
        left_tabs.addTab(tab_test, "Test")
        return left_tabs

    def build_center(self):
        tabs = QTabWidget()
        tabs.addTab(self.memory_tab, "Memory")
        tabs.addTab(self.logic_tab, "Logic Analyzer")
        tabs.addTab(self.peripheral_tab, "Peripherals")
        return tabs

    def create_pc_log_box(self, title):
        box = QGroupBox(title)
        lay = QVBoxLayout(box)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setStyleSheet("background: white; font-family:Consolas; font-size:8pt;")
        btn_clear = QPushButton("Clear")
        btn_clear.clicked.connect(text.clear)
        lay.addWidget(text)
        lay.addWidget(btn_clear)
        return box, text

    def create_uart_control(self, name, uart):
        box = QGroupBox(f"{name} Serial Port")
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

        # Khi rút cáp, luồng bị lỗi và dừng lại, nó sẽ tự động kích hoạt tín hiệu 'finished'
        uart.finished.connect(lambda: btn_connect.setText("Connect"))

        btn_refresh.clicked.connect(refresh_ports)
        btn_connect.clicked.connect(toggle)

        lay.addWidget(QLabel("COM Port"))
        lay.addWidget(cb_port)
        lay.addWidget(btn_refresh)
        lay.addWidget(QLabel("Baudrate"))
        lay.addWidget(cb_baud)
        lay.addWidget(btn_connect)
        return box

    def pc_log_append(self, text, newline=True):
        cursor = self.pc_log[1].textCursor()
        cursor.movePosition(cursor.End)
        if newline: cursor.insertText(text + "\n")
        else: cursor.insertText(text)
        self.pc_log[1].setTextCursor(cursor)

    def closeEvent(self, e):
        self.uart_dut.close()
        self.uart_hil.close()
        self.uart_logic.close()
        self.uart_dut.wait()
        self.uart_hil.wait()
        self.uart_logic.wait()
        e.accept()

    # ==================== TEST LOGIC ====================
    def run_tests(self):
        self.test_queue = []
        self.is_running_tests = True

        if self.cb_spi.isChecked():
            self.test_queue.extend([
                self.spi_flash_test_id,
                self.spi_flash_test_prepare_mem,
                self.spi_flash_test_erase,
                self.spi_flash_test_write
            ])
        if self.cb_i2c.isChecked():
            self.test_queue.append(self.run_i2c_eeprom_test)

        if self.cb_uart.isChecked():
            self.test_queue.append(self.run_uart_test)

        if not self.test_queue:
            self.pc_log_append("No test selected")
            self.is_running_tests = False
            return
        self.run_next_test()

    def run_next_test(self):
        if not self.test_queue:
            self.pc_log_append("=== ALL TESTS DONE ===")
            self.is_running_tests = False 
            return
        self.current_test = self.test_queue.pop(0)
        self.current_test()

    def run_next_test_delayed(self, delay_ms=5000):
        QTimer.singleShot(delay_ms, self.run_next_test)

    def spi_flash_test_id(self):
        self.pc_log_append("=== SPI Flash Test ===")
        self.pc_log_append("[DUT] Read ID -> ", newline=False)
        self.uart_dut.send("w25q_ID")

    def spi_flash_test_write(self):
        self.pc_log_append("[DUT] Write Test -> ", newline=False)
        self.uart_dut.send("w25q_write 1024")
        self.pc_log_append("[DUT] Read Test -> ", newline=False)
        self.uart_dut.send("w25q_read 1024")

    def spi_flash_test_prepare_mem(self):
        self.pc_log_append("[HIL] Prepare Memory -> ", newline=False)
        self.uart_dut.spi_parser.set_prepare_mem_size(256)
        self.uart_hil.send("w25q_prepare_mem 256")
        time.sleep(0.5)
        self.pc_log_append("[DUT] Read & Verify -> ", newline=False)
        self.uart_dut.send("w25q_read 256")

    def spi_flash_test_erase(self):
        self.pc_log_append("[DUT] Erase Chip -> ", newline=False)
        self.uart_dut.spi_parser.set_erase_test_data()
        self.uart_dut.send("w25q_erasechip")
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

    def run_uart_test(self):
        self.pc_log_append("=== UART TEST START ===")
        self.uart_test_step = 0
        self.hil_buffer = []
        self.dut_buffer = []
        QTimer.singleShot(10, self.run_uart_step)

    def run_uart_step(self):

        # ================= STEP 0: INIT =================
        if self.uart_test_step == 0:
            self.pc_log_append("=== DUT → HIL ===")
            self.hil_buffer.clear()
            self.uart_dut.send("uart_init")
            self.uart_hil.send("uart_init")
            QTimer.singleShot(500, self.run_uart_step)

        # ================= STEP 1: DUT DUMP =================
        elif self.uart_test_step == 1:
            self.uart_dut.send("uart_dump")
            QTimer.singleShot(2000, self.run_uart_step)

        # ================= STEP 2: HIL RX =================
        elif self.uart_test_step == 2:
            self.uart_hil.send("uart_rx")
            QTimer.singleShot(2000, self.run_uart_step)

        # ================= STEP 3: CHECK DUT → HIL =================
        elif self.uart_test_step == 3:
            expected = list(range(256))
            if self.hil_buffer == expected:
                self.pc_log_append("UART TX PASS")
            else:
                self.pc_log_append(f"UART TX FAIL (got {len(self.hil_buffer)})")
            QTimer.singleShot(200, self.run_uart_step)

        # ================= STEP 4: HIL → DUT START =================
        elif self.uart_test_step == 4:
            self.pc_log_append("=== HIL → DUT ===")
            self.dut_buffer.clear()
            self.uart_hil.send("uart_dump")
            QTimer.singleShot(2000, self.run_uart_step)

        # ================= STEP 5: DUT RX =================
        elif self.uart_test_step == 5:
            self.uart_dut.send("uart_rx")
            QTimer.singleShot(2000, self.run_uart_step)

        # ================= STEP 6: CHECK HIL → DUT =================
        elif self.uart_test_step == 6:
            expected = list(range(256))
            if self.dut_buffer == expected:
                self.pc_log_append("UART RX PASS")
            else:
                self.pc_log_append(f"UART RX FAIL (got {len(self.dut_buffer)})")
            QTimer.singleShot(200, self.run_uart_step)

        # ================= DONE =================
        elif self.uart_test_step == 7:
            self.pc_log_append("=== UART TEST DONE ===")
            self.run_next_test()
            return
        
        self.uart_test_step += 1

    def on_test_completed(self, test_type):
        if not self.is_running_tests: return

        if test_type == "uart":
            self.pc_log_append("PASS")
            self.run_next_test()
            return
        
        if test_type == "i2c":
            parser = self.uart_dut.i2c_parser
            if not parser.buffer: self.pc_log_append("FAIL (no data)")
            elif len(parser.buffer) != parser.expected: self.pc_log_append("FAIL (size mismatch)")
            else: self.pc_log_append("PASS")
            parser.reset()
            self.run_i2c_step()
            return

        self.uart_dut.spi_parser.reset()
        if (hasattr(self, 'current_test') and self.current_test and 
            self.current_test.__name__ in ['spi_flash_test_prepare_mem', 'spi_flash_test_erase']):
            self.run_next_test_delayed(5000)
        else:
            self.run_next_test()

    def handle_hil_uart_byte(self, text):
        text = text.strip()

        if text.startswith("UART_BYTE:"):
            try:
                val = int(text.split(":")[1])
                self.hil_buffer.append(val)
            except:
                pass

    def handle_dut_uart_byte(self, text):
        text = text.strip()

        if text.startswith("UART_BYTE:"):
            try:
                val = int(text.split(":")[1])
                self.dut_buffer.append(val)
            except:
                pass
    