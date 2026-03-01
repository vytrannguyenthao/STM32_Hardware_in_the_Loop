# File: core/uart_thread.py

import time
import serial
from PyQt5.QtCore import QThread, pyqtSignal
from core.parsers import SPIParser, I2CParser, UARTParser

class UARTThread(QThread):
    log_signal = pyqtSignal(str)
    spi_data = pyqtSignal(int, int)
    i2c_data = pyqtSignal(int, int)
    uart_data = pyqtSignal(int, int)
    spi_clear = pyqtSignal()
    i2c_clear = pyqtSignal()
    uart_clear = pyqtSignal()
    pc_log_signal = pyqtSignal(str)
    test_completed = pyqtSignal(str)

    def __init__(self, name):
        super().__init__()
        self.name = name
        self.running = False
        self.ser = None
        self.spi_parser = SPIParser(self.spi_data.emit, self.log_signal.emit, self.spi_clear.emit, self.pc_log_signal.emit, self.test_completed.emit)
        self.i2c_parser = I2CParser(self.i2c_data.emit, self.log_signal.emit, self.i2c_clear.emit, self.test_completed.emit)
        self.uart_parser = UARTParser(
            byte_cb=self.handle_uart_byte,
            log_cb=self.log_signal.emit
        )
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
                    if self.name == "LOGIC":
                        # Với cổng LOGIC: Đọc kiểu nhị phân (Binary) và xả đi càng nhanh càng tốt
                        # Không dùng readline() vì data mã hóa RLE không có \n, sẽ làm treo app
                        raw_data = self.ser.read(self.ser.in_waiting)
                        # Tạm thời chưa cần in ra hay decode, cứ đọc để xả buffer cho Pico khỏi tràn
                        # print(f"Received {len(raw_data)} bytes") 
                    else:
                        # Với DUT và HIL thì giữ nguyên đọc từng dòng Text
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

    def handle_line(self, line):
        self.log_signal.emit(f"{line}")
        line = line.strip()

        if self.spi_parser.feed(line): return
        if self.i2c_parser.feed(line): return
        if self.uart_parser.feed(line): return

    def handle_uart_byte(self, byte):
        self.pc_log_signal.emit(f"UART_BYTE:{byte}")
