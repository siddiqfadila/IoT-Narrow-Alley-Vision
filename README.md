# Final-Project
**Aajskhjkash**
📷 IoT Real-Time Motion Monitoring System (Edge Deployment) Sistem Computer Vision berbasis Internet of Things (IoT) untuk mendeteksi pergerakan secara real-time menggunakan algoritma Dual Region of Interest (ROI). Proyek ini dirancang secara modular dengan arsitektur berorientasi objek (OOP) di Python, dan di-deploy langsung pada edge device (Raspberry Pi 3B+ dengan OS Debian Bullseye) menggunakan integrasi layanan background Linux.

🏗️ System Architecture & Workflow (Tambahkan gambar bagan arsitektur di sini jika ada)

Sistem ini memisahkan beban kerja pemrosesan sensor dan antarmuka web, berkomunikasi menggunakan protokol TCP/IP Socket:

Core Processing (motion_detector.py): Berjalan sebagai Linux Daemon (systemd). Mengakses kamera, menjalankan algoritma Background Subtraction, dan bertindak sebagai TCP Server.

Web Interface (app.py): Berjalan melalui Gunicorn WSGI server. Bertindak sebagai TCP Client yang mengambil data dari Core Processing dan meneruskannya ke browser klien secara asynchronous via WebSockets (Flask-SocketIO).

✨ Key Engineering Features 💻 Software Development (Dev) Object-Oriented Architecture: Penggunaan class (DualROIDetector, FlaskWebInterface) untuk enkapsulasi logika, pengelolaan state, dan memastikan kode mudah di-maintain.

Non-Blocking Asynchronous Logic: Implementasi WebSockets dan komunikasi antarmuka (IPC) via internal TCP API (localhost socket) agar pemrosesan video yang berat tidak membuat antarmuka web menjadi freeze.

Lightweight Computer Vision: Menggunakan algoritma ROI dan Background Subtraction MOG2 yang dioptimalkan untuk perangkat keras dengan RAM & CPU terbatas (Raspberry Pi).

🐧 System Administration & Networking (Ops) Linux Service Management: Implementasi systemd (motion-detector.service) untuk auto-start, isolasi proses, dan auto-restart jika terjadi crash (High Availability).

Production Web Server Deployment: Menggunakan Gunicorn dengan worker class geventwebsocket yang dieksekusi via rc.local untuk menangani traffic web secara stabil di lingkungan Linux.

TCP/IP Inter-Process Communication: Menghubungkan dua script independen menggunakan port lokal TCP, menunjukkan pemahaman fondasi jaringan komputer dalam pengembangan aplikasi.

🛠️ Tech Stack Programming Language: Python 3, JavaScript (ES6), HTML/CSS

Libraries: OpenCV (cv2), Flask, Flask-SocketIO, Gunicorn, RPi.GPIO

OS & Infrastructure: Debian Bullseye (Raspberry Pi OS), systemd, Bash Scripting, TCP Sockets

🚀 Deployment / Installation Guide (Tuliskan langkah-langkah instalasi di Linux, ini menunjukkan Anda paham CLI dan environment Linux)

Clone repository ini.

Setup Virtual Environment: python3 -m venv bin

Install dependencies: pip install -r requirements.txt

Copy service file ke systemd: sudo cp deployment/motion-detector.service /etc/systemd/system/

Enable service: sudo systemctl enable motion-detector dan sudo systemctl start motion-detector

Jalankan web server (Gunicorn) sesuai script di deployment/rc.local.
