# backend/report_generator.py
from fpdf import FPDF
from datetime import datetime
from pathlib import Path

class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 11)
        self.cell(0, 8, 'CAD Assessment Report', 0, 1, 'C')
        self.ln(2)
    
    def footer(self):
        self.set_y(-10)
        self.set_font('Arial', 'I', 7)
        self.cell(0, 5, f'Page {self.page_no()}', 0, 0, 'C')

def get_accuracy_grade(deviation):
    if deviation <= 0.5: return "A+"
    elif deviation <= 1.5: return "A"
    elif deviation <= 3.0: return "B"
    elif deviation <= 5.0: return "C"
    else: return "F"

def get_gdt_grade(score):
    if score >= 95: return "A+"
    elif score >= 90: return "A"
    elif score >= 80: return "B"
    elif score >= 70: return "C"
    else: return "F"

def create_report(analysis_data, plagiarism_info, output_pdf_path):
    filename_stem = Path(analysis_data.get('student_file', '')).stem
    parts = filename_stem.split('_', 1)
    register_number, part_name = parts if len(parts) == 2 else ("N/A", filename_stem)

    pdf = PDFReport()
    pdf.add_page()
    pdf.set_auto_page_break(False)  # Disable auto page break - must fit on 1 page
    
    # Header - Compact
    pdf.set_font('Arial', 'B', 13)
    pdf.cell(0, 6, f"{part_name}", 0, 1, 'C')
    pdf.set_font('Arial', '', 9)
    pdf.cell(0, 5, f"Reg: {register_number} | {datetime.now().strftime('%Y-%m-%d %H:%M')}", 0, 1, 'C')
    pdf.ln(3)

    # File Error Check (if any)
    file_error = analysis_data.get('analysis_error', '')
    if file_error:
        pdf.set_font('Arial', 'B', 11)
        pdf.set_text_color(255, 0, 0)
        pdf.cell(0, 6, "[FILE ERROR]", 0, 1, 'C')
        pdf.set_font('Arial', '', 8)
        pdf.multi_cell(0, 4, f"Error: {file_error[:80]}")
        pdf.set_text_color(0)
        pdf.ln(2)

    # PLAGIARISM - Very Compact
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 5, 'PLAGIARISM', 0, 1)
    pdf.set_font('Arial', '', 8)
    
    if plagiarism_info.get('is_plagiarised'):
        pdf.set_text_color(255, 0, 0)
        copied_from = plagiarism_info.get('copied_from', [])
        if copied_from:
            regs = [Path(cf).stem.split('_', 1)[0] for cf in copied_from]
            pdf.cell(0, 4, f"[ALERT] Similar to: {', '.join(regs[:3])}", 0, 1)
        else:
            pdf.cell(0, 4, "[ALERT] Potential plagiarism detected", 0, 1)
    else:
        pdf.set_text_color(0, 128, 0)
        pdf.cell(0, 4, "[PASS] No plagiarism detected", 0, 1)
    
    pdf.set_text_color(0)
    pdf.ln(3)
    
    # VOLUME ACCURACY - Compact
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 5, 'VOLUME ACCURACY', 0, 1)
    pdf.set_font('Arial', '', 8)
    
    deviation = analysis_data.get('volume_deviation_percent', 0.0)
    accuracy_grade = get_accuracy_grade(deviation)
    master_vol = analysis_data.get('master_volume_mm3', 0.0)
    student_vol = analysis_data.get('student_volume_mm3', 0.0)
    
    pdf.cell(50, 4, f"Master: {master_vol:.1f} mm3", 0, 0)
    pdf.cell(50, 4, f"Student: {student_vol:.1f} mm3", 0, 0)
    pdf.cell(0, 4, f"Dev: {deviation:.2f}%", 0, 1)
    
    pdf.set_font('Arial', 'B', 9)
    if deviation <= 1.5:
        pdf.set_text_color(0, 128, 0)
        status_text = f"Grade: {accuracy_grade} [PASS]"
    elif deviation <= 5.0:
        pdf.set_text_color(255, 140, 0)
        status_text = f"Grade: {accuracy_grade} [WARNING]"
    else:
        pdf.set_text_color(255, 0, 0)
        status_text = f"Grade: {accuracy_grade} [FAIL]"
    
    pdf.cell(0, 4, status_text, 0, 1)
    pdf.set_text_color(0)
    pdf.ln(3)

    # GD&T - Compact
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 5, 'GD&T ASSESSMENT', 0, 1)
    pdf.set_font('Arial', '', 8)
    
    gdt_comp = analysis_data.get('gdt_comparison', {})
    gdt_score = gdt_comp.get('score', 0)
    gdt_grade = get_gdt_grade(gdt_score)
    
    pdf.cell(50, 4, f"Score: {gdt_score}% ({gdt_grade})", 0, 0)
    pdf.cell(50, 4, f"Required: {gdt_comp.get('total_required', 0)}", 0, 0)
    pdf.cell(0, 4, f"Found: {gdt_comp.get('total_found', 0)}", 0, 1)
    
    missing_count = gdt_comp.get('missing_count', 0)
    
    pdf.set_font('Arial', 'B', 9)
    if gdt_score >= 95:
        pdf.set_text_color(0, 128, 0)
        pdf.cell(0, 4, "[PASS] All GD&T present", 0, 1)
    elif missing_count > 0:
        pdf.set_text_color(255, 140, 0)
        pdf.cell(0, 4, f"[WARNING] Missing {missing_count} annotation(s)", 0, 1)
    else:
        pdf.set_text_color(128, 128, 128)
        pdf.cell(0, 4, "[INFO] No GD&T required", 0, 1)
    
    pdf.set_text_color(0)
    pdf.set_font('Arial', '', 7)
    
    # Show missing items (max 5, very compact)
    missing_anns = gdt_comp.get('missing_annotations', [])
    if missing_anns:
        pdf.ln(1)
        pdf.set_font('Arial', 'I', 7)
        for ann in missing_anns[:5]:
            ann_text = ann if len(ann) <= 60 else ann[:57] + "..."
            pdf.cell(0, 3, f"- {ann_text}", 0, 1)
    
    pdf.ln(3)
    
    # OVERALL SUMMARY - Compact
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 5, 'OVERALL', 0, 1)
    
    accuracy_percent = 100 - min(deviation * 10, 100)
    overall_score = (accuracy_percent * 0.6) + (gdt_score * 0.4)
    
    if overall_score >= 90:
        overall_grade = "Excellent"
        color = (0, 128, 0)
    elif overall_score >= 75:
        overall_grade = "Good"
        color = (0, 128, 0)
    elif overall_score >= 60:
        overall_grade = "Satisfactory"
        color = (255, 140, 0)
    else:
        overall_grade = "Needs Improvement"
        color = (255, 0, 0)
    
    pdf.set_text_color(*color)
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 6, f"{overall_grade} ({overall_score:.1f}/100)", 0, 1, 'C')
    pdf.set_text_color(0)
    
    pdf.ln(2)
    pdf.set_font('Arial', 'I', 7)
    pdf.multi_cell(0, 3, "Automated assessment. Faculty review recommended for final grading.")
    
    pdf.output(output_pdf_path)
