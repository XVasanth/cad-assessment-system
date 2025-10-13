# 🎓 CAD Assessment System

![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

An automated system for evaluating SOLIDWORKS part files and detecting plagiarism in an academic setting. The application analyzes student submissions against a standard base model, identifies peer-to-peer copying using a "delta" analysis of the feature tree, and generates individual PDF reports.



---

## ✨ Features

* **Web-Based Interface:** A simple and intuitive UI built with Streamlit for uploading files.
* **Standard Base Model:** Faculty provides a standard starting part file (`.SLDPRT`).
* **Bulk Student Submissions:** Accepts a single `.ZIP` archive containing all student part files.
* **Delta-Based Plagiarism Detection:** Intelligently ignores the common base features and analyzes only the unique work added by each student to detect copying between peers.
* **Automated PDF Reports:** Generates a professional, downloadable PDF report for each student detailing the analysis and any plagiarism alerts.
* **Packaged Results:** Delivers all PDF reports in a single, convenient `.ZIP` file.

---

## 🏛️ Architecture

This application uses a client-server architecture to function:

1.  **Streamlit Frontend:** The user-facing web application that handles file uploads and displays results.
2.  **Flask Backend:** The central server that receives files, manages the analysis workflow, and orchestrates the worker.
3.  **SOLIDWORKS Worker:** A Python script that uses the SOLIDWORKS API (`pywin32`) to open files, extract feature data, and perform the core analysis. This requires a local SOLIDWORKS installation.

---

## 📋 Prerequisites

Before you begin, ensure you have the following installed on your system:

* **Python 3.8** or newer.
* A licensed copy of **SOLIDWORKS**.
* **Git** for cloning the repository.

---

## 🚀 Setup & Installation

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/your-username/cad-assessment-system.git](https://github.com/your-username/cad-assessment-system.git)
    cd cad-assessment-system
    ```

2.  **Create and activate a Python virtual environment:**
    ```bash
    python -m venv venv
    venv\Scripts\activate
    ```

3.  **Install the required dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

---

## ▶️ How to Run

1.  **Start SOLIDWORKS:** Launch the SOLIDWORKS application and leave it running in the background.
2.  **Run the Backend Server:** Open a command prompt, navigate to the project root, activate the virtual environment, and run:
    ```bash
    python backend/api_server.py
    ```
3.  **Run the Frontend Application:** Open a **second** command prompt, navigate to the project root, activate the virtual environment, and run:
    ```bash
    streamlit run frontend/app.py
    ```
4.  **Open the Application:** Your web browser should automatically open to `http://localhost:8501`. Follow the on-screen instructions to upload your files and generate the reports.

---

##  F.A.Q
- How to do a proper submission for evaluation
	- Please follow this naming convention `RegisterNumber_PartName.sldprt` as the PDF generation is depended on it.

## 📄 License

This project is licensed under the **MIT License**. See the `LICENSE` file for more details.
