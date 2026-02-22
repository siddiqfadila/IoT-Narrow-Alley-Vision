# 📷 Smart Narrow Alley Vision (IoT Edge Deployment)

**IoT Computer Vision Deployed on Linux Debian Bullseye (Raspberry Pi 3B+) using Background Subtraction Algorithm.**

Sistem keamanan dan *monitoring* pergerakan *real-time* yang dirancang khusus untuk lingkungan sempit (gang). Proyek ini menggunakan algoritma *Dual Region of Interest* (ROI) dengan arsitektur berbasis *Object-Oriented Programming* (OOP) di Python, dan di-*deploy* langsung pada *edge device* dengan integrasi layanan *background* Linux.

## 🏗️ System Architecture

Sistem memisahkan beban kerja antara pemrosesan sensor (Core) dan antarmuka pengguna (Web) menggunakan komunikasi **TCP/IP Socket** secara *asynchronous*.

```mermaid
graph TD
    subaxis Hardware
        Cam[PiCamera] --> Core
        Core --> Relay[GPIO Relay/Lamp]
        Core --> Buzzer[GPIO Buzzer]
    end

    subaxis Core Processing Daemon
        Core[motion_detector.py<br/>TCP Server] -- Local Socket <br/> port 8001 --> Web[app.py<br/>TCP Client]
    end

    subaxis Web Server Interface
        Web --> Gunicorn[Gunicorn + Gevent]
        Gunicorn -- WebSockets <br/> port 5000 --> Browser[Client Dashboard]
    end
