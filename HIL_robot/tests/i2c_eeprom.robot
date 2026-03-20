*** Settings ***
Resource    ../resources/HIL_keywords.robot
Resource    ../user_resources/DUT_keywords.robot

Suite Setup         Run Keywords
...                 Connect To HIL          AND
...                 Power DUT On            AND
...                 Connect To DUT

Suite Teardown      Run Keywords
...                 Disconnect from HIL     AND
...                 Disconnect from DUT

*** Test Cases ***
EEPROM Validation
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
