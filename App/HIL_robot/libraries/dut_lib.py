from robot.api.deco import library, keyword
from cli_lib import CLI
import re
from robot.api import logger
from robot.api.deco import keyword
from robot.api import logger
from robot.libraries.BuiltIn import BuiltIn

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

    @keyword("HIL Help")
    def hil_help(self):
        """
        Send 'help' command to HIL and print raw response.
        Used to verify connection and communication.
        """

        resp = self.cli.execute("help")

        # log ra robot report (đẹp trong log.html)
        logger.info(f"HIL HELP RESPONSE:<br><pre>{resp}</pre>", html=True)

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
