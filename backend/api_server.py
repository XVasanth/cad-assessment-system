# backend/api_server.py
from flask import Flask, request, jsonify, send_file
import os
import subprocess
import datetime
import zipfile
from pathlib import Path
import report_generator # Import our new PDF generator

app = Flask(__name__)
PROCESSING_DIR = Path("temp_processing_files")
PROCESSING_DIR.mkdir(exist_ok=True)
WORKER_SCRIPT_PATH = Path("../worker/sw_worker.py").resolve()

@app.route('/analyze', methods=['POST'])
def analyze_files():
    if 'master_file' not in request.files or 'student_zip' not in request.files:
        return jsonify({"error": "Missing files"}), 400

    master_file = request.files['master_file']
    student_zip = request.files['student_zip']
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    job_dir = PROCESSING_DIR / timestamp
    job_dir.mkdir()

    master_file_path = job_dir / master_file.filename
    master_file.save(master_file_path)

    student_file_paths = []
    with zipfile.ZipFile(student_zip, 'r') as zf:
        zf.extractall(job_dir)
        for filename in zf.namelist():
            if filename.lower().endswith('.sldprt') and not filename.startswith('__MACOSX'):
                student_file_paths.append(job_dir / filename)
    
    if not student_file_paths:
        return jsonify({"error": "No .sldprt files found in zip"}), 400

    pdf_report_paths = []
    for student_path in student_file_paths:
        output_json_path = student_path.with_suffix('.json')
        output_pdf_path = student_path.with_suffix('.pdf')
        command = ["python", str(WORKER_SCRIPT_PATH), str(master_file_path), str(student_path), str(output_json_path)]
        
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
            # After worker succeeds, generate the PDF
            report_generator.create_report(output_json_path, output_pdf_path)
            pdf_report_paths.append(output_pdf_path)
        except subprocess.CalledProcessError as e:
            print(f"Worker failed for {student_path.name}: {e.stderr}")
            # Even if it fails, we can create a simple "failed" report
            error_data = {"student_file": student_path.name, "analysis_status": "Failed", "error_message": e.stderr}
            with open(output_json_path, 'w') as f:
                json.dump(error_data, f)
            report_generator.create_report(output_json_path, output_pdf_path)
            pdf_report_paths.append(output_pdf_path)

    # Package all generated PDFs into a single zip file
    final_zip_path = job_dir / "assessment_reports.zip"
    with zipfile.ZipFile(final_zip_path, 'w') as zf:
        for pdf_path in pdf_report_paths:
            zf.write(pdf_path, arcname=pdf_path.name)
    
    # Send the zip file back to the frontend for download
    return send_file(final_zip_path, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
