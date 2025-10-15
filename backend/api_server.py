# backend/api_server.py
from flask import Flask, request, send_file
import subprocess, datetime, zipfile, json, hashlib
from pathlib import Path
import pandas as pd
from collections import defaultdict
import report_generator

app = Flask(__name__)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSING_DIR = PROJECT_ROOT / "temp_processing_files"
WORKER_SCRIPT_PATH = PROJECT_ROOT / "worker" / "sw_worker.py"
PROCESSING_DIR.mkdir(exist_ok=True)
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
    
    # 3. *** FINAL, ROBUST PLAGIARISM LOGIC ***
    plagiarism_results = {name: {"is_plagiarised": False, "copied_from": []} for name in student_analysis_data.keys()}
    
    # Group students ONLY by their complex feature delta signature
    delta_groups = defaultdict(list)
    for name, data in student_analysis_data.items():
        delta = data["delta"]
        # Only consider deltas that are complex enough to be suspicious
        if len(delta) > PLAGIARISM_COMPLEXITY_THRESHOLD:
            delta_str = json.dumps(delta, sort_keys=True)
            delta_hash = hashlib.md5(delta_str.encode()).hexdigest()
            delta_groups[delta_hash].append(name)
            
    # Now, populate results based ONLY on these delta groups
    for group in delta_groups.values():
        if len(group) > 1: # A group with more than one member is a plagiarism cluster
            for member_name in group:
                plagiarism_results[member_name]["is_plagiarised"] = True
                plagiarism_results[member_name]["copied_from"].extend([other for other in group if other != member_name])

    # 4. Generate Reports and CSV (unchanged)
    pdf_paths, csv_data = [], []
    for s_path in student_paths:
        analysis_data = {"student_file": s_path.name, "master_volume_mm3": master_volume, **student_analysis_data[s_path.name]}
        plagiarism_info = plagiarism_results[s_path.name]
        plagiarism_info["copied_from"] = sorted(list(set(plagiarism_info["copied_from"])))

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
