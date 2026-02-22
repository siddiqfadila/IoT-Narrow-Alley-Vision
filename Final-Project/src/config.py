# -*- coding: utf-8 -*-

# =============================================================================
# CONFIGURATION FILE
# -----------------------------------------------------------------------------
# File ini berisi semua variabel konfigurasi untuk sistem deteksi gerakan.
# Mengubah nilai di sini akan mempengaruhi perilaku skrip motion_detector.py
# dan app.py tanpa perlu mengubah logika inti program.
# =============================================================================

# -- PENGATURAN UMUM --
HOST = '127.0.0.1'  # Alamat IP untuk API internal (biarkan 127.0.0.1)
PORT = 8001         # Port untuk API internal
LOG_LEVEL = "INFO"  # Level logging (DEBUG, INFO, WARNING, ERROR)

# -- PENGATURAN PIN GPIO --
# Menggunakan penomoran pin BCM (Broadcom SOC channel)
RELAY_PIN = 17      # Pin GPIO yang terhubung ke relay lampu
BUZZER_PIN = 27     # Pin GPIO yang terhubung ke buzzer

# -- PENGATURAN KAMERA & DETEKSI --
# Resolusi kamera (lebar, tinggi)
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FRAME_RATE = 30     # Frame per detik

# Region of Interest (ROI)
# ROI adalah area di mana deteksi gerakan akan dipantau.
# Format: (startX, startY, endX, endY)
# ROI 1 harus menjadi zona pertama yang dilewati objek.
ROI_1 = (20, 150, 220, 350)
ROI_2 = (420, 150, 620, 350)

# Sensitivitas Deteksi
# Nilai yang lebih kecil berarti lebih sensitif terhadap gerakan.
MIN_CONTOUR_AREA = 2500  # Luas kontur minimum untuk dianggap sebagai gerakan

# Pengaturan Waktu
# Durasi alarm dalam detik setelah gerakan terdeteksi
ALARM_DURATION_SECONDS = 5.0
# Waktu maksimum (detik) antara deteksi di ROI 1 dan ROI 2
# untuk dianggap sebagai satu sekuens gerakan yang valid.
SEQUENCE_TIMEOUT_SECONDS = 2.0
