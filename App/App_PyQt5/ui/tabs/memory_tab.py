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

        # ================= MEMORY TABLES =================
        splitter = QSplitter(Qt.Vertical)
        self.spi_table = self.create_mem_table("SPI Flash")
        self.i2c_table = self.create_mem_table("I2C EEPROM")

        splitter.addWidget(self.spi_table[0])
        splitter.addWidget(self.i2c_table[0])
        splitter.setSizes([500, 500])

        layout = QVBoxLayout(self)
        layout.addWidget(splitter)

    def create_mem_table(self, title):
        box = QGroupBox(title)
        lay = QVBoxLayout(box)
        table = QTableWidget(64, 16)
        table.setHorizontalHeaderLabels([f"{i:X}" for i in range(16)])
        table.setVerticalHeaderLabels([f"{i*16:04X}" for i in range(64)])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        lay.addWidget(table)
        return box, table

    # ================= UI UPDATE SLOTS =================
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
