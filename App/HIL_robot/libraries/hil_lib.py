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

    # ------------------
    # Connection
    # ------------------
    @keyword("Connect HIL")
    def connect_hil(self, port):
        """Connect to HIL serial"""
        self.cli.connect(port)
        logger.info(f"Connected HIL at {port}")

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

        resp = self.cli.execute("help")

        # log ra robot report
        logger.info(f"HIL HELP RESPONSE:<br><pre>{resp}</pre>", html=True)

        # log ra terminal
        logger.console("\n===== HIL HELP RESPONSE =====")
        logger.console(resp)
        logger.console("================================")

        return resp
    
    @keyword("Verify HIL Alive")
    def verify_hil_alive(self):

        resp = self.cli.execute("help")

        logger.info(f"HIL RESP:\n{resp}")

        if not resp.strip():
            raise AssertionError("HIL not responding")

        if "help" not in resp.lower():
            raise AssertionError("Invalid HIL response")

        return resp
    
    # ------------------
    # Power control
    # ------------------
    @keyword("Power DUT On")
    def power_dut_on(self):
        resp = self.cli.execute("dut_power 1")
        logger.info(resp)

    # ------------------
    # PWM
    # ------------------
    @keyword("Read HIL Voltage")
    def read_voltage(self):

        resp = self.cli.execute("adc_read_pwm")

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
