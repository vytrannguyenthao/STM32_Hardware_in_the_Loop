/*
 * w25q_slave.c
 *
 *  Created on: Sep 27, 2025
 *      Author: Samy Ve
 */

#include "w25q_slave.h"

extern SPI_HandleTypeDef hspi3;

static uint8_t dummy = 0xFF;

W25Q_Slave w25q = {
	.spi = SPI3,
	.device_id = {0xEF, 0x40, 0x18}, // ID cho W25Q128
	.address = 0,
	.cmd = W25Q_NO_CMD,
	.rx_count = 0,
	.tx_count = 0,
	.rx_data = 0,
	.is_cmd_received = false,
	.count_byte_address = 0
};

// Hàm khởi tạo W25Q_Slave
void W25Q_Slave_Init(W25Q_Slave* dev) {
	memset(dev->memory, 0xFF, sizeof(dev->memory)); // Khởi tạo bộ nhớ mô phỏng với giá trị 0xFF
}

static void Reset_W25Q (W25Q_Slave* dev) {
	dev->cmd = W25Q_NO_CMD;
	dev->rx_count = 0;
	dev->tx_count = 0;
	dev->address = 0;
	dev->is_cmd_received = false;
	dev->count_byte_address = 0;
}

void W25Q_Slave_IRQHandler(W25Q_Slave *dev, uint8_t rx_data)
{
    uint8_t next_tx = dummy; // mặc định gửi dummy

    // Nếu chưa có command thì byte đầu tiên chính là command
    if (dev->cmd == W25Q_NO_CMD) {
        dev->cmd = rx_data;
        dev->tx_count = 0;
        dev->rx_count = 0;
        dev->count_byte_address = 0;

        switch (dev->cmd) {
        case W25Q_READ_ID_CMD:
            next_tx = dev->device_id[dev->tx_count++];
            break;

        case W25Q_READ_STATUS_REG1_CMD:
            next_tx = 0x00; // status mặc định
            break;

        case W25Q_CHIP_ERASE_CMD:
            memset(dev->memory, 0xFF, sizeof(dev->memory));
            break;

        default:
            next_tx = dummy;
            break;
        }
    } else {
        // Đã có command, xử lý các byte tiếp theo
        switch (dev->cmd) {
        case W25Q_READ_ID_CMD:
            if (dev->tx_count < 3) {
                next_tx = dev->device_id[dev->tx_count++];
            }
            break;

        case W25Q_READ_CMD:
            if (dev->count_byte_address < 3) {
                dev->address = (dev->address << 8) | rx_data;
                dev->count_byte_address++;
                dev->address &= 0x00FFFFFF;
                if (dev->count_byte_address == 3) {
                    next_tx = dev->memory[dev->address++];
                }
            } else {
                next_tx = dev->memory[dev->address + dev->tx_count++];
            }
            break;

        case W25Q_PAGE_PROGRAM_CMD:
            if (dev->count_byte_address < 3) {
                dev->address = (dev->address << 8) | rx_data;
                dev->count_byte_address++;
                dev->address &= 0x00FFFFFF;
            } else {
                dev->memory[dev->address + dev->rx_count++] = rx_data;
            }
            break;

        default:
            next_tx = dummy;
            break;
        }
    }

    // Chuẩn bị byte tiếp theo cho master
    HAL_SPI_TransmitReceive_IT(&hspi3, &next_tx, &dev->rx_data, 1);
}

void W25Q_PrepareData(W25Q_Slave *dev, uint32_t length)
{
	if (length > W25Q_MEMORY_SIZE) {
		length = W25Q_MEMORY_SIZE; // tránh tràn
	}
	memset(dev->memory, 0xFF, sizeof(dev->memory)); // data default trong memory
	for (uint32_t i = 0; i < length; i++) {
		dev->memory[i] = (uint8_t)(i & 0xFF); // dữ liệu tăng dần từ 0..255
	}
}

void HAL_SPI_TxRxCpltCallback(SPI_HandleTypeDef *hspi)
{
    if (hspi->Instance == SPI3) {
        W25Q_Slave_IRQHandler(&w25q, w25q.rx_data);
    }
}

void HAL_GPIO_EXTI_Callback(uint16_t GPIO_Pin)
{
    if (GPIO_Pin == GPIO_PIN_15) // NSS
    {
        if (HAL_GPIO_ReadPin(GPIOA, GPIO_PIN_15) == GPIO_PIN_RESET)
        {
            Reset_W25Q(&w25q);

            uint8_t tx = 0xFF; // preload dummy
            HAL_SPI_TransmitReceive_IT(&hspi3, &tx, &w25q.cmd, 1);
        }
    }
}
