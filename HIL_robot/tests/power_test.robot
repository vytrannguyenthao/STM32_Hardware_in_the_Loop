*** Settings ***
Resource    ../resources/HIL_keywords.robot
Suite Setup         Connect To HIL
Suite Teardown      Disconnect from HIL

*** Test Cases ***
Test Power DUT On
    Power DUT On
    Check is DUT power on

Test Power DUT Off
    Power DUT Off
    Check is DUT power off
