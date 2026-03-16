/*
 * adc.h
 *
 *  Created on: Mar 10, 2026
 *      Author: VyTran
 */

#ifndef EMUDRIVERS_INC_ANALOG_H_
#define EMUDRIVERS_INC_ANALOG_H_

#include "stm32f4xx_hal.h"
#include <stdint.h>
#include <stdbool.h>

float adc_read_voltage(void);
int pwm_verify_voltage(uint8_t ch, uint16_t target_mv, uint16_t tolerance_mv);
float adc_read_pwm_voltage(void);

#endif /* EMUDRIVERS_INC_ANALOG_H_ */
