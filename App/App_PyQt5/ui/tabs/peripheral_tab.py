import re
import time
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
                             QLabel, QSlider, QPushButton, QLineEdit, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QCheckBox, QGridLayout, 
                             QSplitter, QSpinBox)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor

class PeripheralTab(QWidget):
    def __init__(self, uart_dut=None, uart_hil=None):
        super().__init__()
        self.uart_dut = uart_dut
        self.uart_hil = uart_hil
        
        # Biến trạng thái cho bộ phân tích CAN (CAN Parser)
        self._is_reading_can = False
        self._temp_can_id = ""
        self._temp_can_data = []
        
        # Timer để tự động chốt dữ liệu CAN RX
        self._can_flush_timer = QTimer(self)
        self._can_flush_timer.setSingleShot(True) 
        self._can_flush_timer.timeout.connect(self._flush_can_data)

        # Mảng màu cho 5 bóng LED
        self.led_colors = ["#e74c3c", "#2ecc71", "#3498db", "#f1c40f", "#9b59b6"]
        self.led_ui_elements = [] 
        
        # Biến cờ kiểm tra tần số đã set chưa
        self._is_freq_set = False 

        # ==================================================
        # CHIA ĐÔI MÀN HÌNH BẰNG QSPLITTER
        # ==================================================
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        self.splitter = QSplitter(Qt.Horizontal)
        
        # --- CỘT TRÁI ---
        self.left_panel = QWidget()
        self.left_layout = QVBoxLayout(self.left_panel)
        self.left_layout.setContentsMargins(0, 0, 10, 0)
        
        # --- CỘT PHẢI ---
        self.right_panel = QWidget()
        self.right_layout = QVBoxLayout(self.right_panel)
        self.right_layout.setContentsMargins(0, 0, 0, 0)

        # Build UI
        self.build_left_panel()
        self.build_right_panel()

        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.right_panel)
        self.splitter.setSizes([400, 750]) 
        
        main_layout.addWidget(self.splitter)

        # Kết nối sự kiện UART LOG
        if self.uart_dut:
            self.uart_dut.log_signal.connect(self.parse_dut_log)
        if self.uart_hil:
            self.uart_hil.log_signal.connect(self.parse_hil_log)

    # ==================================================
    # BUILD CỘT TRÁI (CONTROL DESK)
    # ==================================================
    def build_left_panel(self):
        # --------------------------------------------------
        # 1. Khối Generator PWM
        # --------------------------------------------------
        pwm_group = QGroupBox("PWM Generator")
        pwm_layout = QVBoxLayout(pwm_group)
        
        # Tần số chung
        freq_layout = QHBoxLayout()
        freq_layout.addWidget(QLabel("Common Frequency (Hz):"))
        self.spin_pwm_freq = QSpinBox()
        self.spin_pwm_freq.setRange(1, 100000)
        self.spin_pwm_freq.setValue(1000)
        
        self.btn_set_freq = QPushButton("Set Freq")
        
        freq_layout.addWidget(self.spin_pwm_freq)
        freq_layout.addWidget(self.btn_set_freq)
        pwm_layout.addLayout(freq_layout)

        # 4 Kênh PWM
        self.pwm_sliders = []
        self.pwm_labels = []
        self.pwm_btns = [] 
        self.pwm_states = [False, False, False, False] 

        for i in range(4):
            row = QHBoxLayout()
            row.addWidget(QLabel(f"CH{i+1} Duty:"))
            
            slider = QSlider(Qt.Horizontal)
            slider.setRange(0, 100)
            slider.setValue(0)
            
            val_label = QLabel("0%")
            val_label.setFixedWidth(35)
            
            btn_toggle = QPushButton("Start")
            btn_toggle.setFixedWidth(60)
            # Khóa nút Start lúc ban đầu vì chưa set tần số
            btn_toggle.setEnabled(False)
            
            # Kết nối sự kiện
            slider.valueChanged.connect(lambda val, idx=i, lbl=val_label: self.on_pwm_duty_changed(idx, val, lbl))
            btn_toggle.clicked.connect(lambda checked, idx=i: self.on_pwm_toggle(idx))
            
            row.addWidget(slider)
            row.addWidget(val_label)
            row.addWidget(btn_toggle)
            
            self.pwm_sliders.append(slider)
            self.pwm_labels.append(val_label)
            self.pwm_btns.append(btn_toggle)
            pwm_layout.addLayout(row)
            
        self.left_layout.addWidget(pwm_group)
        self.btn_set_freq.clicked.connect(self.on_pwm_set_freq)

        # --------------------------------------------------
        # 2. Khối Gen Sine/Triangle Wave
        # --------------------------------------------------
        wave_group = QGroupBox("Waveform Generator")
        wave_layout = QVBoxLayout(wave_group)
        
        wfreq_layout = QHBoxLayout()
        wfreq_layout.addWidget(QLabel("Frequency (1-10000 Hz):"))
        self.spin_wave_freq = QSpinBox()
        self.spin_wave_freq.setRange(1, 10000)
        self.spin_wave_freq.setValue(1000)
        wfreq_layout.addWidget(self.spin_wave_freq)
        wave_layout.addLayout(wfreq_layout)

        btn_layout = QHBoxLayout()
        self.btn_gen_sine = QPushButton("Gen Sine")
        self.btn_gen_tri = QPushButton("Gen Triangle")
        self.btn_stop_wave = QPushButton("Stop Wave")
        self.btn_stop_wave.setEnabled(False) 
        
        btn_layout.addWidget(self.btn_gen_sine)
        btn_layout.addWidget(self.btn_gen_tri)
        btn_layout.addWidget(self.btn_stop_wave)
        wave_layout.addLayout(btn_layout)
        
        self.left_layout.addWidget(wave_group)

        # --------------------------------------------------
        # 3. Khối 5 bóng đèn LED
        # --------------------------------------------------
        led_group = QGroupBox("LED Control (5 Channels)")
        led_layout = QGridLayout(led_group)
        
        for i in range(5):
            lbl_name = QLabel(f"LED {i+1}")
            
            indicator = QLabel()
            indicator.setFixedSize(24, 24)
            indicator.setStyleSheet("background-color: #bdc3c7; border-radius: 12px; border: 1px solid #7f8c8d;")
            self.led_ui_elements.append(indicator)
            
            btn_on = QPushButton("ON")
            btn_off = QPushButton("OFF")
            btn_on.setFixedWidth(50)
            btn_off.setFixedWidth(50)
            
            btn_on.clicked.connect(lambda checked, idx=i: self.on_led_toggle(idx, True))
            btn_off.clicked.connect(lambda checked, idx=i: self.on_led_toggle(idx, False))
            
            led_layout.addWidget(lbl_name, i, 0)
            led_layout.addWidget(indicator, i, 1, alignment=Qt.AlignCenter)
            led_layout.addWidget(btn_on, i, 2)
            led_layout.addWidget(btn_off, i, 3)

        self.left_layout.addWidget(led_group)

        # --------------------------------------------------
        # 4. Khối ADC Reading
        # --------------------------------------------------
        adc_group = QGroupBox("ADC Reading (Potentiometer)")
        adc_layout = QVBoxLayout(adc_group)
        
        slider_row = QHBoxLayout()
        self.adc_slider = QSlider(Qt.Horizontal)
        self.adc_slider.setRange(0, 330)
        self.adc_slider.setValue(0)
        
        self.lbl_volt_set = QLabel("0.0 V")
        self.lbl_volt_set.setFixedWidth(45)
        
        slider_row.addWidget(self.adc_slider)
        slider_row.addWidget(self.lbl_volt_set)
        
        adc_layout.addWidget(QLabel("Set HIL Voltage:"))
        adc_layout.addLayout(slider_row)
        
        self.btn_read_adc = QPushButton("Read ADC from DUT")
        self.txt_result = QLineEdit()
        self.txt_result.setReadOnly(True)
        self.txt_result.setPlaceholderText("Waiting for DUT...")
        
        adc_layout.addWidget(self.btn_read_adc)
        adc_layout.addWidget(self.txt_result)
        
        self.left_layout.addWidget(adc_group)

        # --------------------------------------------------
        # 5. Khối CAN TX
        # --------------------------------------------------
        can_tx_group = QGroupBox("CAN Controller")
        can_tx_layout = QVBoxLayout(can_tx_group)
        
        self.txt_can_input = QLineEdit()
        self.txt_can_input.setPlaceholderText("String payload (e.g. Hello)")
        
        self.btn_can_str = QPushButton("Send String")
        self.btn_can_buf = QPushButton("Send 256-Byte Buffer")

        self.btn_can_read = QPushButton("Read CAN Buffer")
        
        can_tx_layout.addWidget(QLabel("Payload:"))
        can_tx_layout.addWidget(self.txt_can_input)
        can_tx_layout.addWidget(self.btn_can_str)
        can_tx_layout.addWidget(self.btn_can_buf)
        can_tx_layout.addWidget(self.btn_can_read)
        
        self.left_layout.addWidget(can_tx_group)
        self.left_layout.addStretch()

        # --- Gán sự kiện UI ---
        self.btn_gen_sine.clicked.connect(self.on_gen_sine)
        self.btn_gen_tri.clicked.connect(self.on_gen_tri)
        self.btn_stop_wave.clicked.connect(self.on_stop_wave)
        
        self.adc_slider.valueChanged.connect(self.on_adc_slider_changed)
        self.btn_read_adc.clicked.connect(self.on_read_adc_clicked)
        self.btn_can_str.clicked.connect(self.on_can_send_string)
        self.btn_can_buf.clicked.connect(self.on_can_send_buffer)
        self.btn_can_read.clicked.connect(self.on_can_read_manual) # Kích hoạt sự kiện Đọc

    # ==================================================
    # BUILD CỘT PHẢI (CAN MONITOR)
    # ==================================================
    def build_right_panel(self):
        can_rx_group = QGroupBox("CAN Traffic Monitor")
        can_rx_layout = QVBoxLayout(can_rx_group)
        
        toolbar = QHBoxLayout()
        self.btn_clear_log = QPushButton("Clear Log")
        
        toolbar.addStretch() # Đẩy nút Clear Log sát lề phải
        toolbar.addWidget(self.btn_clear_log)
        
        self.can_table = QTableWidget(0, 4)
        self.can_table.setHorizontalHeaderLabels(["Time", "Dir", "ID / Type", "Data Payload"])
        self.can_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.can_table.setColumnWidth(0, 80)
        self.can_table.setColumnWidth(1, 40)
        self.can_table.setColumnWidth(2, 90)
        self.can_table.verticalHeader().setVisible(False)
        self.can_table.setWordWrap(True) 

        can_rx_layout.addLayout(toolbar)
        can_rx_layout.addWidget(self.can_table)
        
        self.right_layout.addWidget(can_rx_group)

        self.btn_clear_log.clicked.connect(lambda: self.can_table.setRowCount(0))

    # ==================================================
    # LOGIC HÀM XỬ LÝ UART COMMANDS
    # ==================================================
    
    # --- LOGIC PWM ---
    def on_pwm_set_freq(self):
        if not self.uart_dut: return
        freq = self.spin_pwm_freq.value()
        self.uart_dut.send(f"pwm_set_freq {freq}")
        
        self._is_freq_set = True
        # Mở khóa toàn bộ các nút Start nếu chúng đang dừng
        for i in range(4):
            if not self.pwm_states[i]:
                self.pwm_btns[i].setEnabled(True)

    def on_pwm_toggle(self, ch_idx):
        if not self.uart_dut: return
        if not self._is_freq_set: return

        is_running = self.pwm_states[ch_idx]
        btn = self.pwm_btns[ch_idx]
        duty = self.pwm_sliders[ch_idx].value()
        channel = ch_idx + 1 

        if not is_running:
            self.uart_dut.send(f"pwm_set_duty_cycle {channel} {duty}")
            self.uart_dut.send(f"pwm_start {channel}")
            btn.setText("Stop")
            self.pwm_states[ch_idx] = True
        else:
            self.uart_dut.send(f"pwm_stop {channel}")
            btn.setText("Start")
            self.pwm_states[ch_idx] = False

        # Kiểm tra xem có kênh nào đang chạy không
        is_any_running = any(self.pwm_states)
        
        # Khóa/Mở khóa việc set tần số
        self.btn_set_freq.setEnabled(not is_any_running)
        self.spin_pwm_freq.setEnabled(not is_any_running)

    def on_pwm_duty_changed(self, ch_idx, value, label_widget):
        label_widget.setText(f"{value}%")
        if self.pwm_states[ch_idx] and self.uart_dut:
            channel = ch_idx + 1
            self.uart_dut.send(f"pwm_set_duty_cycle {channel} {value}")

    # --- LOGIC WAVE ---
    def on_gen_sine(self):
        self.btn_gen_sine.setEnabled(False)
        self.btn_gen_tri.setEnabled(False)
        self.btn_stop_wave.setEnabled(True)
        freq = self.spin_wave_freq.value()
        # TODO: Điền command gen sine

    def on_gen_tri(self):
        self.btn_gen_sine.setEnabled(False)
        self.btn_gen_tri.setEnabled(False)
        self.btn_stop_wave.setEnabled(True)
        freq = self.spin_wave_freq.value()
        # TODO: Điền command gen triangle

    def on_stop_wave(self):
        self.btn_gen_sine.setEnabled(True)
        self.btn_gen_tri.setEnabled(True)
        self.btn_stop_wave.setEnabled(False)
        # TODO: Điền command stop wave

    # --- LOGIC LED ---
    def on_led_toggle(self, led_idx, is_on):
        indicator = self.led_ui_elements[led_idx]
        if is_on:
            color = self.led_colors[led_idx]
            indicator.setStyleSheet(f"background-color: {color}; border-radius: 12px; border: 1px solid #7f8c8d;")
        else:
            indicator.setStyleSheet("background-color: #bdc3c7; border-radius: 12px; border: 1px solid #7f8c8d;")
        #TODO: Gửi command LED tương ứng

    # --- LOGIC ADC ---
    def on_adc_slider_changed(self, value):
        volt = value / 100.0
        self.lbl_volt_set.setText(f"{volt:.1f} V")
        
    def on_read_adc_clicked(self):
        if not self.uart_hil or not self.uart_dut: return
        volt = self.adc_slider.value() / 100.0
        self.uart_hil.send(f"dac_set_voltage {volt:.1f}")
        self.txt_result.setText("Reading from DUT...")
        QTimer.singleShot(200, lambda: self.uart_dut.send("adc_read"))

    # --- LOGIC CAN ---
    def on_can_send_string(self):
        if not self.uart_hil: return
        payload = self.txt_can_input.text().strip()
        if payload:
            self.add_can_row("TX", "String", payload)
            self.uart_hil.send(f"can_send_string {payload}")
            self.txt_can_input.clear()

    def on_can_send_buffer(self):
        if not self.uart_hil: return
        self.add_can_row("TX", "Buffer", "Sending 256-byte internal sequence...")
        self.uart_hil.send("can_send_buffer")

    def on_can_read_manual(self):
        if not self.uart_hil: return
        self.uart_hil.send("can_read")

    # ==================================================
    # CAN PARSING & LOGGING
    # ==================================================
    def parse_dut_log(self, text):
        if "Voltage:" in text:
            try:
                val_str = text.split("Voltage:")[1].strip()
                self.txt_result.setText(f"{val_str}")
            except Exception:
                pass

    def parse_hex_to_ascii(self, hex_string):
        ascii_chars = []
        for h in hex_string.split():
            try:
                val = int(h, 16)
                if 32 <= val <= 126:
                    ascii_chars.append(chr(val))
                else:
                    ascii_chars.append('.') 
            except ValueError:
                pass
        return "".join(ascii_chars)

    def add_can_row(self, direction, can_id, payload):
        row = self.can_table.rowCount()
        self.can_table.insertRow(row)
        
        t_str = time.strftime("%H:%M:%S")
        display_text = payload
        
        if direction == "RX" and all(c in "0123456789abcdefABCDEF \n" for c in payload):
            ascii_preview = self.parse_hex_to_ascii(payload)
            display_text = f"[HEX]   {payload}\n[ASCII] {ascii_preview}"

        item_time = QTableWidgetItem(t_str)
        item_dir = QTableWidgetItem(direction)
        item_id = QTableWidgetItem(can_id)
        item_data = QTableWidgetItem(display_text)
        
        color = QColor("#d35400") if direction == "TX" else QColor("#2980b9")
        item_dir.setForeground(color)
        item_dir.setFont(item_time.font()) 
        
        for item in [item_time, item_dir, item_id]:
            item.setTextAlignment(Qt.AlignCenter)
            
        self.can_table.setItem(row, 0, item_time)
        self.can_table.setItem(row, 1, item_dir)
        self.can_table.setItem(row, 2, item_id)
        self.can_table.setItem(row, 3, item_data)
        
        self.can_table.resizeRowToContents(row)
        self.can_table.scrollToBottom()

    def _flush_can_data(self):
        """Hàm này được gọi bởi QTimer khi mạch HIL ngừng gửi dữ liệu CAN RX trong 100ms"""
        if self._is_reading_can and self._temp_can_data:
            self._is_reading_can = False
            full_payload = " ".join(self._temp_can_data)
            self.add_can_row("RX", self._temp_can_id, full_payload)
            self._temp_can_data = [] 
        
    def parse_hil_log(self, text):
        text = text.strip()
        if not text: return

        if "DUT ID:" in text:
            self._temp_can_id = text.split(":")[1].strip()
            self._temp_can_data = []
            self._is_reading_can = True
            
            self._can_flush_timer.start(100) 
            return

        if self._is_reading_can:
            if "Data:" in text: return 
            
            is_hex = bool(re.match(r'^([0-9A-Fa-f]{2}\s*)+$', text))
            if is_hex or text.replace(" ", "").isalnum(): 
                self._temp_can_data.append(text)
                self._can_flush_timer.start(100) 
            else:
                self._can_flush_timer.stop()
                self._flush_can_data()
