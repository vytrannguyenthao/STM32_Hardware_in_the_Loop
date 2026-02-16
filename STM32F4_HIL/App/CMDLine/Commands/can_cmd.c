/*
 * can_cmd.c
 *
 *  Created on: Feb 16, 2026
 *      Author: Samy Ve
 */

#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include "cmd.h"
#include "can_driver.h"

static int Cmd_CAN_Send_Buffer(int argc, char *argv[]) {
	if (argc > 2) return CMDLINE_TOO_MANY_ARGS;
        
	CAN_SendBuffer();
	return CMDLINE_OK;
}

static int Cmd_CAN_Read_Buffer(int argc, char *argv[]) {
	if (argc > 2) return CMDLINE_TOO_MANY_ARGS;
        
	Console_Write("DUT ID: 0x%x\r\n", can_driver.rx_header.StdId);
    Console_Write("Data:\r\n");

    char buffer[128];
    for (uint32_t i = 0; i < 256; i++) {
		snprintf(buffer, sizeof(buffer), "%02X ", can_driver.rx_buffer[i]);
		Console_Write(buffer);
		if ((i + 1) % 16 == 0) {
			Console_Write("\r\n");
		}
	}
	Console_Write("\r\n");

	return CMDLINE_OK;
}

static int Cmd_CAN_Blink_LED(int argc, char *argv[]) {
	if (argc < 4) {
		return CMDLINE_TOO_FEW_ARGS;
	}
	if (argc > 4) {
		return CMDLINE_TOO_MANY_ARGS;
	}
        
	uint8_t tx_buf[2] = {0};
	tx_buf[0] = atoi(argv[1]); // LED index
	tx_buf[1] = atoi(argv[2]); // Blink count
        
	CAN_Send(tx_buf, 2);
	return CMDLINE_OK;
}

void Cmd_CAN_Register(void) {
    CLI_RegisterCommand("can_send_buffer", Cmd_CAN_Send_Buffer, "Send 256 bytes of data over CAN");
    CLI_RegisterCommand("can_read_buffer", Cmd_CAN_Read_Buffer, "Read received CAN data buffer");
    CLI_RegisterCommand("can_blink_led", Cmd_CAN_Blink_LED, "Blink DUT LED via CAN | format: can_blink_led <led_index> <blink_count>");
}
