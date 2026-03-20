import serial
import time

class CLI:
    """
    Generic CLI communication class.

    Responsibility:
        - open serial
        - send command
        - wait response
    """

    def __init__(self):
        self.ser = None

    # -------------------------
    # CONNECTION
    # -------------------------

    def connect(self, port, baud):

        self.ser = serial.Serial(port, baud, timeout=0.1)

        # wait STM32 reboot
        time.sleep(0.5)

        # clear boot garbage
        self.ser.reset_input_buffer()

        # wake CLI
        self.ser.write(b"\n")

    def disconnect(self):
        """Close serial"""
        if self.ser:
            self.ser.close()

    # -------------------------
    # COMMAND
    # -------------------------

    def execute(self, cmd):

        if not self.ser:
            raise Exception("Serial not connected")

        self.ser.reset_input_buffer()

        self.ser.write((cmd + "\r\n").encode())

        response = ""
        timeout = time.time() + 3

        while time.time() < timeout:

            if self.ser.in_waiting:
                data = self.ser.read(self.ser.in_waiting).decode(errors="ignore")
                response += data

            time.sleep(0.05)

        return response.strip()
    
    # -------------------------
    # LOGIC ANALYZER / BINARY
    # -------------------------

    def setup_logic_analyzer(self, rate: int, samples: int):
        if not self.ser:
            raise Exception("Serial not connected")

        # 1. Reset state
        self.ser.write(b"*")
        time.sleep(0.05)

        # 2. Cấu hình các kênh Analog / Digital
        channels = [b"A10\n", b"D10\n", b"D11\n", b"D12\n", b"D13\n"]
        for ch in channels:
            self.ser.write(ch)
            time.sleep(0.01)

        # 3. Cấu hình Rate và Sample count
        self.ser.write(f"R{rate}\n".encode('ascii'))
        time.sleep(0.01)
        self.ser.write(f"L{samples}\n".encode('ascii'))
        time.sleep(0.01)
