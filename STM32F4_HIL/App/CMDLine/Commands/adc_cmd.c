/*
 * adc_cmd.c
 *
 *  Created on: Mar 10, 2026
 *      Author: VyTran
 */

#include <stdio.h>
#include <stdlib.h>
#include "cmd.h"
#include "adc.h"

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

void Cmd_ADC_Register(void)
{
	CLI_RegisterCommand("adc_read", cmd_adc_read, "Read ADC value");
	CLI_RegisterCommand("adc_read_pwm", cmd_adc_read_pwm, "Read PWM voltage value");
}


