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
        
        # Biến cờ kiểm tra tần số PWM đã set chưa
        self._is_freq_set = False 
        
        # Biến trạng thái cho Waveform Generator
        self._wave_running = "NONE" # "NONE", "SINE", "TRIANGLE"

        # Biến lưu lại index của LED đang chờ HIL đọc phản hồi
        self._pending_led_idx = None

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
        self.splitter.setSizes([500, 650]) 
        
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
        self.spin_pwm_freq.setRange(1, 1000000)
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
        
        # Tạo 2 nút Start độc lập
        self.btn_wave_sine = QPushButton("Start Sine")
        
        self.btn_wave_tri = QPushButton("Start Triangle")
        
        btn_layout.addWidget(self.btn_wave_sine)
        btn_layout.addWidget(self.btn_wave_tri)
        wave_layout.addLayout(btn_layout)
        
        self.left_layout.addWidget(wave_group)

        # Gán sự kiện cho 2 nút Wave
        self.btn_wave_sine.clicked.connect(self.on_toggle_sine)
        self.btn_wave_tri.clicked.connect(self.on_toggle_tri)

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
        self.adc_slider.valueChanged.connect(self.on_adc_slider_changed)
        self.btn_read_adc.clicked.connect(self.on_read_adc_clicked)
        self.btn_can_str.clicked.connect(self.on_can_send_string)
        self.btn_can_buf.clicked.connect(self.on_can_send_buffer)
        self.btn_can_read.clicked.connect(self.on_can_read_manual)

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

        self.can_table = QTableWidget(0, 5)
        self.can_table.setHorizontalHeaderLabels(["Time", "Dir", "ID / Type", "HEX Data", "ASCII Parse"])
        self.can_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.can_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        
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
        if not self.uart_hil: return
        freq = self.spin_pwm_freq.value()
        self.uart_hil.send(f"pwm_set_freq {freq}")
        
        self._is_freq_set = True
        # Mở khóa toàn bộ các nút Start nếu chúng đang dừng
        for i in range(4):
            if not self.pwm_states[i]:
                self.pwm_btns[i].setEnabled(True)

    def on_pwm_toggle(self, ch_idx):
        if not self.uart_hil: return
        if not self._is_freq_set: return

        is_running = self.pwm_states[ch_idx]
        btn = self.pwm_btns[ch_idx]
        duty = self.pwm_sliders[ch_idx].value()
        channel = ch_idx + 1 

        if not is_running:
            self.uart_hil.send(f"pwm_set_duty_cycle {channel} {duty}")
            self.uart_hil.send(f"pwm_start {channel}")
            btn.setText("Stop")
            self.pwm_states[ch_idx] = True
        else:
            self.uart_hil.send(f"pwm_stop {channel}")
            btn.setText("Start")
            self.pwm_states[ch_idx] = False

        # Kiểm tra xem có kênh nào đang chạy không
        is_any_running = any(self.pwm_states)
        
        # Khóa/Mở khóa việc set tần số
        self.btn_set_freq.setEnabled(not is_any_running)
        self.spin_pwm_freq.setEnabled(not is_any_running)

    def on_pwm_duty_changed(self, ch_idx, value, label_widget):
        label_widget.setText(f"{value}%")
        if self.pwm_states[ch_idx] and self.uart_hil:
            channel = ch_idx + 1
            self.uart_hil.send(f"pwm_set_duty_cycle {channel} {value}")

    # --- LOGIC WAVE ---
    def on_toggle_sine(self):
        freq = self.spin_wave_freq.value()
        
        if self._wave_running == "NONE":
            # Đang dừng -> Chạy Sine
            # Kiểm tra tần số nằm trong range 1-10000
            if 1 <= freq <= 10000:
                if self.uart_hil:
                    self.uart_hil.send(f"set_freq {freq}")
                    self.uart_hil.send("sine_wave 1")
                
                self._wave_running = "SINE"
                self.btn_wave_sine.setText("Stop Sine")
                
                # Khóa nút Triangle
                self.btn_wave_tri.setEnabled(False)
                
                # Khóa Spinbox Tần số (Không cho đổi khi đang chạy)
                self.spin_wave_freq.setEnabled(False)
            
        elif self._wave_running == "SINE":
            # Đang chạy Sine -> Dừng
            if self.uart_hil:
                self.uart_hil.send("sine_wave 0")
            
            self._wave_running = "NONE"
            self.btn_wave_sine.setText("Start Sine")
            
            # Mở khóa nút Triangle
            self.btn_wave_tri.setEnabled(True)
            
            # Mở khóa Spinbox Tần số
            self.spin_wave_freq.setEnabled(True)

    def on_toggle_tri(self):
        freq = self.spin_wave_freq.value()
        
        if self._wave_running == "NONE":
            # Đang dừng -> Chạy Triangle
            # Kiểm tra tần số nằm trong range 1-10000
            if 1 <= freq <= 10000:
                if self.uart_hil:
                    self.uart_hil.send(f"set_freq {freq}")
                    self.uart_hil.send("triangle_wave 1")
                
                self._wave_running = "TRIANGLE"
                self.btn_wave_tri.setText("Stop Triangle")
                
                # Khóa nút Sine
                self.btn_wave_sine.setEnabled(False)
                
                # Khóa Spinbox Tần số
                self.spin_wave_freq.setEnabled(False)
            
        elif self._wave_running == "TRIANGLE":
            # Đang chạy Triangle -> Dừng
            if self.uart_hil:
                self.uart_hil.send("triangle_wave 0")
            
            self._wave_running = "NONE"
            self.btn_wave_tri.setText("Start Triangle")
            
            # Mở khóa nút Sine
            self.btn_wave_sine.setEnabled(True)
            
            # Mở khóa Spinbox Tần số
            self.spin_wave_freq.setEnabled(True)

    # --- LOGIC LED ---
    def on_led_toggle(self, led_idx, is_on):
        if not self.uart_dut or not self.uart_hil: return
        
        # 1. Gửi lệnh set_led cho DUT (index DUT từ 1 đến 5)
        dut_index = led_idx + 1
        state_val = 1 if is_on else 0
        self.uart_dut.send(f"set_led {dut_index} {state_val}")
        
        # Ghi nhớ lại bóng đèn đang thao tác để chờ HIL phản hồi
        self._pending_led_idx = led_idx
        
        # 2 & 3. Delay 50ms, sau đó yêu cầu HIL đọc port e (pin HIL từ 0 đến 4)
        hil_pin = led_idx
        QTimer.singleShot(50, lambda: self.uart_hil.send(f"gpio_read e {hil_pin}"))

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
        
        # Biến chứa data
        display_hex = payload
        display_ascii = ""
        
        # Phân loại data để cho vào đúng cột
        # Nếu payload toàn mã Hex -> đưa vào cột HEX, dịch ra cột ASCII
        if all(c in "0123456789abcdefABCDEF \n" for c in payload) and payload.strip():
            display_ascii = self.parse_hex_to_ascii(payload)
        # Nếu đang gửi String trực tiếp -> đưa vào cột ASCII, để trống cột HEX
        elif can_id == "String": 
            display_ascii = payload
            display_hex = ""

        # Tạo 5 item cho 5 cột
        item_time = QTableWidgetItem(t_str)
        item_dir = QTableWidgetItem(direction)
        item_id = QTableWidgetItem(can_id)
        item_hex = QTableWidgetItem(display_hex)
        item_ascii = QTableWidgetItem(display_ascii)
        
        color = QColor("#d35400") if direction == "TX" else QColor("#2980b9")
        item_dir.setForeground(color)
        item_dir.setFont(item_time.font()) 
        
        for item in [item_time, item_dir, item_id]:
            item.setTextAlignment(Qt.AlignCenter)
            
        # Nạp 5 item vào đúng các cột
        self.can_table.setItem(row, 0, item_time)
        self.can_table.setItem(row, 1, item_dir)
        self.can_table.setItem(row, 2, item_id)
        self.can_table.setItem(row, 3, item_hex)
        self.can_table.setItem(row, 4, item_ascii)
        
        self.can_table.resizeRowToContents(row)
        self.can_table.scrollToBottom()

    def _flush_can_data(self):
        if self._is_reading_can and self._temp_can_data:
            self._is_reading_can = False
            full_payload = " ".join(self._temp_can_data)
            self.add_can_row("RX", self._temp_can_id, full_payload)
            self._temp_can_data = [] 
        
    def parse_hil_log(self, text):
        text = text.strip()
        if not text: return

        if "GPIO =" in text and getattr(self, '_pending_led_idx', None) is not None:
            try:
                # Bóc tách data GPIO
                val_str = text.split("GPIO =")[1].strip()
                val = int(val_str)
                
                idx = self._pending_led_idx
                indicator = self.led_ui_elements[idx]
                
                # Nếu là 1 thì sáng đèn theo màu chỉ định, 0 thì màu xám (tắt)
                if val == 1:
                    color = self.led_colors[idx]
                    indicator.setStyleSheet(f"background-color: {color}; border-radius: 12px; border: 1px solid #7f8c8d;")
                else:
                    indicator.setStyleSheet("background-color: #bdc3c7; border-radius: 12px; border: 1px solid #7f8c8d;")
                
                # Reset lại cờ sau khi xử lý xong
                self._pending_led_idx = None
            except Exception:
                pass
            return # Tránh chạy tiếp xuống phần parse CAN bên dưới

        if "DUT ID:" in text:
            self._temp_can_id = text.split(":")[1].strip()
            self._temp_can_data = []
            self._is_reading_can = True
            
            self._can_flush_timer.start(100) 
            return

        if self._is_reading_can:
            if "Data:" in text: return 
            
            if text == "OK":
                self._can_flush_timer.stop()
                self._flush_can_data()
                return
            
            is_hex = bool(re.match(r'^([0-9A-Fa-f]{2}\s*)+$', text))
            if is_hex or text.replace(" ", "").isalnum(): 
                self._temp_can_data.append(text)
                self._can_flush_timer.start(100) 
            else:
                self._can_flush_timer.stop()
                self._flush_can_data()
