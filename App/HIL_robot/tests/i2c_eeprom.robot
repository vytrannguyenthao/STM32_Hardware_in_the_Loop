*** Settings ***
Library    ../libraries/hil_lib.py
Library    ../libraries/dut_lib.py

*** Test Cases ***
*** Test Cases ***
EEPROM Validation

    Connect HIL    COM17
    Connect DUT    COM16

    Verify HIL Alive
    Verify DUT Alive

    # --- HIL setup ---
    HIL Init EEPROM        0x50    1024    256
    HIL Activate I2C Device    0x50

    # --- DUT setup ---
    DUT Init EEPROM        0x50    1024    256

    # --- Timing ---
    ${t}=    Measure EEPROM Write Time    0x50    256
    Write Time Should Be Less Than    ${t}    5

    # --- Data validation ---
    ${data}=    DUT Write And Verify EEPROM    0x50    256
    EEPROM Data Should Increment    ${data}

    # --- HIL deinit ---
    HIL Deinit EEPROM        0x50

    Disconnect DUT
    Disconnect HIL