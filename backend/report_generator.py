# backend/report_generator.py
import json
from fpdf import FPDF
from datetime import datetime
from pathlib import Path

class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12); self.cell(0, 10, 'CAD Assessment Report', 0, 1, 'C'); self.ln(5)
    def footer(self):
        self.set_y(-15); self.set_font('Arial', 'I', 8); self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def get_accuracy_grade(deviation):
    if deviation <= 0.5: return "A+ (Excellent)"
    elif deviation <= 1.5: return "A (Good)"
    elif deviation <= 3.0: return "B (Acceptable)"
    elif deviation <= 5.0: return "C (Needs Improvement)"
    else: return "F (Major Revision Required)"

def create_report(analysis_data, plagiarism_info, output_pdf_path):
    filename_stem = Path(analysis_data.get('student_file', '')).stem
    parts = filename_stem.split('_', 1)
    register_number, part_name = parts if len(parts) == 2 else ("N/A", filename_stem)

    pdf = PDFReport()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16); pdf.cell(0, 10, f"Assessment for: {part_name}", 0, 1)
    pdf.set_font('Arial', '', 12); pdf.cell(0, 10, f"Register Number: {register_number}", 0, 1); pdf.ln(10)

    pdf.set_font('Arial', 'B', 12); pdf.cell(0, 10, 'Plagiarism Analysis', 0, 1, 'L'); pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 190, pdf.get_y()); pdf.ln(5)
    pdf.set_font('Arial', '', 11)
    if plagiarism_info.get('is_plagiarised'):
        pdf.set_text_color(255, 0, 0)
        copied_from_reg_num = Path(plagiarism_info.get('copied_from', '')).stem.split('_', 1)[0]
        pdf.multi_cell(0, 8, f"ALERT: High similarity found with submission from Register Number: {copied_from_reg_num}. Manual review required.")
    else:
        pdf.set_text_color(0, 128, 0); pdf.cell(0, 10, "No direct plagiarism detected among peers.", 0, 1)
    pdf.set_text_color(0); pdf.ln(10)
    
    pdf.set_font('Arial', 'B', 12); pdf.cell(0, 10, 'Geometric Accuracy Assessment (vs. Faculty Model)', 0, 1, 'L'); pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 190, pdf.get_y()); pdf.ln(5)
    pdf.set_font('Arial', '', 11)
    deviation = analysis_data.get('volume_deviation_percent', 0.0)
    accuracy_grade = get_accuracy_grade(deviation)
    pdf.cell(60, 10, "Volume Deviation:", 0, 0); pdf.cell(0, 10, f"{deviation:.4f} %", 0, 1)
    pdf.cell(60, 10, "Accuracy Grade:", 0, 0); pdf.set_font('Arial', 'B', 11); pdf.cell(0, 10, accuracy_grade, 0, 1); pdf.set_font('Arial', '', 11)
    pdf.cell(60, 10, "Faculty Model Volume (mm³):", 0, 0); pdf.cell(0, 10, f"{analysis_data.get('master_volume_mm3', 0.0):,.2f}", 0, 1)
    pdf.cell(60, 10, "Student Model Volume (mm³):", 0, 0); pdf.cell(0, 10, f"{analysis_data.get('student_volume_mm3', 0.0):,.2f}", 0, 1); pdf.ln(10)

    pdf.set_font('Arial', 'B', 12); pdf.cell(0, 10, 'Feature Construction Assessment', 0, 1, 'L'); pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 190, pdf.get_y()); pdf.ln(5)
    pdf.set_font('Arial', '', 11)
    pdf.cell(60, 10, "Base Model Modified:", 0, 0); pdf.cell(0, 10, "Yes" if analysis_data.get('base_modified') else "No", 0, 1)
    pdf.cell(60, 10, "Features added by student:", 0, 0); pdf.cell(0, 10, str(analysis_data.get('delta_feature_count', 'N/A')), 0, 1)

    pdf.output(output_pdf_path)
