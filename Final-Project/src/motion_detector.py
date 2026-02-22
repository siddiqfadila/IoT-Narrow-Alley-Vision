# /home/pi/camera_project/src/motion_detector.py
import cv2
import time
import json
import threading
import logging
import socket
import RPi.GPIO as GPIO
from picamera2 import Picamera2
from datetime import datetime
import signal
import sys
import os
import config

class DualROIDetector:
    def __init__(self):
        # Inisialisasi dari file config
        self.buzzer_pin = config.BUZZER_PIN
        self.lamp_pin = config.LAMP_PIN
        self.api_port = config.API_PORT
        self.roi1_coords = config.ROI_1_COORDS
        self.roi2_coords = config.ROI_2_COORDS
        self.motion_threshold = config.MOTION_THRESHOLD
        self.direction_time_threshold = config.DIRECTION_TIME_THRESHOLD
        self.alarm_cooldown = config.ALARM_COOLDOWN

        # Variabel untuk melacak posisi terakhir objek
        self.last_centroid = None

        # Variabel Internal
        self.running = True
        self.latest_frame = None
        self.frame_lock = threading.Lock()
        self.state_lock = threading.Lock()
        self.picam2 = None
        self.bg_subtractor = None
        self.api_socket = None
        self.logger = None

        # Variabel state deteksi
        self.roil_detected_time = 0 # Perhatikan, ini 'roil' bukan 'roi1' sesuai gambar asli
        self.last_alarm_time = 0
        self.sequence_count = 0
        self.last_sequence_time = None
        self.sequence_detected_flag = False

    def setup_logging(self):
        os.makedirs('/home/pi/camera_project/logs', exist_ok=True)
        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s - Detector - %(levelname)s - %(message)s',
                            handlers=[
                                logging.FileHandler('/home/pi/camera_project/logs/motion_detector.log'),
                                logging.StreamHandler()
                            ])
        self.logger = logging.getLogger(__name__)

    def setup_gpio(self):
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.buzzer_pin, GPIO.OUT)
        GPIO.setup(self.lamp_pin, GPIO.OUT)
        GPIO.output(self.buzzer_pin, GPIO.LOW)
        GPIO.output(self.lamp_pin, GPIO.HIGH)

    def setup_camera(self):
        try:
            self.picam2 = Picamera2()
            cam_config = self.picam2.create_preview_configuration(main={"format": 'XRGB8888', "size": (640, 480)})
            self.picam2.configure(cam_config)
            self.picam2.start()
            self.logger.info("Kamera berhasil diinisialisasi.")
            time.sleep(2.0)
        except Exception as e:
            self.logger.critical(f"Gagal total menginisialisasi kamera: {e}")
            sys.exit(1)

    def setup_background_subtractors(self):
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=50, detectShadows=False)

    def setup_internal_api(self):
        self.api_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.api_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.api_socket.bind(('localhost', self.api_port))
        self.api_socket.listen(5)
        api_thread = threading.Thread(target=self.api_server_loop, daemon=True)
        api_thread.start()
        self.logger.info(f"Server API Internal berjalan di port {self.api_port}")

    def api_server_loop(self):
        while self.running:
            try:
                conn, addr = self.api_socket.accept()
                request = conn.recv(1024).decode().strip()
                if request == "get_frame_and_status":
                    with self.frame_lock:
                        if self.latest_frame is not None:
                            _, buffer = cv2.imencode('.jpg', self.latest_frame)
                            frame_data_hex = buffer.tobytes().hex()
                        else:
                            frame_data_hex = ""
                    with self.state_lock:
                        status = {
                            "sequence_detected": self.sequence_detected_flag,
                            "sequence_count": self.sequence_count,
                            "last_sequence": self.last_sequence_time,
                        }
                    response_data = {"status": status, "frame": frame_data_hex}
                    conn.sendall(json.dumps(response_data).encode())
                    conn.close()
            except Exception:
                pass

    def activate_alarm_outputs(self, duration=3, repeat=3):
        self.logger.info("!!! ALARM AKTIF: Lampu & Buzzer Berkedip!!!")
        interval = (duration / repeat) / 2
        for _ in range(repeat):
            GPIO.output(self.lamp_pin, GPIO.LOW)
            GPIO.output(self.buzzer_pin, GPIO.HIGH)
            time.sleep(interval)
            GPIO.output(self.lamp_pin, GPIO.HIGH)
            GPIO.output(self.buzzer_pin, GPIO.LOW)
            time.sleep(interval)
        self.logger.info("!!! ALARM NONAKTIF !!!")

    def signal_handler(self, signum, frame):
        self.logger.info(f"Menerima sinyal {signum}, mematikan...")
        self.running = False

    def cleanup(self):
        self.logger.info("Membersihkan resource...")
        self.running = False
        if self.picam2:
            self.picam2.stop()
        GPIO.output(self.lamp_pin, GPIO.HIGH)
        GPIO.cleanup()
        if self.api_socket:
            self.api_socket.close()
        self.logger.info("Pembersihan selesai.")

    def run(self):
        self.setup_logging()
        self.setup_gpio()
        self.setup_camera()
        self.setup_background_subtractors()
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        self.setup_internal_api()
        self.logger.info("Sistem Deteksi Gerakan Dimulai.")

        try:
            while self.running:
                frame = self.picam2.capture_array()
                current_time = time.time()

                fg_mask = self.bg_subtractor.apply(frame)
                _, fg_mask = cv2.threshold(fg_mask, 250, 255, cv2.THRESH_BINARY)
                contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                current_centroid = None
                if contours:
                    largest_contour = max(contours, key=cv2.contourArea)
                    if cv2.contourArea(largest_contour) > self.motion_threshold:
                        M = cv2.moments(largest_contour)
                        if M["m00"] != 0:
                            cx = int(M["m10"] / M["m00"])
                            cy = int(M["m01"] / M["m00"])
                            current_centroid = (cx, cy)
                
                x1, y1, w1, h1 = self.roi1_coords
                x2, y2, w2, h2 = self.roi2_coords

                in_roi1 = current_centroid is not None and (x1 < current_centroid[0] < x1 + w1 and y1 < current_centroid[1] < y1 + h1)
                in_roi2 = current_centroid is not None and (x2 < current_centroid[0] < x2 + w2 and y2 < current_centroid[1] < y2 + h2)

                with self.state_lock:
                    self.sequence_detected_flag = False

                    if in_roi1 and self.roil_detected_time == 0:
                        if self.last_centroid is not None:
                            if self.last_centroid[1] < y1 and current_centroid[1] > y1:
                                self.logger.info("Objek MASUK ke ROI 1 dari ATAS. Memulai timer...")
                                self.roil_detected_time = current_time

                    if in_roi2 and self.roil_detected_time > 0:
                        time_diff = current_time - self.roil_detected_time
                        if 0 < time_diff < self.direction_time_threshold:
                            if (current_time - self.last_alarm_time) > self.alarm_cooldown:
                                self.logger.info("Objek terkonfirmasi di ROI 2. Memicu alarm!")
                                threading.Thread(target=self.activate_alarm_outputs, args=(3,3)).start()
                                self.last_alarm_time = current_time
                                
                                # TIGA BARIS YANG HILANG, SEKARANG DITAMBAHKAN KEMBALI
                                self.sequence_detected_flag = True
                                self.sequence_count += 1
                                self.last_sequence_time = datetime.now().isoformat()
                                self.roil_detected_time = 0

                    if self.roil_detected_time > 0 and (current_time - self.roil_detected_time) > self.direction_time_threshold:
                        self.logger.info("Timeout. Mereset timer.")
                        self.roil_detected_time = 0

                self.last_centroid = current_centroid
                
                display_frame = frame.copy()
                roi1_color = (0, 255, 0) if in_roi1 else (0, 0, 255)
                roi2_color = (0, 255, 0) if in_roi2 else (0, 0, 255)
                
                cv2.rectangle(display_frame, (x1, y1), (x1 + w1, y1 + h1), roi1_color, 2)
                cv2.putText(display_frame, "ROI 1 (Entry)", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, roi1_color, 2)
                cv2.rectangle(display_frame, (x2, y2), (x2 + w2, y2 + h2), roi2_color, 2)
                cv2.putText(display_frame, "ROI 2 (Confirm)", (x2, y2 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, roi2_color, 2)
                
                if current_centroid:
                    cv2.circle(display_frame, current_centroid, 5, (255, 0, 255), -1)

                with self.frame_lock:
                    self.latest_frame = display_frame
                time.sleep(0.01)

        except KeyboardInterrupt:
            self.logger.info("Proses dihentikan.")
        finally:
            self.cleanup()


if __name__ == "__main__":
    detector = DualROIDetector()
    detector.run()