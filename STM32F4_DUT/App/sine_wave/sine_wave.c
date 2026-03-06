/*
 * sine_wave.c
 *
 *  Created on: Feb 14, 2026
 *      Author: Samy Ve
 */

#include "sine_wave.h"
#include "math.h"

#define PI 3.1415926
#define SAMPLES_NUM 100
#define DAC_MAX 4000
#define APB2_CLK 60000000

extern DAC_HandleTypeDef hdac;

extern TIM_HandleTypeDef htim2;

uint32_t sine_val[100];

struct sine_wave_t
{
	bool is_freq_set;
	uint32_t freq;

};

struct sine_wave_t sine_wave = {
	.is_freq_set = false,
	.freq = 0
};

void calcsin (void) {
	for (uint32_t i=0; i<SAMPLES_NUM; i++) {
		sine_val[i] = ((sin(i*2*PI/SAMPLES_NUM) + 1)*(DAC_MAX/2));
	}
}

bool is_sine_wave_freq_set() {
	return sine_wave.is_freq_set;
}

void set_freq(uint32_t sine_wave_freq) {
	sine_wave.freq = sine_wave_freq;
	sine_wave.is_freq_set = true;

	uint32_t f_sample = sine_wave_freq * SAMPLES_NUM;
	uint32_t N = APB2_CLK / f_sample;
	uint32_t prescaler = 6; // Bắt đầu với một giá trị prescaler nhỏ để có độ phân giải cao hơn
	uint32_t arr;

	// tìm prescaler sao cho ARR <= 0xFFFF
	while ((arr = N / prescaler) > 0xFFFF) {
		prescaler++;
	}

	htim2.Init.Prescaler = prescaler - 1;
	htim2.Init.Period = arr - 1;
	HAL_TIM_Base_Init(&htim2);
}

uint32_t get_freq(void) {
	return sine_wave.freq;
}

void stop_sine_wave() {
	HAL_TIM_Base_Stop(&htim2);
	HAL_DAC_Stop_DMA(&hdac, DAC_CHANNEL_1);
}

void start_sine_wave() {
	HAL_TIM_Base_Start(&htim2);
	HAL_DAC_Start_DMA(&hdac, DAC_CHANNEL_1, sine_val, SAMPLES_NUM, DAC_ALIGN_12B_R);
}
