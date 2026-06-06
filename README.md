# Điều Khiển Đèn Thông Minh Bằng Giọng Nói Ngoại Tuyến (TinyML Audio-KWS)

Dự án nghiên cứu và triển khai hệ thống nhận diện từ khóa giọng nói (**Audio Keyword Spotting - KWS**) hoạt động ngoại tuyến (**100% offline**) trực tiếp trên vi điều khiển **ESP32** để điều khiển hệ thống chiếu sáng thông minh. 

Đây là sản phẩm tiểu luận cuối kỳ môn học **Mạng cảm biến (ELE1421)**.
* **Ngành:** Công nghệ Internet vạn vật (IoT) - Khoa Viễn thông II
* **Học viện:** Học viện Công nghệ Bưu chính Viễn thông Cơ sở tại TP. Hồ Chí Minh
* **Sinh viên thực hiện:** Lê Văn Hùng
* **MSSV:** N23DCCI028
* **Lớp:** D23CQCI01-N
* **Giảng viên hướng dẫn:** Thầy Hồ Nhựt Minh

---

## 1. Tính Năng Dự Án
- **Nhận diện giọng nói Offline:** Xử lý và suy luận trực tiếp trên chip biên không cần mạng Internet, bảo vệ quyền riêng tư gia đình tối đa.
- **Trợ lý kích hoạt giọng nói:** Tích hợp Wake Word `"hùng ơi"` để mở trạng thái chờ lệnh trong 5 giây (tránh nhận nhầm khẩu lệnh khi trò chuyện bình thường).
- **Bộ 6 nhãn phân loại:** 
  1. `hùng ơi` (Wake word kích hoạt)
  2. `bật đèn` (Mở thiết bị chiếu sáng)
  3. `tắt đèn` (Tắt thiết bị chiếu sáng)
  4. `sáng hơn` (Tăng độ sáng của đèn qua PWM)
  5. `noise` (Tiếng ồn nền môi trường: quạt, máy tính, tiếng xe cộ)
  6. `unknown` (Các từ nói tự do ngoài danh mục)
- **Tùy chỉnh độ sáng:** Điều khiển LED chính tăng dần độ sáng theo cấp bằng tín hiệu điều chế độ rộng xung (PWM).

---

## 2. Thông Số Hiệu Năng Mô Hình (Edge Impulse)
Mô hình TinyML 1D-CNN được lượng tử hóa INT8 thông qua trình biên dịch EON Compiler đạt các thông số thực nghiệm như sau:
- **Độ chính xác Validation (Validation Accuracy):** `66.7%`
- **Độ mất mát Validation (Validation Loss):** `1.08`
- **Độ chính xác Test độc lập (Test Accuracy):** `58.33%`
- **Thời gian suy luận (Inference Latency):** `86 ms` (gồm 85 ms trích xuất đặc trưng DSP MFCC và 1 ms chạy mạng 1D-CNN) trên vi xử lý ARM Cortex-M4 tương đương.
- **Bộ nhớ RAM tĩnh (Peak RAM Usage):** `15.4 KB`
- **Bộ nhớ lưu trữ (Flash Usage):** `31.2 KB`

---

## 3. Sơ Đồ Đấu Nối Phần Cứng (Wiring Diagram)

### Kết nối cảm biến âm thanh INMP441 I2S với ESP32:
| Chân INMP441 | Chân ESP32 | Mô tả |
|---|---|---|
| **VDD** | **3.3V** | Cấp nguồn 3.3V |
| **GND** | **GND** | Nối đất |
| **L/R** | **GND** | Chọn kênh Trái (Left Channel) |
| **WS** | **GPIO 25** | Tín hiệu Word Select (chọn kênh) |
| **SCK** | **GPIO 32** | Tín hiệu Serial Clock (xung nhịp) |
| **SD** | **GPIO 33** | Tín hiệu Serial Data (dữ liệu âm thanh) |

### Kết nối cơ cấu chấp hành (LED / Relay):
| Thiết bị đầu ra | Chân ESP32 | Vai trò |
|---|---|---|
| **LED chính (PWM)** | **GPIO 2** | Đèn chiếu sáng thông minh (Điều khiển độ sáng qua PWM) |
| **LED trạng thái** | **GPIO 12** | Đèn hiển thị trạng thái chờ lệnh (bật khi nhận diện được `hùng ơi`) |

---

## 4. Cấu Trúc Mã Nguồn Thư Mục
```text
mangcambien-cuoiky-levanhung/
├── edge-impulse-sdk/      # Thư viện SDK của Edge Impulse (chứa các thuật toán DSP & toán tử toán học)
├── model-parameters/       # Tham số mô hình (cấu hình trích xuất đặc trưng, số lượng nhãn)
├── tflite-model/           # File lưu trữ đồ thị mạng nơ-ron và trọng số lượng tử hóa INT8
├── README.md               # Tài liệu hướng dẫn sử dụng và giới thiệu đề tài (File này)
└── inference_kws.cpp       # Mã nguồn thực thi suy luận mẫu trên thiết bị vi điều khiển ESP32
```

---

## 5. Hướng Dẫn Biên Dịch Và Nạp Chương Trình

### Bước 1: Chuẩn bị phần mềm
1. Tải và cài đặt [Arduino IDE](https://www.arduino.cc/en/software) phiên bản mới nhất.
2. Cài đặt ESP32 Board package trong Arduino IDE:
   - Truy cập `File` > `Preferences` > Thêm URL sau vào *Additional Boards Manager URLs*:
     `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`
   - Truy cập `Tools` > `Board` > `Boards Manager`, tìm kiếm `esp32` của Espressif và ấn *Install*.

### Bước 2: Tải thư viện mô hình từ Edge Impulse
1. Đăng nhập dự án của bạn trên [Edge Impulse Studio](https://studio.edgeimpulse.com/).
2. Di chuyển đến mục **Deployment** ở menu bên trái.
3. Trong phần *Create library*, chọn **Arduino library** và click **Build**.
4. Giải nén file `.zip` tải về và copy các thư mục `edge-impulse-sdk`, `model-parameters`, `tflite-model` cùng file header `.h` vào chung thư mục chứa mã nguồn của bạn.

### Bước 3: Nạp chương trình xuống ESP32
1. Mở file mã nguồn `inference_kws.cpp` trong Arduino IDE hoặc IDE yêu thích.
2. Đấu nối phần cứng theo bảng sơ đồ ở mục 3.
3. Kết nối ESP32 với máy tính qua cáp Micro-USB hoặc USB-C.
4. Chọn đúng Board (ví dụ: *ESP32 Dev Module*) và đúng Cổng COM nhận diện được tại mục `Tools` > `Port`.
5. Bấm nút **Upload** (mũi tên hướng sang phải) trên thanh công cụ để biên dịch và nạp code xuống ESP32.
6. Mở **Serial Monitor** (phím tắt `Ctrl + Shift + M`) với tốc độ baud `115200` để theo dõi nhật ký hoạt động và kết quả nhận dạng khẩu lệnh trực tiếp.
