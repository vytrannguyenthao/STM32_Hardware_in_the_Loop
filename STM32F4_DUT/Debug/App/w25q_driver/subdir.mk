################################################################################
# Automatically-generated file. Do not edit!
# Toolchain: GNU Tools for STM32 (12.3.rel1)
################################################################################

# Add inputs and outputs from these tool invocations to the build variables 
C_SRCS += \
../App/w25q_driver/w25q_driver.c 

OBJS += \
./App/w25q_driver/w25q_driver.o 

C_DEPS += \
./App/w25q_driver/w25q_driver.d 


# Each subdirectory must supply rules for building sources it contributes
App/w25q_driver/%.o App/w25q_driver/%.su App/w25q_driver/%.cyclo: ../App/w25q_driver/%.c App/w25q_driver/subdir.mk
	arm-none-eabi-gcc "$<" -mcpu=cortex-m4 -std=gnu11 -g3 -DDEBUG -DUSE_HAL_DRIVER -DSTM32F407xx -DUSE_FULL_LL_DRIVER -c -I../Core/Inc -I../Drivers/STM32F4xx_HAL_Driver/Inc -I../Drivers/STM32F4xx_HAL_Driver/Inc/Legacy -I../Drivers/CMSIS/Device/ST/STM32F4xx/Include -I../Drivers/CMSIS/Include -I"D:/STUDY/00_SCHOOL/DA/STM32F4_HIL/ThirdParty/FreeRTOS/include" -I"D:/STUDY/00_SCHOOL/DA/STM32F4_HIL/ThirdParty/FreeRTOS/portable/GCC/ARM_CM4F" -I"D:/STUDY/00_SCHOOL/DA/STM32F4_HIL/ThirdParty/FreeRTOS/portable" -I"D:/STUDY/00_SCHOOL/DA/STM32F4_HIL/ThirdParty/FreeRTOS" -I"D:/STUDY/00_SCHOOL/DA/STM32F4_HIL/App/USB" -I"D:/STUDY/00_SCHOOL/DA/STM32F4_HIL/App/w25q_driver" -I"D:/STUDY/00_SCHOOL/DA/STM32F4_HIL/App/CMDLine" -I"D:/STUDY/00_SCHOOL/DA/STM32F4_HIL/App/UART" -I"D:/STUDY/00_SCHOOL/DA/STM32F4_HIL/App/i2c_eeprom_driver" -O0 -ffunction-sections -fdata-sections -Wall -fstack-usage -fcyclomatic-complexity -MMD -MP -MF"$(@:%.o=%.d)" -MT"$@" --specs=nano.specs -mfpu=fpv4-sp-d16 -mfloat-abi=hard -mthumb -o "$@"

clean: clean-App-2f-w25q_driver

clean-App-2f-w25q_driver:
	-$(RM) ./App/w25q_driver/w25q_driver.cyclo ./App/w25q_driver/w25q_driver.d ./App/w25q_driver/w25q_driver.o ./App/w25q_driver/w25q_driver.su

.PHONY: clean-App-2f-w25q_driver

