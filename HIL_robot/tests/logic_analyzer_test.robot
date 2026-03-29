*** Settings ***
Resource    ../resources/HIL_keywords.robot
Resource    ../user_resources/DUT_keywords.robot
Suite Setup         Run Keywords
...                 Connect To HIL               AND
...                 Connect To Logic Analyzer

Suite Teardown      Run Keywords
...                 Disconnect from HIL     AND
...                 Disconnect from Logic Analyzer

*** Variables ***
${SAMPLE_RATE}     250000
${SAMPLE_COUNT}    2500000

*** Test Cases ***
Test Set up Logic Analyzer
    # Thêm các bước thiết lập logic analyzer nếu cần
    Setup Logic Analyzer    ${SAMPLE_RATE}    ${SAMPLE_COUNT}
    ${data}    Read Logic Analyzer Data
    Verify Sine Wave    ${data}
