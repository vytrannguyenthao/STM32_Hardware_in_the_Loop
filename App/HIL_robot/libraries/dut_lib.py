from robot.api.deco import library, keyword
from robot.api import logger
from cli_lib import CLI

@library(scope="GLOBAL")
class DUTLibrary:
    """
    Robot Library for DUT firmware
    """

    def __init__(self):
        self.cli = CLI()

    # ------------------
    # Connection
    # ------------------
    @keyword("Connect DUT")
    def connect_dut(self, port):
        self.cli.connect(port)

    @keyword("Disconnect DUT")
    def disconnect_dut(self):
        self.cli.disconnect()

    @keyword("DUT Help")
    def dut_help(self):
        """
        Send 'help' command to HIL and print raw response.
        Used to verify connection and communication.
        """

        resp = self.cli.execute("help")

        # log ra robot report (đẹp trong log.html)
        logger.info(f"DUT HELP RESPONSE:<br><pre>{resp}</pre>", html=True)

        # log ra terminal
        logger.console("\n===== HIL HELP RESPONSE =====")
        logger.console(resp)
        logger.console("================================")

        return resp

    @keyword("Verify DUT Alive")
    def verify_dut_alive(self):

        resp = self.cli.execute("help")

        logger.info(f"DUT RESP:\n{resp}")

        if not resp.strip():
            raise AssertionError("DUT not responding")

        if "help" not in resp.lower():
            raise AssertionError("Invalid DUT response")

        return resp

    # ------------------
    # PWM
    # ------------------

    @keyword("Start DUT PWM")
    def start_pwm(self, ch):
        self.cli.execute(f"pwm_start {ch}")

    @keyword("Stop DUT PWM")
    def stop_pwm(self, ch):
        self.cli.execute(f"pwm_stop {ch}")

    @keyword("Set DUT volt")
    def set_pwm_volt(self, ch, volt):
        mv = int(float(volt) * 1000)
        self.cli.execute(f"pwm_volt {ch} {mv}")

    @keyword("Set DUT PWM freq")
    def set_pwm_freq(self, freq):
        self.cli.execute(f"pwm_freq {freq}")

    @keyword("Configure DUT PWM")
    def configure_pwm(self, ch, freq, volt):
        mv = int(float(volt) * 1000)
        self.cli.execute(f"pwm_freq {freq}")
        self.cli.execute(f"pwm_volt {ch} {mv}")
        self.cli.execute(f"pwm_start {ch}")