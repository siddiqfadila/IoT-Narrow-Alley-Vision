import os
import time
import socket
import json
import logging
import threading
from flask import Flask, render_template, Response, jsonify
from flask_socketio import SocketIO
import cv2
import numpy as np

class FlaskWebInterface:
    def __init__(self, motion_api_port=8888):
        self.motion_api_port = motion_api_port
        self.app = None
        self.socketio = None
        self.logger = None
        # BARU: Variabel untuk mengingat jumlah sekuens terakhir
        self.last_known_sequence_count = 0
        
        self.setup_logging()
        
        if not self.wait_for_detector_api():
            self.logger.critical("Motion detector API did not respond. Web interface cannot start.")
            sys.exit(1)
        
        self.setup_flask()
    
    def setup_logging(self):
        os.makedirs('/home/pi/camera_project/logs', exist_ok=True)
        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s - WebApp - %(levelname)s - %(message)s',
                            handlers=[
                                logging.FileHandler('/home/pi/camera_project/logs/flask_web.log'),
                                logging.StreamHandler()
                            ])
        self.logger = logging.getLogger(__name__)
    
    def wait_for_detector_api(self, max_retries=30):
        for attempt in range(max_retries):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1.0)
                    s.connect(('localhost', self.motion_api_port))
                    self.logger.info(f"Connected to Motion Detector API on attempt {attempt + 1}.")
                    return True
            except (ConnectionRefusedError, socket.timeout):
                self.logger.warning(f"Waiting for Motion Detector API... (attempt {attempt + 1}/{max_retries})")
                time.sleep(1)
        return False
    
    def setup_flask(self):
        self.app = Flask(__name__)
        self.socketio = SocketIO(self.app, async_mode='gevent')
        self.register_routes()
    
    def get_frame_and_status_from_detector(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2.0)
                s.connect(('localhost', self.motion_api_port))
                s.sendall(b'get_frame_and_status')
                
                data_buffer = b""
                while True:
                    part = s.recv(4096)
                    if not part:
                        break
                    data_buffer += part
                
                response = json.loads(data_buffer.decode())
                return response
        except Exception as e:
            self.logger.error(f"Failed to communicate with the motion detector: {e}")
            return None
    
    def register_routes(self):
        @self.app.route('/')
        def index():
            return render_template('dashboard.html')
        
        @self.app.route('/video_feed')
        def video_feed():
            return Response(self.generate_frames_from_api(), mimetype='multipart/x-mixed-replace; boundary=frame')
        
        @self.socketio.on('shutdown_system')
        def handle_shutdown():
            self.logger.warning("Shutdown command received from web interface. Shutting down now.")
            # This command requires passwordless sudo configuration
            os.system('sudo shutdown now')
    
    def generate_frames_from_api(self):
        while True:
            response = self.get_frame_and_status_from_detector()
            
            if response and response.get('frame'):
                frame_hex = response['frame']
                frame_bytes = bytes.fromhex(frame_hex)
                
                # ========================================================
                # == LOGIKA NOTIFIKASI YANG BARU DAN LEBIH ANDAL ==
                # ========================================================
                if response and response.get('status'):
                    status_data = response['status']
                    current_sequence_count = status_data.get('sequence_count', 0)
                    
                    # Cek jika jumlah sekuens BERTAMBAH
                    if current_sequence_count > self.last_known_sequence_count:
                        self.logger.info(f"New sequence detected! Count increased from {self.last_known_sequence_count} to {current_sequence_count}")
                        # Kirim notifikasi 'alert' ke web
                        self.socketio.emit('motion_alert', {'message': 'PERINGATAN: OBJEK TERDETEKSI!'})
                        # Update jumlah sekuens yang terakhir diketahui
                        self.last_known_sequence_count = current_sequence_count
                    
                    # Selalu kirim status terbaru untuk memperbarui angka di dashboard
                    self.socketio.emit('motion_status_update', status_data)
                
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            else:
                self.logger.warning("No frame received from API, displaying placeholder")
                black_frame_jpg = cv2.imencode('.jpg', np.zeros((480, 640, 3), dtype=np.uint8))[1].tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + black_frame_jpg + b'\r\n')
            
            time.sleep(0.1)

# === Section for Gunicorn ===
web_interface = FlaskWebInterface()
app = web_interface.app
socketio = web_interface.socketio

if __name__ == '__main__':
    web_interface = FlaskWebInterface()
    
    # ========================================================
    # == TAMBAHAN: SSL/HTTPS SUPPORT (FIX untuk gevent) ==
    # ========================================================
    # Path ke SSL certificate
    ssl_cert = '/home/pi/camera_project/ssl/cert.pem'
    ssl_key = '/home/pi/camera_project/ssl/key.pem'
    
    # Cek apakah certificate ada
    if os.path.exists(ssl_cert) and os.path.exists(ssl_key):
        print("Starting Flask-SocketIO web app with HTTPS...")
        # Untuk gevent, gunakan certfile dan keyfile sebagai keyword arguments
        web_interface.socketio.run(
            web_interface.app, 
            host='0.0.0.0', 
            port=5000, 
            debug=False,
            certfile=ssl_cert,
            keyfile=ssl_key
        )
    else:
        print("SSL certificates not found. Starting with HTTP...")
        print("To enable HTTPS, generate certificates with:")
        print("  sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \\")
        print("    -keyout /home/pi/camera_project/ssl/key.pem \\")
        print("    -out /home/pi/camera_project/ssl/cert.pem")
        web_interface.socketio.run(
            web_interface.app, 
            host='0.0.0.0', 
            port=5000, 
            debug=False

        )
