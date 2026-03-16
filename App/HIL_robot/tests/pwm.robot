*** Settings ***
Library    ../libraries/hil_lib.py
Library    ../libraries/dut_lib.py

*** Test Cases ***
PWM Test
    Connect DUT    COM16
    Connect HIL    COM17

    Verify DUT Alive
    Verify HIL Alive

    Configure DUT PWM    1    10    1

    Wait Until Voltage Stable   0.9    1.1

    Disconnect DUT
    Disconnect HIL