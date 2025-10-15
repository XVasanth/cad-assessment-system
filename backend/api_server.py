# backend/api_server.py
from flask import Flask, request, send_file
import subprocess, datetime, zipfile, json, itertools
from pathlib import Path
import pandas as pd
import report_generator

app = Flask(__name__)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSING_DIR = PROJECT_ROOT / "temp_processing_files"
WORKER_SCRIPT_PATH = PROJECT_ROOT / "worker" / "sw_worker.py"
PROCESSING_DIR.mkdir(exist_ok=True)

# --- NEW: Define a threshold for what is considered a "complex" sequence of features ---
# A delta of 3 or fewer features is considered too simple to be a reliable plagiarism signal.
# You can adjust this value based on your assignments.
PLAGIARISM_COMPLEXITY_THRESHOLD = 3

def get_analysis_data(file_path, job_dir):
    output_json = job_dir / f"{file_path.stem}_analysis.json"
    command = ["python", str(WORKER_SCRIPT_PATH), str(file_path), str(output_json)]
    subprocess.run(command, check=True, capture_output=True, text=True, shell=True) 
    with open(output_json, 'r') as f: return json.load(f)

@app.route('/analyze', methods=['POST'])
def analyze():
    # 1. Setup and file handling (unchanged)
    master_file = request.files['master_file']
    student_zip = request.files['student_zip']
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    job_dir = PROCESSING_DIR / timestamp; job_dir.mkdir()
    master_file_path = job_dir / master_file.filename; master_file.save(master_file_path)

    student_paths = []
    with zipfile.ZipFile(student_zip, 'r') as zf:
        zf.extractall(job_dir)
        for name in zf.namelist():
            if name.lower().endswith('.sldprt') and not name.startswith('__MACOSX'):
                student_paths.append(job_dir / name)

    # 2. Analyze all files (unchanged)
    master_data = get_analysis_data(master_file_path, job_dir)
    base_signature = master_data.get("signature", [])
    master_volume = master_data.get("volume_mm3", 0.0)
    master_gdt = set(master_data.get("gdt_callouts", []))

    student_analysis_data = {}
    for s_path in student_paths:
        s_data = get_analysis_data(s_path, job_dir)
        full_signature = s_data.get("signature", [])
        student_volume = s_data.get("volume_mm3", 0.0)
        student_gdt = set(s_data.get("gdt_callouts", []))
        
        base_modified = not (len(full_signature) >= len(base_signature) and full_signature[:len(base_signature)] == base_signature)
        delta = full_signature[len(base_signature):] if not base_modified else full_signature
        volume_dev = abs(student_volume - master_volume) / master_volume * 100 if master_volume > 0 else 0
        
        gdt_match = "Match" if student_gdt == master_gdt else "Mismatch"
        if not student_gdt and master_gdt: gdt_match = "Missing"

        student_analysis_data[s_path.name] = {
            "delta": delta, "base_modified": base_modified, "volume_deviation_percent": volume_dev, 
            "student_volume_mm3": student_volume, "gdt_match_status": gdt_match
        }
    
    # 3. *** UPDATED PLAGIARISM "HANDSHAKE" CHECK ***
    plagiarism_results = {name: {"is_plagiarised": False, "copied_from": None} for name in student_analysis_data.keys()}
    for (s1_name, s2_name) in itertools.combinations(student_analysis_data.keys(), 2):
        s1_data, s2_data = student_analysis_data[s1_name], student_analysis_data[s2_name]
        
        # Condition 1: The feature deltas are identical AND sufficiently complex
        deltas_match = (
            len(s1_data["delta"]) > PLAGIARISM_COMPLEXITY_THRESHOLD and 
            s1_data["delta"] == s2_data["delta"]
        )
        
        # Condition 2: The final volumes are nearly identical (a direct file copy)
        volumes_match = abs(s1_data["student_volume_mm3"] - s2_data["student_volume_mm3"]) < 0.001
        
        # If either condition is true, flag it as plagiarism
        if deltas_match or volumes_match:
            plagiarism_results[s1_name].update({"is_plagiarised": True, "copied_from": s2_name})
            plagiarism_results[s2_name].update({"is_plagiarised": True, "copied_from": s1_name})

    # 4. Generate Reports and CSV (unchanged)
    pdf_paths, csv_data = [], []
    for s_path in student_paths:
        analysis_data = {"student_file": s_path.name, "master_volume_mm3": master_volume, **student_analysis_data[s_path.name]}
        plagiarism_info = plagiarism_results[s_path.name]
        
        output_pdf_path = job_dir / f"{s_path.stem}_report.pdf"
        report_generator.create_report(analysis_data, plagiarism_info, output_pdf_path); pdf_paths.append(output_pdf_path)
        
        stem = s_path.stem; parts = stem.split('_', 1)
        reg_num, part_name = parts if len(parts) == 2 else ("N/A", stem)
        csv_data.append({
            "Register Number": reg_num, "Part Name": part_name,
            "Volume Deviation (%)": f"{analysis_data['volume_deviation_percent']:.4f}",
            "Accuracy Grade": report_generator.get_accuracy_grade(analysis_data['volume_deviation_percent']),
            "GD&T Status": analysis_data['gdt_match_status'],
            "Plagiarism Flag": "YES" if plagiarism_info['is_plagiarised'] else "NO"
        })

    # 5. Create final ZIP package (unchanged)
    summary_csv_path = job_dir / "summary_report.csv"
    pd.DataFrame(csv_data).to_csv(summary_csv_path, index=False)

    final_zip_path = job_dir / "assessment_reports.zip"
    with zipfile.ZipFile(final_zip_path, 'w') as zf:
        for pdf_path in pdf_paths: zf.write(pdf_path, arcname=pdf_path.name)
        zf.write(summary_csv_path, arcname=summary_csv_path.name)
    
    return send_file(final_zip_path, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
