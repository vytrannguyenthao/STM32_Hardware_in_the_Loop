# File: ui/tabs/memory_tab.py
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
                             QSplitter, QTableWidget, QTableWidgetItem, QHeaderView, 
                             QPushButton, QTextEdit, QLineEdit)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QBrush, QColor

class MemoryTab(QWidget):
    def __init__(self, uart_dut, uart_hil):
        super().__init__()
        self.uart_dut = uart_dut
        self.uart_hil = uart_hil

        # ============ MAIN SPLITTER ============
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

        main_splitter.addWidget(left_splitter)
        main_splitter.addWidget(right)
        main_splitter.setSizes([900, 650])

        layout = QVBoxLayout(self)
        layout.addWidget(main_splitter)

    def create_mem_table(self, title):
        box = QGroupBox(title)
        lay = QVBoxLayout(box)
        table = QTableWidget(64, 16)
        table.setHorizontalHeaderLabels([f"{i:X}" for i in range(16)])
        table.setVerticalHeaderLabels([f"{i*16:04X}" for i in range(64)])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        lay.addWidget(table)
        return box, table

    def create_log_box(self, title, uart):
        box = QGroupBox(title)
        lay = QVBoxLayout(box)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setStyleSheet("background:white;font-family:Consolas;font-size:8pt;")

        bottom = QHBoxLayout()
        input_line = QLineEdit()
        input_line.setPlaceholderText("Enter command and press Enter")
        btn_clear = QPushButton("Clear")
        btn_clear.setFixedWidth(70)

        btn_clear.clicked.connect(text.clear)
        input_line.returnPressed.connect(lambda: (uart.send(input_line.text()), input_line.clear()))

        bottom.addWidget(input_line)
        bottom.addWidget(btn_clear)

        lay.addWidget(text)
        lay.addLayout(bottom)
        return box, text

    # ================= UI UPDATE SLOTS =================
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

    def highlight_spi_error(self, addr):
        if 0 <= addr < 1024:
            r, c = divmod(addr, 16)
            item = self.spi_table[1].item(r, c)
            if item:
                item.setBackground(QBrush(QColor(255, 0, 0, 200))) 

    def clear_spi_table(self):
        self.spi_table[1].clearContents()

    def clear_i2c_table(self):
        self.i2c_table[1].clearContents()
