from robot.api.deco import library, keyword
from robot.api import logger
from cli_lib import CLI
import re
import time

@library(scope="GLOBAL")
class DUTLibrary:
    """
    Robot Library for DUT firmware
    """

    def __init__(self):
        self.cli = CLI()

    # ------------------
    # Internal CLI
    # ------------------
    def _dut_cmd(self, cmd, expect_response=True):
        resp = self.cli.execute(cmd)
        resp = resp.replace("\r", "").strip()
        resp = resp.replace("DUT:~", "").strip() # Xóa prefix "DUT:~" nếu có

        logger.info(f"{resp}")

        if expect_response and not resp.strip():
            raise AssertionError(f"No response for command: {cmd}")

        return resp

    # ------------------
    # Connection
    # ------------------
    @keyword("Connect DUT")
    def connect_dut(self, port, baud):
        self.cli.connect(port, baud)

    @keyword("Disconnect DUT")
    def disconnect_dut(self):
        self.cli.disconnect()

    @keyword("DUT Help")
    def dut_help(self):

        resp = self._dut_cmd("help")

        return resp

    @keyword("Verify DUT Alive")
    def verify_dut_alive(self):

        resp = self._dut_cmd("help")

        if "help" not in resp.lower():
            raise AssertionError("Invalid DUT response")

        return resp

    # ------------------
    # PWM
    # ------------------
    @keyword("Start DUT PWM")
    def start_pwm(self, ch):
        self._dut_cmd(f"pwm_start {ch}", expect_response=False)

    @keyword("Stop DUT PWM")
    def stop_pwm(self, ch):
        self._dut_cmd(f"pwm_stop {ch}", expect_response=False)

    @keyword("Set DUT duty cycle")
    def set_pwm_duty(self, ch, duty):
        self._dut_cmd(f"pwm_set_duty_cycle {ch} {duty}", expect_response=False)

    @keyword("Set DUT PWM freq")
    def set_pwm_freq(self, freq):
        self._dut_cmd(f"pwm_set_freq {freq}", expect_response=False)

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


    # ------------------
    # EEPROM 
    # ------------------

    @keyword("DUT Init EEPROM")
    def dut_init_eeprom(self, addr, size, page):

        addr = self._validate_i2c_addr(addr)
        size = self._validate_uint("size", size)
        page = self._validate_uint("page", page)

        if size % page != 0:
            raise AssertionError(
                "EEPROM size must be multiple of page size"
            )

        cmd = f"eeprom_init 0x{addr:02X} {size} {page}"

        self._dut_cmd(cmd, expect_response=False)

    @keyword("I2C Device Should Exist")
    def i2c_device_should_exist(self, resp, addr):

        addr_val = int(str(addr), 0)

        hex_addr = f"0x{addr_val:02X}".lower()

        if hex_addr not in resp.lower():
            raise AssertionError(
                f"I2C device {hex_addr} not detected"
            )

    @keyword("DUT EEPROM Fill")
    def dut_eeprom_fill(self, addr, length):

        addr = self._validate_i2c_addr(addr)
        length = self._validate_uint("length", length)

        self._dut_cmd(
            f"eeprom_fill 0x{addr:02X} {length}",
            expect_response=False
        )

    @keyword("DUT EEPROM Write")
    def dut_eeprom_write(self, addr, length):

        addr = self._validate_i2c_addr(addr)
        length = self._validate_uint("length", length)

        self._dut_cmd(
            f"eeprom_write 0x{addr:02X} {length}",
            expect_response=False
        )

    @keyword("DUT EEPROM Read")
    def dut_eeprom_read(self, addr, length):

        addr = self._validate_i2c_addr(addr)
        length = self._validate_uint("length", length)

        resp = self._dut_cmd(
            f"eeprom_read 0x{addr:02X} {length}"
        )

        # ---- extract ONLY data section ----
        match = re.search(
            r"\)\:\s*\n(.*)",
            resp,
            re.S
        )

        if not match:
            raise AssertionError("EEPROM data block not found")

        data_block = match.group(1)

        # now parse bytes
        data = re.findall(r"\b[0-9A-Fa-f]{2}\b", data_block)

        if len(data) != length:
            raise AssertionError(
                f"Expected {length} bytes, got {len(data)}"
            )

        return data

    @keyword("DUT Write And Verify EEPROM")
    def dut_write_and_verify(self, addr, length):

        logger.console("\nWriting EEPROM...")
        self.dut_eeprom_fill(addr, length)

        logger.console("\nReading EEPROM...")
        data = self.dut_eeprom_read(addr, length)

        logger.info("\nEEPROM data length OK")

        return data
    
    @keyword("Data Should Increment")
    def eeprom_data_should_increment(self, data):

        for i, byte in enumerate(data):
            if int(byte, 16) != (i & 0xFF):
                raise AssertionError(
                    f"Mismatch at {i}: {byte}"
                )
            
    @keyword("Measure EEPROM Write Time")
    def measure_write_time(self, addr, length):

        addr = self._validate_i2c_addr(addr)
        length = self._validate_uint("length", length)

        start = time.perf_counter()

        self._dut_cmd(f"eeprom_write 0x{addr:02X} {length}", False)

        end = time.perf_counter()

        duration = end - start

        logger.info(f"\nEEPROM write time = {duration:.4f}s")

        return duration
    
    @keyword("Write Time Should Be Less Than")
    def write_time_should_be_less_than(self, measured, limit):

        if float(measured) > float(limit):
            raise AssertionError(
                f"Write too slow: {measured}s"
            )

    # ------------------
    # SPI FLASH (W25Q)
    # ------------------
    @keyword("Read SPI Flash ID")
    def read_spi_flash_id(self):
        resp = self._dut_cmd("w25q_ID")
        if "EF4018" in resp:
            return True
        else:
            raise AssertionError(f"Wrong Flash ID! Expected EF4018, got: {resp}")

    @keyword("Read SPI Flash Data")
    def read_spi_flash_data(self, length):
        length = self._validate_uint("length", length)
        resp = self._dut_cmd(f"w25q_read {length}")

        match = re.search(
            r"W25Q\:\s*\n(.*)",
            resp,
            re.S
        )

        if not match:
            raise AssertionError("SPI Flash data block not found in response")

        data_block = match.group(1)

        data = re.findall(r"\b[0-9A-Fa-f]{2}\b", data_block)

        if len(data) != length:
            raise AssertionError(
                f"SPI Flash Read Error: Expected {length} bytes, got {len(data)}"
            )
        return data

    @keyword("Write SPI Flash Data")
    def write_spi_flash_data(self, length):
        length = self._validate_uint("length", length)
        self._dut_cmd(f"w25q_write {length}")

    @keyword("Erase SPI Flash Data")
    def erase_spi_flash_data(self):
        rsp = self._dut_cmd(f"w25q_erasechip")
        if "OK" not in rsp:
            raise AssertionError(f"Failed to erase SPI Flash")

    @keyword("Is SPI Flash Data Erased")
    def is_spi_flash_data_erased(self, data):
        for index, byte in enumerate(data):
            # Ép kiểu về chữ HOA để so sánh cho an toàn (lỡ firmware trả về 'ff')
            if byte.upper() != "FF":
                raise AssertionError(
                    f"Flash is not blank! Found byte '{byte}' at index {index}."
                )
        return True

    # ------------------
    # Generate waveform
    # ------------------
    @keyword("DUT Generate Sine Wave")
    def dut_generate_sine_wave(self, frequency):
        frequency = self._validate_uint("frequency", frequency)
        resp = self._dut_cmd(f"set_freq {frequency}")
        if "Invalid" in resp:
            raise AssertionError(f"Invalid frequency: {frequency}")
        resp = self._dut_cmd("sine_wave 1")
        if "Start" not in resp:
            raise AssertionError(f"DUT failed to generate sine wave")
        return True

    @keyword("DUT Stop Sine Wave")
    def dut_stop_sine_wave(self):
        resp = self._dut_cmd("sine_wave 0")
        if "Stop" not in resp:
            raise AssertionError(f"DUT failed to stop sine wave")
        return True

    @keyword("DUT Generate Triangle Wave")
    def dut_generate_triangle_wave(self, frequency):
        frequency = self._validate_uint("frequency", frequency)
        resp = self._dut_cmd(f"set_freq {frequency}")
        if "Invalid" in resp:
            raise AssertionError(f"Invalid frequency: {frequency}")

        resp = self._dut_cmd("triangle_wave 1")
        if "Start" not in resp:
            raise AssertionError(f"DUT failed to generate triangle wave")
        return True

    @keyword("DUT Stop Triangle Wave")
    def dut_stop_triangle_wave(self):
        resp = self._dut_cmd("triangle_wave 0")
        if "Stop" not in resp:
            raise AssertionError(f"DUT failed to stop triangle wave")
        return True

    # ------------------
    # Analog
    # ------------------
    @keyword("DUT Read ADC Voltage")
    def dut_read_adc_voltage(self, expected_volt=None):

        resp = self._dut_cmd("adc_read")

        match = re.search(r"Voltage:\s*(\d+)\s*mV", resp)
        if not match:
            raise AssertionError("ADC value not found")

        voltage_mv = int(match.group(1))
        if expected_volt is not None:
            # Ép kiểu chuỗi truyền vào thành số thực, sau đó nhân 1000 để đổi ra mV
            expected_mv = float(expected_volt) * 1000.0
            # Tính khoảng sai số 5%
            margin = expected_mv * 0.05
            lower_bound = expected_mv - margin
            upper_bound = expected_mv + margin

            # So sánh trực tiếp giá trị mV thu được với khoảng cho phép
            if voltage_mv < lower_bound or voltage_mv > upper_bound:
                raise AssertionError(
                    f"FAIL: Voltage out of bounds! "
                    f"Got {voltage_mv} mV, Expected {expected_mv} mV \u00B15% "
                    f"(Range: {lower_bound:.0f} mV to {upper_bound:.0f} mV)"
                )
            logger.info(f"Got {voltage_mv} mV, (Range: [{lower_bound:.0f} -> {upper_bound:.0f}] mV)")
        return True
