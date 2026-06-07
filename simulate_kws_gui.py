import tkinter as tk
from tkinter import messagebox, ttk
import threading
import time
import sys
import os

# Helper to check and install dependencies
def check_dependencies():
    try:
        import speech_recognition as sr
    except ImportError:
        print("Installing dependency: speech_recognition...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "SpeechRecognition"])
    try:
        import pyaudio
    except ImportError:
        print("Installing dependency: pyaudio...")
        import subprocess
        # On Windows, pip install pyaudio usually works directly with python 3.7+
        # If it fails, we will notify the user in the GUI log.
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyaudio"])
        except Exception:
            print("Failed to install pyaudio. Try installing it manually.")

# Perform dependency check in background
check_dependencies()

import speech_recognition as sr

class TinyMLSimulator:
    def __init__(self, root):
        self.root = root
        self.root.title("TinyML Smart Light - Virtual Hardware Simulator")
        self.root.geometry("850x650")
        self.root.resizable(False, False)
        self.root.configure(bg="#0F172A") # Dark slate tech background
        
        # State variables
        self.is_active = False # Wake word activated status
        self.brightness = 0 # 0, 50, 150, 255 (PWM range)
        self.wake_timer = 0
        self.listening = False
        
        self.setup_ui()
        self.log_message("=== KHỞI ĐỘNG TRÌNH GIẢ LẬP PHẦN CỨNG ẢO ===")
        self.log_message("Thiết bị giả lập: ESP32 + INMP441 Microphone + 2x LED")
        self.log_message("Đang sử dụng microphone máy tính của bạn làm bộ thu tín hiệu...")
        
        # Start voice recognition thread
        self.stop_listening_event = threading.Event()
        self.listen_thread = threading.Thread(target=self.voice_recognition_loop, daemon=True)
        self.listen_thread.start()
        
    def setup_ui(self):
        # Title Header
        title_lbl = tk.Label(self.root, text="MÔ PHỎNG HỆ THỐNG ĐIỀU KHIỂN ĐÈN BẰNG GIỌNG NÓI", 
                             fg="#F8FAFC", bg="#0F172A", font=("Arial", 18, "bold"))
        title_lbl.pack(pady=20)
        
        subtitle_lbl = tk.Label(self.root, text="Đề tài: Mạng cảm biến TinyML KWS | SVTH: Lê Văn Hùng", 
                                fg="#94A3B8", bg="#0F172A", font=("Arial", 12, "italic"))
        subtitle_lbl.pack(pady=2)
        
        # Main Layout: Left Canvas (Hardware UI), Right Log (Terminal)
        main_frame = tk.Frame(self.root, bg="#0F172A")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Left Panel (Canvas)
        self.canvas = tk.Canvas(main_frame, width=420, height=450, bg="#1E293B", 
                                highlightthickness=2, highlightbackground="#334155")
        self.canvas.pack(side=tk.LEFT, padx=10, pady=10)
        
        # Draw Virtual Hardware
        self.draw_hardware_layout()
        
        # Right Panel (Log Terminal)
        right_frame = tk.Frame(main_frame, bg="#0F172A")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        log_label = tk.Label(right_frame, text="NHẬT KÝ HỆ THỐNG (TERMINAL)", 
                             fg="#38BDF8", bg="#0F172A", font=("Courier New", 12, "bold"))
        log_label.pack(anchor=tk.W, pady=2)
        
        # Text widget for logs
        self.log_text = tk.Text(right_frame, bg="#020617", fg="#22C55E", 
                                font=("Courier New", 10), state=tk.DISABLED, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Controls Frame (Bottom on right)
        ctrl_frame = tk.Frame(right_frame, bg="#0F172A", pady=10)
        ctrl_frame.pack(fill=tk.X)
        
        # Manual Trigger Buttons for testing without Microphone
        manual_lbl = tk.Label(ctrl_frame, text="Kích hoạt thủ công (nếu không có Mic):", 
                              fg="#94A3B8", bg="#0F172A", font=("Arial", 10))
        manual_lbl.pack(anchor=tk.W, pady=2)
        
        btn_frame = tk.Frame(ctrl_frame, bg="#0F172A")
        btn_frame.pack(fill=tk.X)
        
        btn_wake = tk.Button(btn_frame, text="1. Nói 'Hùng ơi'", bg="#38BDF8", fg="black", 
                             font=("Arial", 10, "bold"), width=11, command=self.trigger_wake)
        btn_wake.pack(side=tk.LEFT, padx=5)
        
        btn_on = tk.Button(btn_frame, text="2. Nói 'Bật đèn'", bg="#EAB308", fg="black", 
                           font=("Arial", 10, "bold"), width=11, command=self.trigger_on)
        btn_on.pack(side=tk.LEFT, padx=5)
        
        btn_off = tk.Button(btn_frame, text="3. Nói 'Tắt đèn'", bg="#64748B", fg="white", 
                            font=("Arial", 10, "bold"), width=11, command=self.trigger_off)
        btn_off.pack(side=tk.LEFT, padx=5)
        
        btn_brt = tk.Button(btn_frame, text="4. Nói 'Sáng hơn'", bg="#EA580C", fg="white", 
                            font=("Arial", 10, "bold"), width=11, command=self.trigger_bright)
        btn_brt.pack(side=tk.LEFT, padx=5)
        
    def draw_hardware_layout(self):
        # Draw ESP32 Board
        self.canvas.create_rectangle(140, 80, 280, 320, fill="#334155", outline="#475569", width=3, tags="esp32")
        self.canvas.create_rectangle(140, 80, 280, 120, fill="#0F172A", outline="#475569", tags="esp32_header")
        self.canvas.create_text(210, 100, text="ESP32 MCU", fill="white", font=("Arial", 12, "bold"))
        
        # Draw Pins
        for y in range(130, 310, 20):
            # Left pins
            self.canvas.create_rectangle(125, y-4, 140, y+4, fill="#94A3B8")
            # Right pins
            self.canvas.create_rectangle(280, y-4, 295, y+4, fill="#94A3B8")
            
        # Draw INMP441 Microphone (Left side)
        self.canvas.create_oval(30, 180, 90, 240, fill="#0284C7", outline="#0369A1", width=2, tags="inmp")
        self.canvas.create_text(60, 210, text="MIC\nI2S", fill="white", font=("Arial", 9, "bold"), justify=tk.CENTER)
        
        # Connect MIC to ESP32 (WS, SCK, SD, Power)
        self.canvas.create_line(90, 200, 125, 230, fill="#F97316", width=2, arrow=tk.LAST) # WS (Orange)
        self.canvas.create_line(90, 210, 125, 250, fill="#EAB308", width=2, arrow=tk.LAST) # SCK (Yellow)
        self.canvas.create_line(90, 220, 125, 270, fill="#22C55E", width=2, arrow=tk.LAST) # SD (Green)
        self.canvas.create_line(90, 190, 125, 150, fill="#EF4444", width=2, arrow=tk.LAST) # VDD (Red)
        self.canvas.create_line(90, 230, 125, 290, fill="black", width=2, arrow=tk.LAST) # GND
        
        self.canvas.create_text(70, 160, text="I2S Bus", fill="#94A3B8", font=("Arial", 8, "italic"))
        
        # Draw Status LED (GPIO 12)
        # Red circle when inactive, Yellow when active
        self.status_led = self.canvas.create_oval(180, 370, 210, 400, fill="#475569", outline="#334155", width=2)
        self.canvas.create_text(195, 415, text="LED Trạng thái\n(GPIO 12)", fill="#94A3B8", font=("Arial", 9), justify=tk.CENTER)
        # Wire
        self.canvas.create_line(210, 300, 210, 350, 195, 350, 195, 370, fill="#A855F7", width=2) # GPIO 12 wire
        
        # Draw Smart Light LED (GPIO 2)
        # Black when off, varying shades of yellow/orange when on
        self.smart_led = self.canvas.create_oval(320, 110, 390, 180, fill="#1E293B", outline="#475569", width=3)
        self.smart_led_glow = self.canvas.create_oval(310, 100, 400, 190, outline="#EAB308", width=1, state=tk.HIDDEN)
        self.canvas.create_text(355, 195, text="Đèn chính (PWM)\n(GPIO 2)", fill="#94A3B8", font=("Arial", 9), justify=tk.CENTER)
        # Wire
        self.canvas.create_line(280, 210, 310, 210, 310, 145, 320, 145, fill="#3B82F6", width=2) # GPIO 2 wire
        
    def log_message(self, msg):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        
    def update_hardware_display(self):
        # Update Status LED
        if self.is_active:
            # Flashing yellow
            self.canvas.itemconfig(self.status_led, fill="#F59E0B", outline="#FBBF24")
        else:
            self.canvas.itemconfig(self.status_led, fill="#475569", outline="#334155")
            
        # Update Smart Light LED based on brightness (PWM value)
        if self.brightness == 0:
            self.canvas.itemconfig(self.smart_led, fill="#1E293B", outline="#475569")
            self.canvas.itemconfig(self.smart_led_glow, state=tk.HIDDEN)
        elif self.brightness == 50:
            self.canvas.itemconfig(self.smart_led, fill="#FEF08A", outline="#FDE047") # Dim yellow
            self.canvas.itemconfig(self.smart_led_glow, state=tk.HIDDEN)
        elif self.brightness == 150:
            self.canvas.itemconfig(self.smart_led, fill="#FDE047", outline="#FACC15") # Medium yellow
            self.canvas.itemconfig(self.smart_led_glow, state=tk.NORMAL, outline="#FDE047")
        else: # 255
            self.canvas.itemconfig(self.smart_led, fill="#FACC15", outline="#EAB308") # Bright yellow/orange
            self.canvas.itemconfig(self.smart_led_glow, state=tk.NORMAL, outline="#FACC15", width=3)

    # Wake word activation timer
    def check_wake_timeout_loop(self):
        while self.is_active:
            time.sleep(1)
            self.wake_timer -= 1
            if self.wake_timer <= 0:
                self.is_active = False
                self.log_message("[HỆ THỐNG] Đã hết 5 giây chờ lệnh. Đèn trạng thái TẮT. Trở lại trạng thái chờ Wake Word.")
                self.root.after(0, self.update_hardware_display)
                break

    # Voice activation simulation triggers
    def trigger_wake(self):
        if not self.is_active:
            self.is_active = True
            self.wake_timer = 5
            self.log_message("[NHẬN DẠNG] Khẩu lệnh: 'HÙNG ƠI' (Wake Word)")
            self.log_message("[HÀNH ĐỘNG] Kích hoạt chế độ nhận lệnh trong 5 giây. Đèn trạng thái BẬT SÁNG.")
            self.update_hardware_display()
            # Start timer thread
            threading.Thread(target=self.check_wake_timeout_loop, daemon=True).start()
        else:
            self.wake_timer = 5 # Reset timer
            self.log_message("[HỆ THỐNG] Nhận lại Wake Word, gia hạn thêm 5 giây chờ lệnh.")

    def trigger_on(self):
        if self.is_active:
            self.brightness = 150 # Default ON brightness
            self.log_message("[NHẬN DẠNG] Khẩu lệnh: 'BẬT ĐÈN'")
            self.log_message("[HÀNH ĐỘNG] ESP32 xuất tín hiệu PWM GPIO 2 (Độ sáng: 60%). Đèn chính BẬT.")
            self.update_hardware_display()
        else:
            self.log_message("[CẢNH BÁO] Nhận diện được 'Bật đèn' nhưng hệ thống chưa được kích hoạt bằng Wake Word 'Hùng ơi'. Bỏ qua lệnh.")

    def trigger_off(self):
        if self.is_active:
            self.brightness = 0
            self.log_message("[NHẬN DẠNG] Khẩu lệnh: 'TẮT ĐÈN'")
            self.log_message("[HÀNH ĐỘNG] ESP32 ngắt tín hiệu GPIO 2. Đèn chính TẮT.")
            self.update_hardware_display()
        else:
            self.log_message("[CẢNH BÁO] Nhận diện được 'Tắt đèn' nhưng chưa kích hoạt bằng Wake Word 'Hùng ơi'. Bỏ qua lệnh.")

    def trigger_bright(self):
        if self.is_active:
            if self.brightness == 0:
                self.brightness = 50
                self.log_message("[HỆ THỐNG] Đèn đang tắt, bật ở mức sáng yếu (20%).")
            elif self.brightness == 50:
                self.brightness = 150
                self.log_message("[HỆ THỐNG] Tăng độ sáng lên mức trung bình (60%).")
            elif self.brightness == 150:
                self.brightness = 255
                self.log_message("[HỆ THỐNG] Tăng độ sáng lên mức tối đa (100%).")
            else:
                self.log_message("[HỆ THỐNG] Đèn đã ở độ sáng tối đa (100%).")
                
            self.log_message(f"[NHẬN DẠNG] Khẩu lệnh: 'SÁNG HƠN'")
            self.log_message(f"[HÀNH ĐỘNG] ESP32 tăng chu kỳ xung PWM GPIO 2. Độ sáng hiện tại: {int(self.brightness/2.55)}%.")
            self.update_hardware_display()
        else:
            self.log_message("[CẢNH BÁO] Nhận diện được 'Sáng hơn' nhưng chưa kích hoạt bằng Wake Word 'Hùng ơi'. Bỏ qua lệnh.")

    # Main Voice Recognition Loop
    def voice_recognition_loop(self):
        r = sr.Recognizer()
        r.energy_threshold = 300  # Adjust according to environment
        r.dynamic_energy_threshold = True
        
        while not self.stop_listening_event.is_set():
            # Check mic availability
            try:
                with sr.Microphone() as source:
                    self.listening = True
                    # Let the system know it's listening
                    # Adjust for ambient noise
                    r.adjust_for_ambient_noise(source, duration=0.5)
                    self.log_message("[MICROPHONE] Đang lắng nghe âm thanh...")
                    audio = r.listen(source, phrase_time_limit=3)
                    
                self.log_message("[HỆ THỐNG] Đang phân tích tín hiệu giọng nói...")
                # Recognize using Google Speech API (Vietnamese)
                try:
                    text = r.recognize_google(audio, language="vi-VN")
                    text_lower = text.lower()
                    self.log_message(f"[THU ÂM] Nhận diện thô: '{text}'")
                    
                    # Process KWS keywords
                    if "hùng" in text_lower or "ơi" in text_lower or "cục cưng" in text_lower:
                        self.root.after(0, self.trigger_wake)
                    elif "bật" in text_lower and "đèn" in text_lower:
                        self.root.after(0, self.trigger_on)
                    elif "tắt" in text_lower and "đèn" in text_lower:
                        self.root.after(0, self.trigger_off)
                    elif "sáng" in text_lower or "hơn" in text_lower or "tăng" in text_lower:
                        self.root.after(0, self.trigger_bright)
                    else:
                        self.log_message(f"[LỌC NHÃN] Phân loại nhãn: 'UNKNOWN' (Khẩu lệnh tự do ngoài danh mục)")
                except sr.UnknownValueError:
                    # Sound was heard but no speech recognized
                    self.log_message("[LỌC NHÃN] Phân loại nhãn: 'NOISE' (Tiếng ồn môi trường)")
                except sr.RequestError as e:
                    self.log_message(f"[LỖI] Không thể kết nối dịch vụ nhận dạng: {e}")
                    
            except Exception as e:
                self.log_message(f"[CẢNH BÁO] Lỗi truy cập Microphone: {str(e)[:50]}")
                self.log_message("-> Bạn có thể nhấn các nút điều khiển thủ công phía dưới để mô phỏng.")
                time.sleep(5) # Wait before retry

if __name__ == "__main__":
    root = tk.Tk()
    app = TinyMLSimulator(root)
    root.mainloop()
