*** Settings ***
Resource    ../resources/HIL_keywords.robot
Resource    ../user_resources/DUT_keywords.robot

Suite Setup         Run Keywords
...                 Connect To HIL               AND
...                 Connect To Logic Analyzer    AND
...                 Power DUT On                 AND
...                 Connect To DUT

Suite Teardown      Run Keywords
...                 Disconnect from HIL               AND
...                 Disconnect from Logic Analyzer    AND
...                 Disconnect from DUT

*** Variables ***
${SAMPLE_RATE}     250000
${SAMPLE_COUNT}    2500000
${FREQUENCY}       1000

*** Test Cases ***
DUT Generate PWM Signal and Acquire Data
    # Set up DUT
    Set DUT PWM freq    freq=1
    Set DUT volt    ch=1    volt=0.825
    Set DUT volt    ch=2    volt=1.65
    Start DUT PWM   ch=1
    Start DUT PWM   ch=2

    # Set up Logic Analyzer
    Setup Logic Analyzer    ${SAMPLE_RATE}    ${SAMPLE_COUNT}
    ${data}    Read Logic Analyzer Data

    # Verify results
    Verify Digital Channel    raw_data=${data}    channel=3    expected_freq_hz=${FREQUENCY}    expected_duty_cycle=25
    Verify Digital Channel    raw_data=${data}    channel=2    expected_freq_hz=${FREQUENCY}    expected_duty_cycle=50

DUT Stop PWM Signal
    Stop DUT PWM   ch=1
    Stop DUT PWM   ch=2
