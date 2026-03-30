from robot.api.deco import library, keyword
from robot.api import logger
from cli_lib import CLI
import re
from robot.libraries.BuiltIn import BuiltIn
import numpy as np

@library(scope="GLOBAL")
class Logic_Library:
    """
    Robot Library for Logic Analyzer
    """

    def __init__(self):
        self.cli = CLI()

    # ------------------
    # Connection
    # ------------------
    @keyword("Connect Logic Analyzer")
    def connect_la(self, port, baud=115200):
        self.cli.connect(port, baud)

    @keyword("Disconnect Logic Analyzer")
    def disconnect_la(self):
        self.cli.disconnect()

    @keyword("Setup Logic Analyzer")
    # Keyword này hiện tại được dùng để debug từng bước
    # Sau này có thể setup luôn trong "Read Logic Analyzer Data"
    # TODO: Không expose keyword này cho user
    def setup_la(self, rate, samples):
        self.cli.setup_logic_analyzer(rate, samples)
        logger.info(f"Logic Analyzer setup: samples={samples}, rate={rate} Hz")
    
    @keyword("Read Logic Analyzer Data")
    def read_la_data(self):
        data = self.cli.capture_binary_stream(timeout_sec=12.0)
        logger.info(f"Logic Analyzer data length: {len(data)} bytes")
        return data

    @keyword("Verify Sine Wave")
    def verify_analog_is_sine_wave(self, raw_data: bytes, expected_freq_hz=None):
        sample_rate = 250000
        snr_threshold = 300

        # 1. Chuyển đổi dữ liệu thô sang mảng Numpy
        arr = np.frombuffer(raw_data, dtype=np.uint8)
        
        # Bỏ byte cuối cùng nếu tổng số byte bị lẻ (đảm bảo chẵn cặp Digital/Analog)
        if len(arr) % 2 != 0:
            arr = arr[:-1]

        if len(arr) < 500:
            raise ValueError("FAIL: Dữ liệu quá ngắn (< 500 byte) để chạy phân tích FFT.")

        # 2. Tách kênh Analog (nằm ở các index lẻ: 1, 3, 5...) và giải mã điện áp 7-bit
        analog_bytes = arr[1::2]
        voltages = (analog_bytes & 0x7F) * (3.3 / 127.0)

        # 3. Tiền xử lý tín hiệu
        # Bỏ thành phần DC (dịch tâm sóng về 0V) để đồ thị FFT không bị vọt lên ở mốc 0Hz
        voltages_no_dc = voltages - np.mean(voltages)
        
        # Áp dụng hàm cửa sổ Hanning (Windowing) để làm mượt hai đầu mảng sóng, giảm rò rỉ phổ
        window = np.hanning(len(voltages_no_dc))
        voltages_windowed = voltages_no_dc * window

        # 4. Chạy thuật toán FFT và tính NĂNG LƯỢNG (Bình phương biên độ)
        fft_values = np.fft.rfft(voltages_windowed)
        fft_power = np.abs(fft_values) ** 2  # <-- FIX 1: Bình phương để lấy Power
        freqs = np.fft.rfftfreq(len(voltages_windowed), d=1.0/sample_rate)

        # 5. Phân tích năng lượng để tìm sóng Sine
        peak_idx = np.argmax(fft_power)
        peak_freq = freqs[peak_idx]

        window_size = 5  # Lấy 5 vạch bên trái và 5 vạch bên phải đỉnh chính
        start_idx = max(0, peak_idx - window_size)
        end_idx = min(len(fft_power), peak_idx + window_size + 1)

        # Tổng năng lượng của Tín hiệu chính
        peak_energy = np.sum(fft_power[start_idx:end_idx])

        # Tính tổng năng lượng của Rác (sau khi đã đào bỏ vùng tín hiệu chính)
        fft_power[start_idx:end_idx] = 0 
        noise_energy = np.sum(fft_power) + 1e-9  # Cộng 1e-9 chống lỗi chia 0

        # Tính tỷ lệ Tín hiệu trên Nhiễu (SNR) bằng năng lượng
        snr_ratio = peak_energy / noise_energy
        
        # Nếu tỷ lệ áp đảo rác => Sóng Sine
        is_sine = bool(snr_ratio >= snr_threshold)
        
        # Tính thêm V_Peak_to_Peak để báo cáo cho đẹp
        v_pp = np.max(voltages) - np.min(voltages)

        # 6. Log kết quả ra Console của Robot Framework
        logger.info(f"--- ANALOG ANALYSIS ---")
        logger.info(f"Measured Freq: {peak_freq:.2f} Hz")
        logger.info(f"Vpp: {v_pp:.2f} V")
        logger.info(f"SNR Ratio: {snr_ratio:.2f} (Threshold: {snr_threshold})")
        logger.info(f"Is Sine Wave: {is_sine}")

        if not is_sine:
            # Nếu SNR quá thấp, ném ra lỗi. Robot Framework sẽ bắt lỗi này và đánh Fail test case!
            raise AssertionError(
                f"Analog signal is not a Sine wave! "
                f"(SNR Ratio = {snr_ratio:.2f}). "
                f"Frequency of noise detected: {peak_freq:.2f} Hz."
            )

        if expected_freq_hz is not None:
            expected_freq_hz = float(expected_freq_hz) # Ép kiểu
            
            # Tính toán sai số 5%
            lower_bound = expected_freq_hz * 0.95
            upper_bound = expected_freq_hz * 1.05

            if not (lower_bound <= peak_freq <= upper_bound):
                raise AssertionError(
                    f"FAIL: Tín hiệu LÀ sóng Sine nhưng SAI tần số! "
                    f"Mong đợi: {expected_freq_hz} Hz (\u00B15%). Đo được thực tế: {peak_freq:.2f} Hz."
                )
        return is_sine
