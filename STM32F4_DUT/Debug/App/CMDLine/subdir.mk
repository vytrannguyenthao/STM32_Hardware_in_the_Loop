################################################################################
# Automatically-generated file. Do not edit!
# Toolchain: GNU Tools for STM32 (12.3.rel1)
################################################################################

# Add inputs and outputs from these tool invocations to the build variables 
C_SRCS += \
../App/CMDLine/cmdline.c \
../App/CMDLine/command.c 

OBJS += \
./App/CMDLine/cmdline.o \
./App/CMDLine/command.o 

C_DEPS += \
./App/CMDLine/cmdline.d \
./App/CMDLine/command.d 


# Each subdirectory must supply rules for building sources it contributes
App/CMDLine/%.o App/CMDLine/%.su App/CMDLine/%.cyclo: ../App/CMDLine/%.c App/CMDLine/subdir.mk
	arm-none-eabi-gcc "$<" -mcpu=cortex-m4 -std=gnu11 -g3 -DDEBUG -DUSE_HAL_DRIVER -DSTM32F407xx -DUSE_FULL_LL_DRIVER -c -I../Core/Inc -I../Drivers/STM32F4xx_HAL_Driver/Inc -I../Drivers/STM32F4xx_HAL_Driver/Inc/Legacy -I../Drivers/CMSIS/Device/ST/STM32F4xx/Include -I../Drivers/CMSIS/Include -I"D:/STUDY/00_SCHOOL/DA/STM32F4_HIL/ThirdParty/FreeRTOS/include" -I"D:/STUDY/00_SCHOOL/DA/STM32F4_HIL/ThirdParty/FreeRTOS/portable/GCC/ARM_CM4F" -I"D:/STUDY/00_SCHOOL/DA/STM32F4_HIL/ThirdParty/FreeRTOS/portable" -I"D:/STUDY/00_SCHOOL/DA/STM32F4_HIL/ThirdParty/FreeRTOS" -I"D:/STUDY/00_SCHOOL/DA/STM32F4_HIL/App/USB" -I"D:/STUDY/00_SCHOOL/DA/STM32F4_HIL/App/w25q_driver" -I"D:/STUDY/00_SCHOOL/DA/STM32F4_HIL/App/CMDLine" -I"D:/STUDY/00_SCHOOL/DA/STM32F4_HIL/App/UART" -I"D:/STUDY/00_SCHOOL/DA/STM32F4_HIL/App/i2c_eeprom_driver" -O0 -ffunction-sections -fdata-sections -Wall -fstack-usage -fcyclomatic-complexity -MMD -MP -MF"$(@:%.o=%.d)" -MT"$@" --specs=nano.specs -mfpu=fpv4-sp-d16 -mfloat-abi=hard -mthumb -o "$@"

clean: clean-App-2f-CMDLine

clean-App-2f-CMDLine:
	-$(RM) ./App/CMDLine/cmdline.cyclo ./App/CMDLine/cmdline.d ./App/CMDLine/cmdline.o ./App/CMDLine/cmdline.su ./App/CMDLine/command.cyclo ./App/CMDLine/command.d ./App/CMDLine/command.o ./App/CMDLine/command.su

.PHONY: clean-App-2f-CMDLine

