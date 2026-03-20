*** Settings ***
Library    ../libraries/hil_lib.py
Library    BuiltIn

*** Variables ***
${HIL_PORT}          COM12
${HIL_BAUDRATE}             115200

*** Keywords ***
Connect To HIL
    Connect HIL     ${HIL_PORT}      ${HIL_BAUDRATE}

Disconnect from HIL    
    Disconnect HIL
