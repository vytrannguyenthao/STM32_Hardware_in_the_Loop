*** Settings ***
Resource    ../resources/HIL_keywords.robot
Resource    ../user_resources/DUT_keywords.robot

Suite Setup         Run Keywords
...                 Connect To HIL               AND
...                 Connect To Logic Analyzer    AND
...                 Power DUT On                 AND
...                 Connect To DUT

Suite Teardown      Run Keywords
...                 Power DUT Off                     AND
...                 Disconnect from HIL               AND
...                 Disconnect from Logic Analyzer    AND
...                 Disconnect from DUT

*** Variables ***
${PWM_FREQUENCY}       1
${PWM_DUTY_CYCLE}      50
${PWM_CHANNEL}         1
${LA_DIGITAL_CHANNEL}  0

*** Test Cases ***
DUT Generate PWM Signal
    Set DUT PWM freq      freq=${PWM_FREQUENCY}
    Set DUT duty cycle    ch=${PWM_CHANNEL}    duty=${PWM_DUTY_CYCLE} 
    Start DUT PWM   ch=${PWM_CHANNEL}

Verify PWM Signal with Logic Analyzer
    # Read data from logic analyzer
    ${data}    Read Logic Analyzer Data

    # Verify results
    Verify Pulse Wave    raw_data=${data}    channel=${LA_DIGITAL_CHANNEL}    expected_freq_hz=${PWM_FREQUENCY}    expected_duty_cycle=${PWM_DUTY_CYCLE}

DUT Stop PWM Signal
    Stop DUT PWM   ch=${PWM_CHANNEL}