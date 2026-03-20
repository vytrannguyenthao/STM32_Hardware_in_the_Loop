import os
from pathlib import Path
from datetime import datetime
from robot.api.deco import library, keyword
from robot.api import logger
from cli_lib import CLI
import re
from robot.libraries.BuiltIn import BuiltIn

@library(scope="GLOBAL")
class HILLibrary:
    """
    Robot Library for HIL board
    """

    def __init__(self):
        self.cli = CLI()
        # Tạo thư mục log và file log
        self.log_dir = Path("hil_logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"hil_serial_{timestamp}.log"

    # ------------------
    # Internal CLI
    # ------------------
    def _hil_cmd(self, cmd, expect_response=True):
        resp = self.cli.execute(cmd)
        resp = resp.replace("\r", "").strip()
        resp = resp.replace("HIL:~", "").strip() # Xóa prefix "HIL:~" nếu có

        logger.info(f"{resp}")

        # Mở file ở chế độ "a" (append) để nối thêm dữ liệu vào cuối file
        with open(self.log_file, "a", encoding="utf-8") as f:
            time_now = datetime.now().strftime("%H:%M:%S.%f")[:-3] # Lấy giờ phút giây . mili giây
            # Ghi cả lệnh đã gửi và dữ liệu nhận được để dễ debug
            f.write(f"[{time_now}] {resp}\n")
            f.write("-" * 50 + "\n")

        if expect_response and not resp.strip():
            raise AssertionError(f"No response for command: {cmd}")

        return resp

    # ------------------
    # Connection
    # ------------------
    @keyword("Connect HIL")
    def connect_hil(self, port, baud):
        """Connect to HIL serial"""
        self.cli.connect(port, baud)
        logger.info(f"Connected HIL at {port}, baud {baud}")

    @keyword("Disconnect HIL")
    def disconnect_hil(self):
        """Disconnect HIL"""
        self.cli.disconnect()
        logger.info("HIL disconnected")

    @keyword("HIL Help")
    def hil_help(self):
        """
        Send 'help' command to HIL and print raw response.
        Used to verify connection and communication.
        """

        resp = self._hil_cmd("help")

        return resp
    
    @keyword("Verify HIL Alive")
    def verify_hil_alive(self):

        resp = self._hil_cmd("help")

        if "help" not in resp.lower():
            raise AssertionError("Invalid HIL response")

        return resp
    
    # ------------------
    # Power control
    # ------------------
    @keyword("Power DUT On")
    def power_dut_on(self):
        resp = self._hil_cmd("dut_power 1")
        logger.info(resp)

    # ------------------
    # PWM
    # ------------------
    @keyword("Read HIL Voltage")
    def read_voltage(self):

        resp = self._hil_cmd("adc_read_pwm")

        match = re.search(r"Measured:\s*(\d+)\s*mV", resp)
        if not match:
            raise AssertionError("ADC value not found")

        voltage = int(match.group(1)) / 1000.0
        logger.info(f"Voltage = {voltage} V")

        return voltage
    
    @keyword("Voltage Should Be In Range")
    def voltage_should_be_in_range(self, min_v, max_v):

        voltage = self.read_voltage()

        if not (float(min_v) <= voltage <= float(max_v)):
            raise AssertionError(
                f"Voltage out of range: {voltage}V"
            )
    
    @keyword("Wait Until Voltage Stable")
    def wait_until_voltage_stable(self, min_v, max_v):
        """
        Wait until ADC voltage becomes stable.
        """
        BuiltIn().run_keyword(
            "Wait Until Keyword Succeeds",
            "5s",
            "200ms",
            "Voltage Should Be In Range",
            min_v,
            max_v,
        )

    # ------------------
    # I2C
    # ------------------

    def _validate_i2c_addr(self, addr):

        try:
            value = int(str(addr), 0)
        except ValueError:
            raise AssertionError(f"Invalid I2C address: {addr}")

        if value <= 0 or value >= 0x7F:
            raise AssertionError(
                f"I2C address out of range: {addr}"
            )

        return value

    def _validate_uint(self, name, val):

        try:
            v = int(val)
        except ValueError:
            raise AssertionError(f"{name} must be integer")

        if v <= 0:
            raise AssertionError(f"{name} must > 0")

        return v

    @keyword("HIL Init EEPROM")
    def hil_init_eeprom(self, addr, size, page):

        addr = self._validate_i2c_addr(addr)
        size = self._validate_uint("size", size)
        page = self._validate_uint("page", page)

        if size % page != 0:
            raise AssertionError(
                "EEPROM size must be multiple of page size"
            )

        cmd = f"eeprom_init 0x{addr:02X} {size} {page}"

        self._hil_cmd(cmd, expect_response=False)
    
    @keyword("HIL Deinit EEPROM")
    def hil_deinit_eeprom(self, addr):
        addr = self._validate_i2c_addr(addr)
        self._hil_cmd(f"eeprom_deinit 0x{addr:02X}", expect_response=False)

    @keyword("HIL Find EEPROM")
    def hil_find_eeprom(self):

        resp = self._hil_cmd("eeprom_find")

        if "eeprom" not in resp.lower():
            raise AssertionError("EEPROM not detected")

        logger.info(resp)
        return resp
    
    @keyword("HIL Activate I2C Device")
    def hil_activate_i2c_device(self, addr):
        addr = self._validate_i2c_addr(addr)
        cmd = f"i2c_dev_active 0x{addr:02X}"
        resp = self._hil_cmd(cmd)

        if "not initialized" in resp.lower():
            raise AssertionError(resp)
