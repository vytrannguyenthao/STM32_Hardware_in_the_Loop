/*
 * dut_control_cmd.c
 *
 *  Created on: Mar 16, 2026
 *      Author: Admin
 */

#ifndef CMDLINE_COMMANDS_DUT_CONTROL_CMD_C_
#define CMDLINE_COMMANDS_DUT_CONTROL_CMD_C_

#include <stdio.h>
#include <stdlib.h>
#include "cmd.h"
#include <stm32f4xx_ll_gpio.h>
#include "FreeRTOS.h"
#include "w25q_slave.h"

static int Cmd_Power_DUT(int argc, char *argv[]) {
    if (argc < 3)
        return CMDLINE_TOO_FEW_ARGS;
    if (argc > 3)
        return CMDLINE_TOO_MANY_ARGS;

    uint32_t status = atoi(argv[1]);
    if(status) {
        // Power on DUT
        LL_GPIO_SetOutputPin(DUT_POWER_GPIO_Port, DUT_POWER_Pin);
        vTaskDelay(pdMS_TO_TICKS(100)); // delay để DUT ổn định
        SPI3_Reset();

        if (LL_GPIO_IsInputPinSet(DUT_POWER_STATUS_GPIO_Port, DUT_POWER_STATUS_Pin)) {
            // DUT đã bật (logic HIGH)
        	Console_Write("DUT is powered ON\r\n");
        } else {
            // DUT không bật được (logic LOW)
        	Console_Write("Failed to power ON DUT\r\n");
        }
    } else {
        LL_GPIO_ResetOutputPin(DUT_POWER_GPIO_Port, DUT_POWER_Pin);

        vTaskDelay(pdMS_TO_TICKS(100)); // delay để DUT ổn định

        if (LL_GPIO_IsInputPinSet(DUT_POWER_STATUS_GPIO_Port, DUT_POWER_STATUS_Pin)) {
            // DUT đã bật (logic HIGH)
        	Console_Write("Failed to power OFF DUT\r\n");
        } else {
            // DUT không bật được (logic LOW)
        	Console_Write("DUT is powered OFF\r\n");
        }
    }
    return CMDLINE_OK;
}

static int Cmd_Power_Status(int argc, char *argv[]) {
    if (argc > 2)
        return CMDLINE_TOO_MANY_ARGS;

    if (LL_GPIO_IsInputPinSet(DUT_POWER_STATUS_GPIO_Port, DUT_POWER_STATUS_Pin)) {
        // DUT đã bật (logic HIGH)
        Console_Write("DUT ON\r\n");
    } else {
        // DUT không bật được (logic LOW)
        Console_Write("DUT OFF\r\n");
    }

    return CMDLINE_OK;
}

void Cmd_DUT_Control_Register(void)
{
	CLI_RegisterCommand("dut_power", Cmd_Power_DUT, "Power DUT on/off | format: dut_power <0|1>");
	CLI_RegisterCommand("dut_power_status", Cmd_Power_Status, "Check DUT power status | format: dut_power_status");
}

#endif /* CMDLINE_COMMANDS_DUT_CONTROL_CMD_C_ */
