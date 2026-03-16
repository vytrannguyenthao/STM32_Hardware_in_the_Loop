from robot.api.deco import library, keyword
from robot.api import logger
from cli_lib import CLI
import re
from robot.api import logger
from robot.api.deco import keyword
from robot.api import logger
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
    