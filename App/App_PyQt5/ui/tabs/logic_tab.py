# File: ui/tabs/logic_tab.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton, QLabel, QComboBox
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor
import pyqtgraph as pg
import time
import numpy as np

# ==================================================
# CLASS TẠO LABEL KÊNH BẰNG THUẦN PYTHON (KHÔNG HTML)
# ==================================================
class ChannelLabel(pg.LabelItem):
    def __init__(self, text, bg_color):
        # Khởi tạo LabelItem cơ bản với chữ trắng, in đậm
        super().__init__(text=text, color='w', bold=True)
        self.bg_color = QColor(bg_color)
        
        # Cố định chiều rộng để các khung đều nhau
        self.setFixedWidth(40)
        
    def paint(self, p, *args):
        # 1. Vẽ khung nền (Background) trước
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(self.bg_color)
        
        # Lấy kích thước thực tế của vùng chứa nhãn và tạo viền bo góc
        rect = self.boundingRect().adjusted(2, 2, -2, -2)
        p.drawRoundedRect(rect, 3, 3)
        
        # 2. Gọi hàm vẽ chữ mặc định đè lên trên nền
        super().paint(p, *args)

class LogicTab(QWidget):
    def __init__(self, uart_logic):
        super().__init__()
        
        self.uart_logic = uart_logic
        self.is_running = False

        # --- BỘ ĐỆM VÀ QUẢN LÝ DỮ LIỆU ---
        self.raw_buffer = bytearray()
        self.leftover_byte = bytearray() # Lưu byte bị kẹt lại chưa có cặp
        self.current_idx = 0 # Con trỏ mảng hiện tại
        
        self.current_sample_rate = 100000
        self.expected_samples = 0
        
        self.plot_timer = QTimer()
        self.plot_timer.timeout.connect(self.update_plots)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.build_control_panel())
        main_layout.addWidget(self.build_plot_area())

    # ==================================================
    # VẼ ĐÈN LED CHO NÚT BẤM
    # ==================================================
    def create_led_icon(self, color_hex):
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.transparent) 
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing) 
        painter.setBrush(QColor(color_hex))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(2, 2, 12, 12) 
        painter.end()
        
        return QIcon(pixmap)

    def build_control_panel(self):
        box = QGroupBox("Sampling Controls")
        layout = QHBoxLayout(box)
        layout.setContentsMargins(10, 10, 10, 10)

        # --- NÚT START / STOP VỚI ĐÈN LED ---
        self.btn_start = QPushButton(" START")
        self.btn_start.setMinimumWidth(100)
        self.btn_start.setStyleSheet("font-weight: bold; padding: 5px;")
        self.btn_start.setIcon(self.create_led_icon("gray"))
        self.btn_start.clicked.connect(self.toggle_start_stop)
        
        layout.addWidget(self.btn_start)
        layout.addSpacing(20)

        # --- CẤU HÌNH SAMPLES ---
        self.cb_samples = QComboBox()
        self.cb_samples.addItems(["10 K", "100 K", "500 K", "1 M", "3 M", "10 M", "50 M", "100 M"])
        self.cb_samples.setCurrentText("1 M")

        layout.addWidget(QLabel("Samples:"))
        layout.addWidget(self.cb_samples)
        layout.addSpacing(20)
        
        # --- CẤU HÌNH SAMPLE RATE ---
        self.cb_rate = QComboBox()
        self.cb_rate.addItems(["10 kHz", "100 kHz", "150 kHz", "200 kHz", "250 kHz", "300 kHz"])
        self.cb_rate.setCurrentText("100 kHz")

        layout.addWidget(QLabel("Sample Rate:"))
        layout.addWidget(self.cb_rate)

        # Đẩy tất cả sang trái
        layout.addStretch() 

        return box

    def build_plot_area(self):
        self.plot_widget = pg.GraphicsLayoutWidget()
        self.plot_widget.setBackground('#FFFFFF') 
        
        # Xóa khoảng cách giữa các đồ thị
        self.plot_widget.ci.layout.setSpacing(0)
        self.plot_widget.ci.layout.setContentsMargins(0, 0, 0, 0)

        channels = ['D0', 'D1', 'D2', 'D3', 'A0']
        
        colors = {
            'D0': '#333333', 'D1': '#8B4513', 'D2': '#DC143C', 
            'D3': '#D2691E', 'A0': '#4682B4'
        }

        self.plots = {}
        self.curves = {} # [UPDATE] Chuẩn bị sẵn dictionary chứa đường vẽ đồ thị
        self.v_lines = []
        p0 = None

        for i, ch in enumerate(channels):
            # 1. Label Tên kênh bằng Class ChannelLabel (Thuần Python)
            lbl = ChannelLabel(ch, colors[ch])
            self.plot_widget.addItem(lbl, col=0)

            # 2. Biểu đồ (Plot)
            p = self.plot_widget.addPlot(col=1)
            
            # ==========================================
            # TỐI ƯU HÓA PYQTGRAPH CHO LOGIC ANALYZER
            # ==========================================
            p.setClipToView(True) # Chỉ vẽ những điểm nằm trong khung hình hiện tại
            p.setDownsampling(auto=True, mode='peak') # Ghép điểm ảnh, loại bỏ lag
            
            p.getViewBox().setBorder(pg.mkPen(color='#CCCCCC', width=1))

            p.hideButtons()
            
            p.hideAxis('left')
            p.setMouseEnabled(y=False) 
            
            if ch.startswith('D'):
                p.setYRange(-0.2, 1.2, padding=0)
            else:
                p.setYRange(0, 3.5, padding=0)

            if i == 0:
                p0 = p
                p.showAxis('top')    
                p.hideAxis('bottom')
                p.setXRange(0, 100) 
            else:
                p.showAxis('bottom') 
                p.getAxis('bottom').setStyle(showValues=False) 
                p.getAxis('bottom').setHeight(0)               
                p.setXLink(p0)       

            p.showGrid(x=True, y=False, alpha=0.3)

            if i % 2 == 0 and ch.startswith('D'):
                p.getViewBox().setBackgroundColor('#F7F7F7')

            # [UPDATE] Khởi tạo sẵn đường nét để xóa/vẽ data
            curve = p.plot(pen=pg.mkPen(color=colors[ch], width=1.5))
            self.curves[ch] = curve

            v_line = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen(color='#444444', width=1, style=Qt.DashLine))
            p.addItem(v_line)
            self.v_lines.append(v_line)

            self.plots[ch] = p
            self.plot_widget.nextRow()
            
        self.proxy = pg.SignalProxy(self.plot_widget.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved)

        return self.plot_widget

    # ==================================================
    # SỰ KIỆN RÊ CHUỘT CROSSHAIR 
    # ==================================================
    def mouseMoved(self, evt):
        pos = evt[0]  
        for ch, p in self.plots.items():
            if p.sceneBoundingRect().contains(pos):
                mousePoint = p.vb.mapSceneToView(pos)
                for v_line in self.v_lines:
                    v_line.setPos(mousePoint.x())
                break 

    # ==================================================
    # TIẾP NHẬN VÀ XỬ LÝ DỮ LIỆU TỐI ƯU HÓA (O(N))
    # ==================================================
    def process_raw_data(self, data: bytes):
        if self.is_running:
            self.raw_buffer.extend(data)

    def update_plots(self):
        # Nếu không có data mới, thoát sớm để rảnh CPU
        if len(self.raw_buffer) == 0 and len(self.leftover_byte) == 0:
            return

        # Nối data cũ bị lẻ nhịp trước vào đầu chuỗi mới
        chunk = self.leftover_byte + self.raw_buffer[:]
        self.raw_buffer.clear()

        valid_data = np.frombuffer(chunk, dtype=np.uint8)
        valid_data = valid_data[valid_data >= 0x80] # Loại rác

        if len(valid_data) == 0:
            self.leftover_byte.clear()
            return

        # CỰC KỲ QUAN TRỌNG: Xử lý byte bị lẻ cặp (tránh lệch Digital/Analog)
        if len(valid_data) % 2 != 0:
            self.leftover_byte = bytearray([valid_data[-1]])
            valid_data = valid_data[:-1]
        else:
            self.leftover_byte.clear()

        if len(valid_data) == 0:
            return

        # Tách cặp và tính số lượng
        digital_bytes = valid_data[0::2]
        analog_bytes = valid_data[1::2]
        n_samples = len(digital_bytes)

        # Chặn không cho mảng phình to hơn số Sample User đã chọn
        if self.current_idx + n_samples > self.expected_samples:
            n_samples = self.expected_samples - self.current_idx
            digital_bytes = digital_bytes[:n_samples]
            analog_bytes = analog_bytes[:n_samples]

        start_i = self.current_idx
        end_i = start_i + n_samples

        # Đổ dữ liệu vào đúng vị trí của Mảng đã cấp phát sẵn (Nhanh gấp 100 lần list thường)
        self.d0_arr[start_i:end_i] = digital_bytes & 1
        self.d1_arr[start_i:end_i] = (digital_bytes >> 1) & 1
        self.d2_arr[start_i:end_i] = (digital_bytes >> 2) & 1
        self.d3_arr[start_i:end_i] = (digital_bytes >> 3) & 1
        self.a0_arr[start_i:end_i] = (analog_bytes & 0x7F) * (3.3 / 127.0)

        # Chỉ vẽ từ 0 tới điểm đang quét hiện tại
        self.curves['D0'].setData(self.time_arr[:end_i], self.d0_arr[:end_i])
        self.curves['D1'].setData(self.time_arr[:end_i], self.d1_arr[:end_i])
        self.curves['D2'].setData(self.time_arr[:end_i], self.d2_arr[:end_i])
        self.curves['D3'].setData(self.time_arr[:end_i], self.d3_arr[:end_i])
        self.curves['A0'].setData(self.time_arr[:end_i], self.a0_arr[:end_i])

        self.current_idx = end_i

        # Tự động trượt thanh ngắm
        if end_i > 0:
            current_time = self.time_arr[end_i - 1]
            self.plots['D0'].setXRange(0, max(current_time, 0.0001), padding=0)

        # Kiểm tra hoàn thành
        if self.current_idx >= self.expected_samples:
            print(f"[LOGIC] Đã bắt đủ {self.current_idx} mẫu. Tự động Dừng.")
            self.toggle_start_stop()

    # ==================================================
    # [UPDATE] HÀM HỖ TRỢ XỬ LÝ LỆNH START/STOP
    # ==================================================
    def parse_number_value(self, text, multipliers):
        """Chuyển đổi text combobox ('1 M', '100 kHz') thành số thực tế"""
        text = text.replace(" ", "").upper()
        for suffix, mult in multipliers.items():
            if suffix in text:
                return int(float(text.replace(suffix, "")) * mult)
        return int(text)

    def reset_plots_to_zero(self):
        """Xóa hết dữ liệu cũ và ép trục thời gian về lại mốc 0"""
        for ch in self.curves:
            self.curves[ch].setData([], []) 
        
        if 'D0' in self.plots:
            self.plots['D0'].setXRange(0, 100, padding=0)

    # ==================================================
    # SỰ KIỆN NÚT BẤM (GỬI LỆNH)
    # ==================================================
    def toggle_start_stop(self):
        if getattr(self.uart_logic, 'ser', None) is None or not self.uart_logic.ser.is_open:
            print("[LOGIC] Cổng COM chưa được kết nối!")
            return

        if not self.is_running:
            self.is_running = True
            self.btn_start.setText(" STOP")
            self.btn_start.setIcon(self.create_led_icon("#4CAF50")) 

            rate = self.parse_number_value(self.cb_rate.currentText(), {"KHZ": 1000, "MHZ": 1000000})
            samples = self.parse_number_value(self.cb_samples.currentText(), {"K": 1000, "M": 1000000, "G": 1000000000})

            # RESET BIẾN TRẠNG THÁI
            self.current_sample_rate = rate
            self.expected_samples = samples
            self.raw_buffer.clear()
            self.leftover_byte.clear()
            self.current_idx = 0
            self.reset_plots_to_zero()
            
            # ------------------------------------------------
            # TIỀN CẤP PHÁT BỘ NHỚ (NGUYÊN LÝ VÀNG CHỐNG LAG)
            # ------------------------------------------------
            self.d0_arr = np.zeros(samples, dtype=np.int8)
            self.d1_arr = np.zeros(samples, dtype=np.int8)
            self.d2_arr = np.zeros(samples, dtype=np.int8)
            self.d3_arr = np.zeros(samples, dtype=np.int8)
            self.a0_arr = np.zeros(samples, dtype=np.float32)
            
            dt = 1.0 / rate
            self.time_arr = np.arange(samples) * dt
            
            self.plot_timer.start(100) 

            try:
                # 1. Reset state
                self.uart_logic.ser.write(b"*")
                time.sleep(0.01) # Nghỉ 50ms cho Pico reset DMA
                
                # 2. Setup kênh
                self.uart_logic.ser.write(b"A10\n")
                time.sleep(0.01)
                self.uart_logic.ser.write(b"D10\n")
                time.sleep(0.01)
                self.uart_logic.ser.write(b"D11\n")
                time.sleep(0.01)
                self.uart_logic.ser.write(b"D12\n")
                time.sleep(0.01)
                self.uart_logic.ser.write(b"D13\n")
                time.sleep(0.01)
                
                # 3. Setup tham số
                self.uart_logic.ser.write(f"R{rate}\n".encode('ascii'))
                time.sleep(0.01)
                self.uart_logic.ser.write(f"L{samples}\n".encode('ascii'))
                time.sleep(0.01)
                
                # Để test tạm thời tránh Python bị kẹt `readline()`, 
                # bạn phải XÓA/FLUSH buffer RX cũ trước khi ra lệnh START
                self.uart_logic.ser.reset_input_buffer()
                
                # 4. Gửi lệnh chốt (Bắn Data)
                self.uart_logic.ser.write(b"F\n")

                print(f"[LOGIC] Bắt đầu: Setup {samples} samples @ {rate} Hz")
            except Exception as e:
                print(f"[LOGIC] Lỗi gửi lệnh START: {e}")
                self.is_running = False
                self.btn_start.setText(" START")
                self.btn_start.setIcon(self.create_led_icon("gray"))
                self.plot_timer.stop()

        else:
            self.is_running = False
            self.btn_start.setText(" START")
            self.btn_start.setIcon(self.create_led_icon("gray"))
            
            self.plot_timer.stop()
            self.update_plots() 
            
            try:
                self.uart_logic.ser.write(b"+")
                print("[LOGIC] Đã gửi lệnh STOP.")
            except Exception as e:
                print(f"[LOGIC] Lỗi gửi lệnh STOP: {e}")

