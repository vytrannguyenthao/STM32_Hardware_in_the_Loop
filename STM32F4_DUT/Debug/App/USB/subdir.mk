################################################################################
# Automatically-generated file. Do not edit!
# Toolchain: GNU Tools for STM32 (12.3.rel1)
################################################################################

# Add inputs and outputs from these tool invocations to the build variables 
C_SRCS += \
../App/USB/usb.c 

OBJS += \
./App/USB/usb.o 

C_DEPS += \
./App/USB/usb.d 


# Each subdirectory must supply rules for building sources it contributes
App/USB/%.o App/USB/%.su App/USB/%.cyclo: ../App/USB/%.c App/USB/subdir.mk
	arm-none-eabi-gcc "$<" -mcpu=cortex-m4 -std=gnu11 -g3 -DDEBUG -DUSE_HAL_DRIVER -DSTM32F407xx -DUSE_FULL_LL_DRIVER -c -I../Core/Inc -I../Drivers/STM32F4xx_HAL_Driver/Inc -I../Drivers/STM32F4xx_HAL_Driver/Inc/Legacy -I../Drivers/CMSIS/Device/ST/STM32F4xx/Include -I../Drivers/CMSIS/Include -I"D:/STUDY/00_SCHOOL/DA/STM32F4_HIL/ThirdParty/FreeRTOS/include" -I"D:/STUDY/00_SCHOOL/DA/STM32F4_HIL/ThirdParty/FreeRTOS/portable/GCC/ARM_CM4F" -I"D:/STUDY/00_SCHOOL/DA/STM32F4_HIL/ThirdParty/FreeRTOS/portable" -I"D:/STUDY/00_SCHOOL/DA/STM32F4_HIL/ThirdParty/FreeRTOS" -I"D:/STUDY/00_SCHOOL/DA/STM32F4_HIL/App/USB" -I"D:/STUDY/00_SCHOOL/DA/STM32F4_HIL/App/w25q_driver" -I"D:/STUDY/00_SCHOOL/DA/STM32F4_HIL/App/CMDLine" -I"D:/STUDY/00_SCHOOL/DA/STM32F4_HIL/App/UART" -O0 -ffunction-sections -fdata-sections -Wall -fstack-usage -fcyclomatic-complexity -MMD -MP -MF"$(@:%.o=%.d)" -MT"$@" --specs=nano.specs -mfpu=fpv4-sp-d16 -mfloat-abi=hard -mthumb -o "$@"

clean: clean-App-2f-USB

clean-App-2f-USB:
	-$(RM) ./App/USB/usb.cyclo ./App/USB/usb.d ./App/USB/usb.o ./App/USB/usb.su

.PHONY: clean-App-2f-USB

