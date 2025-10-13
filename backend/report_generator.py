# backend/report_generator.py
import json
from fpdf import FPDF
from datetime import datetime

class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'CAD Assessment Report', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def create_report(analysis_data, plagiarism_info, output_pdf_path):
    pdf = PDFReport()
    pdf.add_page()
    pdf.set_font('Arial', '', 12)

    # Report Header
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, f"Student File: {analysis_data['student_file']}", 0, 1)
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 10, f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0, 1)
    pdf.ln(10)

    # Plagiarism Check Section
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Plagiarism Analysis', 0, 1)
    pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 190, pdf.get_y())
    pdf.ln(5)
    pdf.set_font('Arial', '', 11)
    
    if plagiarism_info['is_plagiarised']:
        pdf.set_text_color(255, 0, 0) # Red
        pdf.multi_cell(0, 8, f"ALERT: A high degree of similarity was found between this submission and the file: {plagiarism_info['copied_from']}. Manual review is strongly recommended.")
        pdf.set_text_color(0, 0, 0) # Black
    else:
        pdf.set_text_color(0, 128, 0) # Green
        pdf.cell(0, 10, "No direct plagiarism detected among student submissions.", 0, 1)
        pdf.set_text_color(0, 0, 0) # Black
    pdf.ln(10)

    # Grading Section
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Geometric & Feature Assessment', 0, 1)
    pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 190, pdf.get_y())
    pdf.ln(5)
    
    pdf.set_font('Arial', '', 11)
    pdf.cell(60, 10, "Base Model Modified:", 0, 0)
    pdf.cell(0, 10, "Yes" if analysis_data['base_modified'] else "No", 0, 1)
    
    pdf.cell(60, 10, "Features added by student:", 0, 0)
    pdf.cell(0, 10, str(analysis_data['delta_feature_count']), 0, 1)
    
    pdf.output(output_pdf_path)
