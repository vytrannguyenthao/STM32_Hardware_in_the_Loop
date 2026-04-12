*** Settings ***
Resource    ../resources/HIL_keywords.robot
Resource    ../user_resources/DUT_keywords.robot

Suite Setup         Run Keywords
...                 Connect To HIL          AND
...                 Power DUT On            AND
...                 Connect To DUT

Suite Teardown      Run Keywords
...                 Power DUT Off           AND
...                 Disconnect from HIL     AND
...                 Disconnect from DUT

*** Test Cases ***
RTC Initialization
    # --- HIL setup ---
    HIL Init RTC        0x68
    HIL Activate I2C Device    0x68

    # --- DUT setup ---
    DUT Init RTC

RTC Set and Get Time/Date
    DUT Set RTC Time    14    30    45
    ${time}=    DUT Get RTC Time
    RTC Time Should Be Within    ${time}    14    30    45    7

    DUT Set RTC Date    1    12    4    26
    ${date}=    DUT Get RTC Date
    RTC Date Should Be    ${date}    1    12    4    26

RTC Time Progression
    DUT Set RTC Date    7    31    12    26
    DUT Set RTC Time    23    59    50
    Sleep    10s
    ${date}=    DUT Get RTC Date
    ${time}=    DUT Get RTC Time
    RTC Time Should Be Within    ${time}    0    0    0    7
    RTC Date Should Be    ${date}    1    1    1    27
    
