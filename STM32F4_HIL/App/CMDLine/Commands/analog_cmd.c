/*
 * ananlog_cmd.c
 *
 *  Created on: Mar 10, 2026
 *      Author: VyTran
 */

#include <analog.h>
#include <stdio.h>
#include <stdlib.h>
#include "cmd.h"

static int cmd_adc_read(int argc, char *argv[])
{
	if(argc < 1) return CMDLINE_TOO_FEW_ARGS;
	if(argc > 2) return CMDLINE_TOO_MANY_ARGS;

	float v = adc_read_voltage();
	uint16_t meas = v * 1000;

	Console_Write("\r\n Measured: %u mV\r\n", meas);

	return CMDLINE_OK;
}

static int cmd_adc_read_pwm(int argc, char *argv[])
{
	if(argc < 1) return CMDLINE_TOO_FEW_ARGS;
	if(argc > 2) return CMDLINE_TOO_MANY_ARGS;

	float v = adc_read_pwm_voltage();
	uint16_t meas = v * 1000;

	Console_Write("\r\n Measured: %u mV\r\n", meas);

	return CMDLINE_OK;
}

extern DAC_HandleTypeDef hdac;
static int Cmd_DAC_Set_Voltage(int argc, char *argv[]) {
    if (argc < 3) {
        return CMDLINE_TOO_FEW_ARGS;
    }
    if (argc > 3) {
        return CMDLINE_TOO_MANY_ARGS;
    }

    char *input = argv[1];
    char *dot_pos = strchr(input, '.');

    // Nếu có dấu chấm, kiểm tra phần thập phân
    if (dot_pos != NULL) {
        // dot_pos + 1 là vị trí chữ số đầu tiên sau dấu chấm
        // strlen(dot_pos + 1) sẽ trả về số lượng chữ số sau dấu chấm
        if (strlen(dot_pos + 1) > 1) {
            Console_Write("Error: Only 1 decimal place allowed (e.g., 1.2)\r\n");
            return CMDLINE_OK;
        }
    }

    float voltage = atof(input);
    if (voltage < 0.0f || voltage > 3.3f) {
        Console_Write("Error: Voltage out of range (0.0 - 3.3)\r\n");
        return CMDLINE_OK;
    }

    uint32_t dac_value = (uint32_t)((voltage / 3.3f) * 4095);
    HAL_DAC_SetValue(&hdac, DAC_CHANNEL_2, DAC_ALIGN_12B_R, dac_value);
    return CMDLINE_OK;
}

void Cmd_Analog_Register(void)
{
	CLI_RegisterCommand("adc_read", cmd_adc_read, "Read ADC value");
	CLI_RegisterCommand("adc_read_pwm", cmd_adc_read_pwm, "Read PWM voltage value");
    CLI_RegisterCommand("dac_set_voltage", Cmd_DAC_Set_Voltage, "Set DAC voltage | format: dac_set_voltage <X.Y> (0.0-3.3V)");
}


