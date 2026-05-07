# Secure-Exam-Software-FOR-NASTP
# 🛡️ Secure Air-Gapped Examination Network (LAN)

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![PySide6](https://img.shields.io/badge/PySide6-GUI-brightgreen.svg)
![Pandas](https://img.shields.io/badge/Pandas-ETL_Engine-150458.svg)
![SQLite](https://img.shields.io/badge/SQLite-Database-003B57.svg)
![Network](https://img.shields.io/badge/Network-Offline_LAN-red.svg)

An enterprise-grade, completely offline Client-Server architecture designed to automate examination grading and data extraction in high-security, internet-restricted environments.

## 📌 The Architecture Problem
Government, defense, and aerospace facilities require automated digital testing systems. However, strict security protocols prohibit internet access, rendering standard cloud-based web applications useless. 

**The Solution:** This project bypasses the need for the cloud by establishing a localized, asynchronous HTTP polling network over a facility's internal Local Area Network (LAN). 

## ⚙️ System Workflow
The architecture is split into two distinct nodes:

1. **The Teacher Server (Master Node):** - Runs a localized Python HTTP Server (`BaseHTTPRequestHandler`).
   - Features an automated **Pandas ETL Engine** that dynamically ingests, cleans, and standardizes messy Excel/CSV question banks directly from the local hard drive.
   - Broadcasts the encrypted exam payload across the localized subnet.

2. **The Student Terminal (Client Node):**
   - Connects to the Master Node via local IP socket polling.
   - Operates a secure, locked-down GUI built with PySide6.
   - Submits results instantly back to the Master Node upon completion.

## 🚀 Core Technical Features
* **Air-Gapped Subnet Communication:** Utilizes Python threading and `socket` programming to maintain a secure, offline network without external API dependencies.
* **Dynamic Pandas Aggregation:** Automatically detects and repairs shifted columns or missing headers in raw CSV uploads before pushing the data into the examination loop.
* **Thread-Safe SQLite Logging:** Captures and permanently stores grading data with zero-downtime upon student submission.
* **Automated HTML Reporting:** Generates dynamic, color-coded HTML performance reports instantly upon exam completion.

## 🖥️ User Interface Preview
*(Note: Add 2-3 screenshots of your PySide6 dashboards here to show off the cinematic UI)*

## 🛠️ Installation & Local Deployment
Since this system is designed for offline environments, it requires no cloud configuration. 

**1. Clone the repository:**
```bash
git clone [https://github.com/YourUsername/Secure-AirGapped-Exam-Network.git](https://github.com/YourUsername/Secure-AirGapped-Exam-Network.git)
cd Secure-AirGapped-Exam-Network
