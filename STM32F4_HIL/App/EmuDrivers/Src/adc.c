/*
 * adc.c
 *
 *  Created on: Mar 10, 2026
 *      Author: VyTran
 */

#include "adc.h"

extern ADC_HandleTypeDef hadc1;
static ADC_HandleTypeDef *hadc = &hadc1;

float adc_read_voltage(void)
{
	HAL_ADC_Start(&hadc1);
	HAL_ADC_PollForConversion(hadc, 100);

	uint16_t adc_value = HAL_ADC_GetValue(hadc);

	HAL_ADC_Stop(hadc);

	return ((float)adc_value * 3.3f) / 4095.0f;
}

int pwm_verify_voltage(uint8_t ch, uint16_t target_mv, uint16_t tolerance_mv)
{
	float v = adc_read_voltage();
	uint16_t mv = (uint16_t)(v * 1000);

	if(mv > target_mv + tolerance_mv || mv < target_mv - tolerance_mv)
		return 1;

	return 0;
}

float adc_read_pwm_voltage(void)
{
    uint32_t sum = 0;

    for(int i=0;i<100;i++)
    {
        HAL_ADC_Start(&hadc1);
        HAL_ADC_PollForConversion(&hadc1,10);
        sum += HAL_ADC_GetValue(&hadc1);
        HAL_ADC_Stop(&hadc1);
    }

    float adc = sum / 100.0f;

    return adc * 3.3f / 4095.0f;
}
