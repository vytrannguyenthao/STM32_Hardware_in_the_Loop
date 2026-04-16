*** Settings ***
Library    ../libraries/hil_lib.py
Library    ../libraries/logic_analyzer_lib.py
Library    BuiltIn

*** Variables ***
${HIL_PORT}          COM12
${LOG_PORT}          COM8
${HIL_BAUDRATE}      921600

*** Keywords ***
Connect To HIL
    Connect HIL     ${HIL_PORT}      ${HIL_BAUDRATE}

Disconnect from HIL    
    Disconnect HIL

Connect To Logic Analyzer
    Connect Logic Analyzer     ${LOG_PORT}

Disconnect from Logic Analyzer
    Disconnect Logic Analyzer
