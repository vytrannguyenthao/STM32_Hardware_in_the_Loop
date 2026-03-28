from robot.api.deco import library, keyword
from robot.api import logger
from cli_lib import CLI
import re
from robot.libraries.BuiltIn import BuiltIn

@library(scope="GLOBAL")
class Logic_Library:
    """
    Robot Library for Logic Analyzer
    """

    def __init__(self):
        self.cli = CLI()

    # ------------------
    # Connection
    # ------------------
    @keyword("Connect Logic Analyzer")
    def connect_la(self, port, baud=115200):
        self.cli.connect(port, baud)

    @keyword("Disconnect Logic Analyzer")
    def disconnect_la(self):
        self.cli.disconnect()

    @keyword("Setup Logic Analyzer")
    def setup_la(self, rate, samples):
        self.cli.setup_logic_analyzer(rate, samples)
        logger.info(f"Logic Analyzer setup: samples={samples}, rate={rate} Hz")
    
    @keyword("Read Logic Analyzer Data")
    def read_la_data(self):
        data = self.cli.capture_binary_stream(timeout_sec=12.0)
        logger.info(f"Logic Analyzer data length: {len(data)} bytes")
        return data
