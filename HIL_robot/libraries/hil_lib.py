import os
from pathlib import Path
from datetime import datetime
from robot.api.deco import library, keyword
from robot.api import logger
from cli_lib import CLI
import re
from robot.libraries.BuiltIn import BuiltIn
import subprocess
import time

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
        self._hil_cmd("dut_power 1")

    @keyword("Power DUT Off")
    def power_dut_off(self):
        self._hil_cmd("dut_power 0")

    @keyword("Power DUT Cycle")
    def power_dut_cycle(self):
        self.power_dut_off()
        BuiltIn().sleep(1)
        self.power_dut_on()

    @keyword("Check is DUT power on")
    def check_is_dut_power_on(self):
        resp = self._hil_cmd("dut_power_status")    
        if "ON" in resp:
            return True
        else:
            raise AssertionError("DUT is not powered on")

    @keyword("Check is DUT power off")
    def check_is_dut_power_off(self):
        resp = self._hil_cmd("dut_power_status")    
        if "OFF" in resp:
            return True
        else:
            raise AssertionError("DUT is still powered on")


    # ------------------
    # FLASH FW
    # ------------------
    def set_dut_boot0(self, value):
        if value not in [0, 1]:
            raise AssertionError("BOOT0 value must be 0 or 1")
        self._hil_cmd(f"dut_boot0_set {value}")

    def _wait_for_dfu_device(self, timeout=10):

        start = time.time()

        while time.time() - start < timeout:

            result = subprocess.run(
                ["wmic", "path", "Win32_PnPEntity", "get", "Name"],
                capture_output=True,
                text=True,
            )

            out = result.stdout.lower()

            if "bootloader" in out or "STM32" in out:
                logger.info("STM32 DFU device detected")
                return

        # Nếu không thể tìm thấy device, cần thoát BOOT mode 1 reset lại DUT trước khi báo lỗi
        self.set_dut_boot0(0)
        BuiltIn().sleep(0.5)
        self.power_dut_cycle()
        raise AssertionError("STM32 DFU device not detected")
    
    def _flash_via_stm32_cli(self, fw_path):

        cli_path = r"C:\Program Files\STMicroelectronics\STM32Cube\STM32CubeProgrammer\bin\STM32_Programmer_CLI.exe"

        cmd = [
            cli_path,
            "-c", "port=USB1",
            "-w", fw_path,
            "0x08000000",
            "-v",
        ]

        logger.info("Flashing firmware...")

        result = subprocess.run(cmd, capture_output=True, text=True)

        logger.info(result.stdout)

        if result.returncode != 0:
            # Nếu fail, cần thoát BOOT mode 1 reset lại DUT trước khi báo lỗi
            self.set_dut_boot0(0)
            BuiltIn().sleep(0.5)
            self.power_dut_cycle()
            raise AssertionError("Flashing failed")

        if "Download verified successfully" not in result.stdout:
            # Nếu fail, cần thoát BOOT mode 1 reset lại DUT trước khi báo lỗi
            self.set_dut_boot0(0)
            BuiltIn().sleep(0.5)
            self.power_dut_cycle()
            raise AssertionError("Flash verification failed")

    @keyword("Flash Firmware")
    def flash_firmware(self, fw_path):
        # Check file exists
        if not os.path.isfile(fw_path):
            raise AssertionError(f"Firmware file not found: {fw_path}")
        
        logger.info("Entering DFU mode")
        # Set DUT BOOT0 to 1 to enter USB bootloader mode and power on DUT to apply change
        self.set_dut_boot0(1)
        BuiltIn().sleep(0.5)
        self.power_dut_cycle()

        # Check USB device is detected by HIL
        self._wait_for_dfu_device()
        logger.info("Waiting DFU stabilization...")

        # Flash fimware by using STM32 programmer CLI
        self._flash_via_stm32_cli(fw_path)
        
        logger.info("Leaving DFU mode")
        # After flashing, set BOOT0 back to 0 and reboot DUT to run new firmware
        self.set_dut_boot0(0)
        BuiltIn().sleep(0.5)
        self.power_dut_cycle()

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

    # ------------------
    # SPI FLASH (W25Q)
    # ------------------
    @keyword("HIL prepare SPI Flash data")
    def hil_prepare_spi_flash_data(self, length):
        length = self._validate_uint("length", length)
        resp = self._hil_cmd(f"w25q_prepare_mem {length}")
        if "HIL prepare" not in resp:
            raise AssertionError(f"HIL failed to prepare SPI Flash data")
        return True

    # ------------------
    # Generate waveform
    # ------------------
    @keyword("HIL Generate Sine Wave")
    def hil_generate_sine_wave(self, frequency):
        frequency = self._validate_uint("frequency", frequency)
        resp = self._hil_cmd(f"set_freq {frequency}")
        if "Invalid" in resp:
            raise AssertionError(f"Invalid frequency: {frequency}")
        resp = self._hil_cmd("sine_wave 1")
        if "Start" not in resp:
            raise AssertionError(f"HIL failed to generate sine wave")
        return True

    @keyword("HIL Stop Sine Wave")
    def hil_stop_sine_wave(self):
        resp = self._hil_cmd("sine_wave 0")
        if "Stop" not in resp:
            raise AssertionError(f"HIL failed to stop sine wave")
        return True

    @keyword("HIL Generate Triangle Wave")
    def hil_generate_triangle_wave(self, frequency):
        frequency = self._validate_uint("frequency", frequency)
        resp = self._hil_cmd(f"set_freq {frequency}")
        if "Invalid" in resp:
            raise AssertionError(f"Invalid frequency: {frequency}")

        resp = self._hil_cmd("triangle_wave 1")
        if "Start" not in resp:
            raise AssertionError(f"HIL failed to generate triangle wave")
        return True

    @keyword("HIL Stop Triangle Wave")
    def hil_stop_triangle_wave(self):
        resp = self._hil_cmd("triangle_wave 0")
        if "Stop" not in resp:
            raise AssertionError(f"HIL failed to stop triangle wave")
        return True

    # ------------------
    # Analog
    # ------------------
    @keyword("HIL Read ADC Voltage")
    def hil_read_adc_voltage(self, expected_volt=None):

        resp = self._hil_cmd("adc_read")

        match = re.search(r"Measured:\s*(\d+)\s*mV", resp)
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
    
    @keyword("HIL Set DAC Voltage")
    def hil_set_dac_voltage(self, voltage):
        voltage = float(voltage)
        if voltage < 0 or voltage > 3.3:
            raise AssertionError("Voltage must be between 0 and 3.3 V")
        resp = self._hil_cmd(f"dac_set_voltage {voltage}")
        if "ERROR" in resp:
            raise AssertionError(f"HIL failed to set DAC voltage")
        return True
