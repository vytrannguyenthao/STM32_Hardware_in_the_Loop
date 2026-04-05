*** Settings ***
Resource    ../resources/HIL_keywords.robot
Resource    ../user_resources/DUT_keywords.robot
Suite Setup         Run Keywords
...                 Connect To HIL               AND
...                 Connect To Logic Analyzer    AND
...                 Power DUT On                 AND
...                 Connect To DUT

Suite Teardown      Run Keywords
...                 Disconnect from HIL     AND
...                 Disconnect from Logic Analyzer    AND
...                 Disconnect from DUT


*** Variables ***
${FREQUENCY}       1000
*** Test Cases ***

DUT Generate Sine Wave and Acquire Data
    DUT Generate Sine Wave    ${FREQUENCY}
    ${data}    Read Logic Analyzer Data
    Verify Sine Wave    ${data}    ${FREQUENCY}

DUT Stop Sine Wave
    DUT Stop Sine Wave
