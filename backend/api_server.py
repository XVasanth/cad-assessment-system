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

PYTHON_EXECUTABLE = PROJECT_ROOT / "venv" / "Scripts" / "python.exe"

def get_analysis_data(file_path, job_dir):
    output_json = job_dir / f"{file_path.stem}_analysis.json"
    command = [str(PYTHON_EXECUTABLE), str(WORKER_SCRIPT_PATH), str(file_path), str(output_json)]
    result = subprocess.run(command, check=True, capture_output=True, text=True, shell=True)
    
    # Print subprocess output for debugging
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    with open(output_json, 'r') as f: 
        data = json.load(f)
    
    # Debug: Print what we loaded
    print(f"\n*** JSON DATA LOADED ***")
    print(f"File: {file_path.name}")
    print(f"Volume from JSON: {data.get('volume_mm3', 0.0):.2f} mm^3")
    print(f"Status from JSON: {data.get('status', 'Unknown')}")
    if data.get('error'):
        print(f"Error from JSON: {data.get('error')}")
    print(f"{'*'*30}\n")
    
    return data

def compare_gdt(master_gdt_data, student_gdt_data):
    """
    Detailed GD&T comparison returning status and specific differences.
    """
    master_signature = set(master_gdt_data.get("combined_signature", []))
    student_signature = set(student_gdt_data.get("combined_signature", []))
    
    # Calculate differences
    missing = master_signature - student_signature
    extra = student_signature - master_signature
    matching = master_signature & student_signature
    
    # Determine overall status
    if not master_signature:
        if not student_signature:
            status = "N/A (No GD&T in master)"
            score = 100
        else:
            status = "Extra annotations present"
            score = 50
    elif not student_signature:
        status = "Missing (No GD&T)"
        score = 0
    elif missing and extra:
        status = "Partial match (missing some, has extra)"
        score = (len(matching) / len(master_signature)) * 100
    elif missing:
        status = "Incomplete (missing annotations)"
        score = (len(matching) / len(master_signature)) * 100
    elif extra:
        status = "Complete with extras"
        score = 100
    else:
        status = "Perfect match"
        score = 100
    
    return {
        "status": status,
        "score": round(score, 2),
        "total_required": len(master_signature),
        "total_found": len(student_signature),
        "matching_count": len(matching),
        "missing_count": len(missing),
        "extra_count": len(extra),
        "missing_annotations": sorted(list(missing)),
        "extra_annotations": sorted(list(extra)),
        "details": {
            "master_fcf": len(master_gdt_data.get("feature_control_frames", [])),
            "student_fcf": len(student_gdt_data.get("feature_control_frames", [])),
            "master_dimxpert": len(master_gdt_data.get("dimxpert_annotations", [])),
            "student_dimxpert": len(student_gdt_data.get("dimxpert_annotations", [])),
            "master_datums": len(master_gdt_data.get("datums", [])),
            "student_datums": len(student_gdt_data.get("datums", []))
        }
    }

@app.route('/analyze', methods=['POST'])
def analyze():
    # 1. Setup and file handling
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

    # 2. Analyze master file
    print(f"\n{'='*60}")
    print(f"ANALYZING MASTER FILE: {master_file.filename}")
    print(f"{'='*60}")
    master_data = get_analysis_data(master_file_path, job_dir)
    base_signature = master_data.get("signature", [])
    master_volume = master_data.get("volume_mm3", 0.0)
    master_gdt_data = master_data.get("gdt_data", {})
    
    print(f"\n*** MASTER DATA RECEIVED ***")
    print(f"Master Volume: {master_volume:.2f} mm^3")
    print(f"Master Features: {len(base_signature)}")
    print(f"Master GD&T Count: {len(master_gdt_data.get('combined_signature', []))}")
    print(f"Master Status: {master_data.get('status', 'Unknown')}")
    if master_data.get('error'):
        print(f"Master Error: {master_data.get('error')}")
    print(f"{'='*60}\n")

    # 3. Analyze all student files
    student_analysis_data = {}
    for s_path in student_paths:
        print(f"\n{'-'*60}")
        print(f"Analyzing: {s_path.name}")
        
        try:
            s_data = get_analysis_data(s_path, job_dir)
            
            # Check if analysis succeeded
            if s_data.get('status') != 'Success':
                print(f"  WARNING: Analysis failed for {s_path.name}")
                print(f"  Error: {s_data.get('error', 'Unknown error')}")
                # Still add it with 0 volume so it appears in the report
            
            full_signature = s_data.get("signature", [])
            student_volume = s_data.get("volume_mm3", 0.0)
            student_gdt_data = s_data.get("gdt_data", {})
            
            # Check if base was modified
            base_modified = not (len(full_signature) >= len(base_signature) and 
                               full_signature[:len(base_signature)] == base_signature)
            delta = full_signature[len(base_signature):] if not base_modified else full_signature
            
            # Volume deviation
            volume_dev = abs(student_volume - master_volume) / master_volume * 100 if master_volume > 0 else 0
            
            print(f"\n*** VOLUME COMPARISON ***")
            print(f"  Master Volume: {master_volume:.2f} mm^3")
            print(f"  Student Volume: {student_volume:.2f} mm^3")
            print(f"  Difference: {abs(student_volume - master_volume):.2f} mm^3")
            print(f"  Deviation: {volume_dev:.4f}%")
            print(f"{'*'*30}")
            
            # Detailed GD&T comparison
            gdt_comparison = compare_gdt(master_gdt_data, student_gdt_data)
            print(f"  GD&T Score: {gdt_comparison['score']}% ({gdt_comparison['status']})")
            if gdt_comparison['missing_count'] > 0:
                print(f"  Missing {gdt_comparison['missing_count']} GD&T annotations")
            
            student_analysis_data[s_path.name] = {
                "delta": delta,
                "base_modified": base_modified,
                "volume_deviation_percent": volume_dev,
                "student_volume_mm3": student_volume,
                "gdt_comparison": gdt_comparison,
                "analysis_error": s_data.get('error', '')
            }
            
        except Exception as e:
            print(f"  CRITICAL ERROR analyzing {s_path.name}: {e}")
            import traceback
            traceback.print_exc()
            
            # Add failed entry
            student_analysis_data[s_path.name] = {
                "delta": [],
                "base_modified": False,
                "volume_deviation_percent": 0.0,
                "student_volume_mm3": 0.0,
                "gdt_comparison": {
                    "status": "Failed",
                    "score": 0,
                    "total_required": 0,
                    "total_found": 0,
                    "matching_count": 0,
                    "missing_count": 0,
                    "extra_count": 0,
                    "missing_annotations": [],
                    "extra_annotations": [],
                    "details": {}
                },
                "analysis_error": str(e)
            }
    
    # 4. Plagiarism Logic (unchanged)
    plagiarism_results = {name: {"is_plagiarised": False, "copied_from": []} 
                         for name in student_analysis_data.keys()}
    delta_groups = defaultdict(list)
    for name, data in student_analysis_data.items():
        delta = data["delta"]
        if len(delta) > PLAGIARISM_COMPLEXITY_THRESHOLD:
            delta_str = json.dumps(delta, sort_keys=True)
            delta_hash = hashlib.md5(delta_str.encode()).hexdigest()
            delta_groups[delta_hash].append(name)
            
    for group in delta_groups.values():
        if len(group) > 1:
            for member_name in group:
                plagiarism_results[member_name]["is_plagiarised"] = True
                plagiarism_results[member_name]["copied_from"].extend(
                    [other for other in group if other != member_name])

    # 5. Generate Reports and CSV
    pdf_paths, csv_data = [], []
    for s_path in student_paths:
        analysis_data = {
            "student_file": s_path.name,
            "master_volume_mm3": master_volume,
            **student_analysis_data[s_path.name]
        }
        plagiarism_info = plagiarism_results[s_path.name]
        plagiarism_info["copied_from"] = sorted(list(set(plagiarism_info["copied_from"])))

        output_pdf_path = job_dir / f"{s_path.stem}_report.pdf"
        report_generator.create_report(analysis_data, plagiarism_info, output_pdf_path)
        pdf_paths.append(output_pdf_path)
        
        stem = s_path.stem
        parts = stem.split('_', 1)
        reg_num, part_name = parts if len(parts) == 2 else ("N/A", stem)
        
        gdt_comp = analysis_data['gdt_comparison']
        analysis_err = analysis_data.get('analysis_error', '')
        
        csv_data.append({
            "Register Number": reg_num,
            "Part Name": part_name,
            "Volume Deviation (%)": f"{analysis_data['volume_deviation_percent']:.4f}",
            "Accuracy Grade": report_generator.get_accuracy_grade(
                analysis_data['volume_deviation_percent']),
            "GD&T Score (%)": gdt_comp['score'],
            "GD&T Status": gdt_comp['status'],
            "Missing GD&T": gdt_comp['missing_count'],
            "Plagiarism Flag": "YES" if plagiarism_info['is_plagiarised'] else "NO",
            "Errors": "FAILED: " + analysis_err if analysis_err else "OK"
        })

    # 6. Create final ZIP package
    summary_csv_path = job_dir / "summary_report.csv"
    pd.DataFrame(csv_data).to_csv(summary_csv_path, index=False)
    final_zip_path = job_dir / "assessment_reports.zip"
    with zipfile.ZipFile(final_zip_path, 'w') as zf:
        for pdf_path in pdf_paths:
            zf.write(pdf_path, arcname=pdf_path.name)
        zf.write(summary_csv_path, arcname=summary_csv_path.name)
    
    print(f"\n{'='*60}")
    print(f"ANALYSIS COMPLETE - Reports generated")
    print(f"{'='*60}\n")
    
    return send_file(final_zip_path, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
