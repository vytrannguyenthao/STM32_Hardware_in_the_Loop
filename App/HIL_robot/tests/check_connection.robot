*** Settings ***
Library    ../libraries/hil_lib.py
Library    ../libraries/dut_lib.py


*** Test Cases ***
Test Connection
    Connect HIL    COM17
    Verify HIL Alive
    Disconnect HIL

    Connect DUT    COM16
    Verify DUT Alive
    Disconnect DUT