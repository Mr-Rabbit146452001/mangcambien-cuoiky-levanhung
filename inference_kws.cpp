/**
 * File: inference_kws.cpp
 * 
 * Báo cáo tiểu luận môn Mạng cảm biến
 * Đề tài: Điều khiển đèn thông minh bằng giọng nói (Audio-KWS)
 * Sinh viên thực hiện: Lê Văn Hùng (MSSV: N23DCCI028)
 * Lớp: D23CQCI01-N
 * 
 * Hướng dẫn: Tệp tin này triển khai nhận diện từ khóa giọng nói (Audio Keyword Spotting)
 * sử dụng thư viện Edge Impulse SDK, giao tiếp cảm biến âm thanh INMP441 qua giao thức I2S,
 * điều khiển bật, tắt và thay đổi độ sáng LED bằng tín hiệu PWM.
 */

#include <Arduino.h>
#include <driver/i2s.h>
// Khai báo thư viện suy luận của Edge Impulse
// Thay thế tên thư viện bằng tên file zip thư viện bạn cài đặt trong Arduino IDE
#include <dieu_khien_den_thong_minh_inferencing.h>

// Cấu hình chân I2S kết nối INMP441
#define I2S_WS   25
#define I2S_SD   33
#define I2S_SCK  32
#define I2S_PORT I2S_NUM_0

// Cấu hình chân GPIO điều khiển đèn LED thông minh
#define LED_PIN       2   // Đèn LED chính điều khiển độ sáng (PWM)
#define STATUS_LED    12  // Đèn LED báo trạng thái Wake Word ("hùng ơi")

// Cấu hình thông số PWM điều khiển độ sáng
#define PWM_FREQ      5000
#define PWM_CHAN      0
#define PWM_RES       8   // Phân giải 8-bit (0-255)

// Các biến trạng thái điều khiển
bool is_activated = false;       // Trạng thái chờ lệnh sau Wake-word "hùng ơi"
unsigned long active_timer = 0;   // Bộ đếm thời gian tự động tắt trạng thái nghe (5 giây)
int current_brightness = 128;    // Độ sáng hiện tại (0-255)

// Cấu hình bộ đệm ghi âm cho Edge Impulse
static int16_t *sampleBuffer;
static bool record_status = false;
static unsigned int sample_index = 0;

// Khởi tạo giao tiếp I2S đọc dữ liệu âm thanh từ INMP441
void init_i2s() {
    i2s_config_t i2s_config = {
        .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
        .sample_rate = 16000, // Tần số lấy mẫu 16kHz tương thích cấu hình model TinyML
        .bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT, // INMP441 trả về dữ liệu 32-bit
        .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,  // Đơn kênh Mono
        .communication_format = i2s_comm_format_t(I2S_COMM_FORMAT_I2S | I2S_COMM_FORMAT_I2S_MSB),
        .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count = 8,
        .dma_buf_len = 64,
        .use_apll = false
    };

    i2s_pin_config_t pin_config = {
        .bck_io_num = I2S_SCK,
        .ws_io_num = I2S_WS,
        .data_out_num = I2S_PIN_NO_CHANGE,
        .data_in_num = I2S_SD
    };

    i2s_driver_install(I2S_PORT, &i2s_config, 0, NULL);
    i2s_set_pin(I2S_PORT, &pin_config);
}

// Đọc tín hiệu âm thanh từ bộ đệm DMA
int get_audio_data(size_t offset, size_t length, float *out_ptr) {
    // Ánh xạ dữ liệu thô sang mảng float phục vụ khối trích xuất MFCC
    for (size_t i = 0; i < length; i++) {
        out_ptr[i] = (float)sampleBuffer[offset + i];
    }
    return 0;
}

void setup() {
    Serial.begin(115200);
    while (!Serial);

    Serial.println("=================================================");
    Serial.println("KWS Smart Lights Controller - Le Van Hung (N23DCCI028)");
    Serial.println("=================================================");

    // Khởi tạo chân GPIO đầu ra
    pinMode(STATUS_LED, OUTPUT);
    digitalWrite(STATUS_LED, LOW);

    // Cấu hình PWM điều khiển LED chính
    ledcSetup(PWM_CHAN, PWM_FREQ, PWM_RES);
    ledcAttachPin(LED_PIN, PWM_CHAN);
    ledcWrite(PWM_CHAN, 0); // Ban đầu tắt đèn

    // Khởi tạo I2S cho microphone INMP441
    init_i2s();

    // Cấp phát bộ đệm mẫu âm thanh cho suy luận (1 giây @ 16kHz)
    sampleBuffer = (int16_t *)malloc(EI_CLASSIFIER_RAW_SAMPLE_COUNT * sizeof(int16_t));
    if (sampleBuffer == NULL) {
        Serial.println("ERR: Khong the cap phat bo dem sampleBuffer!");
        return;
    }

    Serial.println("He thong da san sang. Hay phat lenh 'hung oi' de kich hoat...");
}

void loop() {
    // Tự động tắt trạng thái kích hoạt sau 5 giây nếu không nhận được lệnh điều khiển
    if (is_activated && (millis() - active_timer > 5000)) {
        is_activated = false;
        digitalWrite(STATUS_LED, LOW);
        Serial.println("[He thong] Da het thoi gian cho. Ve trang thai cho Wake Word.");
    }

    // Đọc dữ liệu từ Microphone INMP441 vào bộ đệm
    size_t bytes_read;
    int32_t raw_sample;
    int16_t clean_sample;

    for (int i = 0; i < EI_CLASSIFIER_RAW_SAMPLE_COUNT; i++) {
        // Đọc 4 byte dữ liệu từ I2S (INMP441 trả về 32-bit nhưng chỉ lấy 24-bit có nghĩa)
        i2s_read(I2S_PORT, &raw_sample, sizeof(raw_sample), &bytes_read, portMAX_DELAY);
        
        // Chuẩn hóa tín hiệu âm thanh thành dạng 16-bit
        clean_sample = (raw_sample >> 14) & 0xFFFF;
        sampleBuffer[i] = clean_sample;
    }

    // Thiết lập cấu hình callback tín hiệu cho Edge Impulse SDK
    signal_t signal;
    signal.total_length = EI_CLASSIFIER_RAW_SAMPLE_COUNT;
    signal.get_data = &get_audio_data;

    // Chạy mô hình suy luận TinyML (MFCC DSP + 1D-CNN)
    ei_impulse_result_t result = { 0 };
    EI_IMPULSE_ERROR r = run_classifier(&signal, &result, false);
    if (r != EI_IMPULSE_OK) {
        Serial.printf("ERR: Khong the thuc hien suy luan (%d)\n", r);
        return;
    }

    // Phân tích kết quả suy luận
    int pred_index = -1;
    float max_prob = 0.0;

    for (size_t ix = 0; ix < EI_CLASSIFIER_LABEL_COUNT; ix++) {
        if (result.classification[ix].value > max_prob) {
            max_prob = result.classification[ix].value;
            pred_index = ix;
        }
    }

    // Nếu xác suất nhận diện lớn hơn ngưỡng tin cậy 0.65
    if (pred_index != -1 && max_prob > 0.65) {
        String label = result.classification[pred_index].label;
        Serial.printf("Nhan dien duoc: [%s] voi do tin cay: %.2f%%\n", label.c_str(), max_prob * 100);

        // Kịch bản điều khiển thông minh dựa trên 6 nhãn
        if (label == "hung oi") {
            is_activated = true;
            active_timer = millis();
            digitalWrite(STATUS_LED, HIGH);
            Serial.println("[Tro Ly] Vang! Em dang nghe, moi anh ra lenh...");
        } 
        else if (is_activated) {
            if (label == "bat den") {
                ledcWrite(PWM_CHAN, current_brightness);
                Serial.printf("[Hanh dong] Da bat den LED voi do sang %d/255\n", current_brightness);
                is_activated = false;
                digitalWrite(STATUS_LED, LOW);
            } 
            else if (label == "tat den") {
                ledcWrite(PWM_CHAN, 0);
                Serial.println("[Hanh dong] Da tat den LED.");
                is_activated = false;
                digitalWrite(STATUS_LED, LOW);
            } 
            else if (label == "sang hon") {
                current_brightness = min(current_brightness + 64, 255);
                ledcWrite(PWM_CHAN, current_brightness);
                Serial.printf("[Hanh dong] Tang do sang LED: %d/255\n", current_brightness);
                is_activated = false;
                digitalWrite(STATUS_LED, LOW);
            }
        }
    }
}
