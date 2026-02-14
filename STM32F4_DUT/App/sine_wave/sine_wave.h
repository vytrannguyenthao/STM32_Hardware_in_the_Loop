/*
 * sine_wave.h
 *
 *  Created on: Feb 14, 2026
 *      Author: Samy Ve
 */

#ifndef SINE_WAVE_SINE_WAVE_H_
#define SINE_WAVE_SINE_WAVE_H_

#include "stm32f4xx_hal.h"
#include "stdint.h"
#include "stdbool.h"

void calcsin (void);
bool is_sine_wave_freq_set();
uint32_t get_freq(void);
void set_freq(uint32_t sine_wave_freq);
void stop_sine_wave();
void start_sine_wave();

#endif /* SINE_WAVE_SINE_WAVE_H_ */
