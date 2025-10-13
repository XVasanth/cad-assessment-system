# backend/api_server.py
from flask import Flask, request, send_file
import os
import subprocess
import datetime
import zipfile
import json
from pathlib import Path
import itertools
import report_generator

app = Flask(__name__)

# --- START OF FIX ---
# Get the directory of the current script (the 'backend' folder)
BACKEND_DIR = Path(__file__).resolve().parent
# Get the root project directory by going one level up
PROJECT_ROOT = BACKEND_DIR.parent

# Define paths relative to the project root for robustness
PROCESSING_DIR = PROJECT_ROOT / "temp_processing_files"
WORKER_SCRIPT_PATH = PROJECT_ROOT / "worker" / "sw_worker.py"
# --- END OF FIX ---

PROCESSING_DIR.mkdir(exist_ok=True)

def get_signature(file_path, job_dir):
    """Calls the worker to get a feature signature from a file."""
    output_json = job_dir / f"{file_path.stem}_sig.json"
    command = ["python", str(WORKER_SCRIPT_PATH), str(file_path), str(output_json)]
    # Use shell=True for better path handling on Windows, though not always necessary
    subprocess.run(command, check=True, capture_output=True, text=True, shell=True) 
    with open(output_json, 'r') as f:
        return json.load(f)

@app.route('/analyze', methods=['POST'])
def analyze():
    # 1. Setup job directory and save files
    master_file = request.files['master_file']
    student_zip = request.files['student_zip']
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    job_dir = PROCESSING_DIR / timestamp
    job_dir.mkdir()

    master_file_path = job_dir / master_file.filename
    master_file.save(master_file_path)

    student_paths = []
    with zipfile.ZipFile(student_zip, 'r') as zf:
        zf.extractall(job_dir)
        for name in zf.namelist():
            if name.lower().endswith('.sldprt') and not name.startswith('__MACOSX'):
                student_paths.append(job_dir / name)

    # 2. Get the base signature
    base_sig_data = get_signature(master_file_path, job_dir)
    base_signature = base_sig_data.get("signature", [])
    
    # 3. Get all student signatures and calculate deltas
    student_deltas = {}
    for s_path in student_paths:
        full_sig_data = get_signature(s_path, job_dir)
        full_signature = full_sig_data.get("signature", [])
        
        base_modified = False
        delta = []
        if len(full_signature) >= len(base_signature) and full_signature[:len(base_signature)] == base_signature:
            delta = full_signature[len(base_signature):]
        else:
            base_modified = True
            delta = full_signature
        
        student_deltas[s_path.name] = {
            "delta": delta,
            "base_modified": base_modified,
            "delta_feature_count": len(delta)
        }

    # 4. Compare deltas for plagiarism
    plagiarism_results = {s_path.name: {"is_plagiarised": False, "copied_from": None} for s_path in student_paths}
    student_names = list(student_deltas.keys())
    for (student1, student2) in itertools.combinations(student_names, 2):
        delta1 = student_deltas[student1]["delta"]
        delta2 = student_deltas[student2]["delta"]
        
        if len(delta1) > 0 and delta1 == delta2:
            plagiarism_results[student1].update({"is_plagiarised": True, "copied_from": student2})
            plagiarism_results[student2].update({"is_plagiarised": True, "copied_from": student1})

    # 5. Generate PDF reports
    pdf_paths = []
    for s_path in student_paths:
        student_name = s_path.name
        analysis_data = {"student_file": student_name, **student_deltas[student_name]}
        plagiarism_info = plagiarism_results[student_name]
        output_pdf_path = job_dir / f"{s_path.stem}_report.pdf"
        
        report_generator.create_report(analysis_data, plagiarism_info, output_pdf_path)
        pdf_paths.append(output_pdf_path)
        
    # 6. Package reports and send to user
    final_zip_path = job_dir / "assessment_reports.zip"
    with zipfile.ZipFile(final_zip_path, 'w') as zf:
        for pdf_path in pdf_paths:
            zf.write(pdf_path, arcname=pdf_path.name)
    
    return send_file(final_zip_path, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
