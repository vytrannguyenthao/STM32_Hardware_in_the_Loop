*** Settings ***
Resource    ../resources/HIL_keywords.robot
Resource    ../user_resources/DUT_keywords.robot

Suite Setup         Run Keywords
...                 Connect To HIL               AND
...                 Connect To Logic Analyzer    AND
...                 Power DUT On                 AND
...                 Connect To DUT

Suite Teardown      Run Keywords
# ...                 Power DUT Off                     AND
...                 Disconnect from HIL               AND
...                 Disconnect from Logic Analyzer    AND
...                 Disconnect from DUT

*** Variables ***
${SAMPLE_FREQ}         250000
${SAMPLE_COUNT}        100000
${PWM_FREQUENCY}       10000
${PWM_DUTY_CYCLE}      60
${PWM_CHANNEL}         1
${LA_DIGITAL_CHANNEL}  0

*** Test Cases ***
DUT Generate PWM Signal
    Set DUT PWM freq      freq=${PWM_FREQUENCY}
    Set DUT duty cycle    ch=${PWM_CHANNEL}    duty=${PWM_DUTY_CYCLE} 
    Start DUT PWM   ch=${PWM_CHANNEL}

Verify PWM Signal with Logic Analyzer
    # Set up Logic Analyzer
    Setup Logic Analyzer    ${SAMPLE_FREQ}    ${SAMPLE_COUNT}
    ${data}    Read Logic Analyzer Data

    # Verify results
    Verify Pulse Wave    raw_data=${data}    channel=${LA_DIGITAL_CHANNEL}    expected_freq_hz=${PWM_FREQUENCY}    expected_duty_cycle=${PWM_DUTY_CYCLE}

DUT Stop PWM Signal
    Stop DUT PWM   ch=${PWM_CHANNEL}