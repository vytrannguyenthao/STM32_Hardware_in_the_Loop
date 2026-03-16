/*
 * pwm_control.h
 *
 *  Created on: Mar 10, 2026
 *      Author: VyTran
 */

#ifndef PWM_PWM_CONTROL_H_
#define PWM_PWM_CONTROL_H_

#include "stm32f4xx_hal.h"
#include "stdint.h"
#include "stdbool.h"

int pwm_start(uint8_t ch);
int pwm_stop(uint8_t ch);
void set_pwm_freq(uint16_t freq_khz);
void set_pwm_voltage(uint8_t ch, uint16_t voltage_mv);

#endif /* PWM_PWM_CONTROL_H_ */
