# backend/report_generator.py
import json
from fpdf import FPDF
from datetime import datetime

class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'CAD Assessment Report', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def create_report(json_data_path, output_pdf_path):
    with open(json_data_path, 'r') as f:
        data = json.load(f)

    pdf = PDFReport()
    pdf.add_page()
    pdf.set_font('Arial', '', 12)

    # Report Header
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, f"Student File: {data['student_file']}", 0, 1)
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 10, f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0, 1)
    pdf.ln(10)

    # Analysis Results
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Analysis Summary', 0, 1)
    pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 190, pdf.get_y())
    pdf.ln(5)

    pdf.set_font('Arial', '', 11)
    if data['analysis_status'] == 'Success':
        pdf.cell(60, 10, 'Status:', 0, 0)
        pdf.set_text_color(0, 128, 0) # Green
        pdf.cell(0, 10, 'Success', 0, 1)
        pdf.set_text_color(0, 0, 0) # Black
        
        pdf.cell(60, 10, 'Master Model Feature Count:', 0, 0)
        pdf.cell(0, 10, str(data['master_feature_count']), 0, 1)
        
        pdf.cell(60, 10, 'Student Model Feature Count:', 0, 0)
        pdf.cell(0, 10, str(data['student_feature_count']), 0, 1)
        
        # Simple Grade based on feature count
        pdf.ln(10)
        pdf.set_font('Arial', 'B', 12)
        grade = "PASS" if data['master_feature_count'] == data['student_feature_count'] else "FAIL"
        pdf.cell(60, 10, 'Preliminary Grade:', 0, 0)
        pdf.cell(0, 10, grade, 0, 1)
        pdf.set_font('Arial', '', 11)
        if grade == "PASS":
            pdf.multi_cell(0, 10, "Comments: The student's model has the correct number of features, matching the master model. This indicates a good understanding of the required steps.")
        else:
            pdf.multi_cell(0, 10, "Comments: The feature count does not match the master model. Please review the model's construction history for missing or extra features.")

    else:
        pdf.set_text_color(255, 0, 0) # Red
        pdf.multi_cell(0, 10, f"Analysis Failed: {data['error_message']}", 0, 1)
    
    pdf.output(output_pdf_path)
    print(f"PDF report generated: {output_pdf_path}")
