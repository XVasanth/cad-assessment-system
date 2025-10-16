# backend/report_generator.py
from fpdf import FPDF
from datetime import datetime
from pathlib import Path

class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'CAD Assessment Report', 0, 1, 'C')
        self.ln(5)
    
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')
    
    def section_header(self, title):
        """Helper to create consistent section headers"""
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, title, 0, 1, 'L')
        self.line(self.get_x(), self.get_y(), self.get_x() + 190, self.get_y())
        self.ln(5)
    
    def info_row(self, label, value, bold_value=False):
        """Helper to create consistent info rows"""
        self.set_font('Arial', '', 11)
        self.cell(60, 8, label, 0, 0)
        if bold_value:
            self.set_font('Arial', 'B', 11)
        self.cell(0, 8, str(value), 0, 1)
        self.set_font('Arial', '', 11)

def get_accuracy_grade(deviation):
    if deviation <= 0.5: return "A+ (Excellent)"
    elif deviation <= 1.5: return "A (Good)"
    elif deviation <= 3.0: return "B (Acceptable)"
    elif deviation <= 5.0: return "C (Needs Improvement)"
    else: return "F (Major Revision Required)"

def get_gdt_grade(score):
    """Convert GD&T score to letter grade"""
    if score >= 95: return "A+"
    elif score >= 90: return "A"
    elif score >= 85: return "B+"
    elif score >= 80: return "B"
    elif score >= 70: return "C"
    elif score >= 60: return "D"
    else: return "F"

def create_report(analysis_data, plagiarism_info, output_pdf_path):
    filename_stem = Path(analysis_data.get('student_file', '')).stem
    parts = filename_stem.split('_', 1)
    register_number, part_name = parts if len(parts) == 2 else ("N/A", filename_stem)

    pdf = PDFReport()
    pdf.add_page()
    
    # Header Info
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, f"Assessment for: {part_name}", 0, 1)
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 10, f"Register Number: {register_number}", 0, 1)
    pdf.cell(0, 10, f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", 0, 1)
    pdf.ln(10)
    
    # Check for file analysis errors
    file_error = analysis_data.get('analysis_error', '')
    if file_error:
        pdf.set_font('Arial', 'B', 14)
        pdf.set_text_color(255, 0, 0)
        pdf.cell(0, 10, "[FILE ANALYSIS FAILED]", 0, 1, 'C')
        pdf.set_font('Arial', '', 11)
        pdf.multi_cell(0, 8, f"Error: {file_error}")
        pdf.set_text_color(0)
        pdf.multi_cell(0, 8, "This file could not be analyzed. It may be corrupted, from an incompatible SOLIDWORKS version, or locked by another process.")
        pdf.ln(10)

    # ============ PLAGIARISM SECTION ============
    pdf.section_header('Plagiarism Analysis')
    pdf.set_font('Arial', '', 11)
    
    if plagiarism_info.get('is_plagiarised'):
        pdf.set_text_color(255, 0, 0)
        copied_from = plagiarism_info.get('copied_from', [])
        if copied_from:
            copied_from_display = []
            for cf in copied_from:
                reg = Path(cf).stem.split('_', 1)[0]
                copied_from_display.append(reg)
            pdf.multi_cell(0, 8, 
                f"[ALERT] High similarity detected with submission(s) from: "
                f"{', '.join(copied_from_display)}. Manual review required.")
        else:
            pdf.multi_cell(0, 8, "[ALERT] Potential plagiarism detected. Manual review required.")
    else:
        pdf.set_text_color(0, 128, 0)
        pdf.cell(0, 10, "[PASS] No direct plagiarism detected among peers.", 0, 1)
    
    pdf.set_text_color(0)
    pdf.ln(10)
    
    # ============ VOLUME ACCURACY SECTION ============
    pdf.section_header('Geometric Accuracy Assessment')
    
    deviation = analysis_data.get('volume_deviation_percent', 0.0)
    accuracy_grade = get_accuracy_grade(deviation)
    master_vol = analysis_data.get('master_volume_mm3', 0.0)
    student_vol = analysis_data.get('student_volume_mm3', 0.0)
    
    pdf.info_row("Master Volume:", f"{master_vol:.2f} mm3")
    pdf.info_row("Student Volume:", f"{student_vol:.2f} mm3")
    pdf.info_row("Volume Deviation:", f"{deviation:.4f} %", bold_value=True)
    pdf.info_row("Accuracy Grade:", accuracy_grade, bold_value=True)
    
    # Color code the accuracy
    if deviation <= 1.5:
        pdf.set_text_color(0, 128, 0)
        pdf.multi_cell(0, 8, "[PASS] Excellent geometric accuracy achieved.")
    elif deviation <= 5.0:
        pdf.set_text_color(255, 140, 0)
        pdf.multi_cell(0, 8, "[WARNING] Acceptable accuracy but room for improvement.")
    else:
        pdf.set_text_color(255, 0, 0)
        pdf.multi_cell(0, 8, "[FAIL] Significant deviation from master model. Review required.")
    
    pdf.set_text_color(0)
    pdf.ln(10)

    # ============ GD&T SECTION (COMPREHENSIVE) ============
    pdf.section_header('GD&T Assessment (DimXpert)')
    
    gdt_comp = analysis_data.get('gdt_comparison', {})
    gdt_status = gdt_comp.get('status', 'N/A')
    gdt_score = gdt_comp.get('score', 0)
    gdt_grade = get_gdt_grade(gdt_score)
    
    # Summary metrics
    pdf.info_row("GD&T Score:", f"{gdt_score}% ({gdt_grade})", bold_value=True)
    pdf.info_row("Status:", gdt_status, bold_value=True)
    pdf.info_row("Required Annotations:", gdt_comp.get('total_required', 0))
    pdf.info_row("Found Annotations:", gdt_comp.get('total_found', 0))
    pdf.info_row("Matching:", gdt_comp.get('matching_count', 0))
    pdf.info_row("Missing:", gdt_comp.get('missing_count', 0))
    pdf.info_row("Extra:", gdt_comp.get('extra_count', 0))
    pdf.ln(3)
    
    # Detailed breakdown
    details = gdt_comp.get('details', {})
    if details:
        pdf.set_font('Arial', 'I', 10)
        pdf.cell(0, 6, "Breakdown by Type:", 0, 1)
        pdf.set_font('Arial', '', 9)
        pdf.cell(100, 6, f"  Feature Control Frames: {details.get('student_fcf', 0)} / {details.get('master_fcf', 0)}", 0, 1)
        pdf.cell(100, 6, f"  DimXpert Annotations: {details.get('student_dimxpert', 0)} / {details.get('master_dimxpert', 0)}", 0, 1)
        pdf.cell(100, 6, f"  Datums: {details.get('student_datums', 0)} / {details.get('master_datums', 0)}", 0, 1)
        pdf.ln(3)
    
    # Status explanation and feedback
    pdf.set_font('Arial', '', 11)
    missing_count = gdt_comp.get('missing_count', 0)
    extra_count = gdt_comp.get('extra_count', 0)
    
    if gdt_score >= 95:
        pdf.set_text_color(0, 128, 0)
        pdf.multi_cell(0, 8, "[PASS] Excellent! All required GD&T annotations are correctly placed.")
    elif missing_count > 0 and extra_count == 0:
        pdf.set_text_color(255, 140, 0)
        pdf.multi_cell(0, 8, 
            f"[WARNING] Missing {missing_count} required GD&T annotation(s). "
            f"Please add the missing tolerances to meet specification.")
    elif missing_count > 0 and extra_count > 0:
        pdf.set_text_color(255, 140, 0)
        pdf.multi_cell(0, 8, 
            f"[WARNING] Mixed result: Missing {missing_count} required annotation(s) "
            f"but has {extra_count} additional annotation(s). Review carefully.")
    elif missing_count == 0 and extra_count > 0:
        pdf.set_text_color(0, 128, 0)
        pdf.multi_cell(0, 8, 
            f"[PASS] All required annotations present. Has {extra_count} additional "
            f"annotation(s) which may provide extra clarity.")
    elif gdt_comp.get('total_required', 0) == 0:
        pdf.set_text_color(128, 128, 128)
        pdf.multi_cell(0, 8, "[INFO] No GD&T requirements specified in master model.")
    else:
        pdf.set_text_color(255, 0, 0)
        pdf.multi_cell(0, 8, "[FAIL] No GD&T annotations found. Tolerancing is required.")
    
    pdf.set_text_color(0)
    
    # List missing annotations if any
    missing_anns = gdt_comp.get('missing_annotations', [])
    if missing_anns and len(missing_anns) <= 10:  # Only show if reasonable number
        pdf.ln(5)
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(0, 6, "Missing Annotations:", 0, 1)
        pdf.set_font('Arial', '', 9)
        for ann in missing_anns[:10]:  # Limit to 10 items
            # Truncate long annotations
            ann_text = ann if len(ann) <= 70 else ann[:67] + "..."
            pdf.multi_cell(0, 5, f"  - {ann_text}")
    
    # ============ OVERALL SUMMARY ============
    pdf.ln(10)
    pdf.section_header('Overall Assessment Summary')
    pdf.set_font('Arial', '', 11)
    
    # Calculate overall grade (weighted average: 60% accuracy, 40% GD&T)
    accuracy_percent = 100 - min(deviation * 10, 100)  # Scale deviation to percent
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
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, f"Overall Grade: {overall_grade} ({overall_score:.1f}/100)", 0, 1)
    pdf.set_text_color(0)
    pdf.set_font('Arial', '', 10)
    
    pdf.ln(5)
    pdf.set_font('Arial', 'I', 9)
    pdf.multi_cell(0, 6, 
        "Note: This is an automated assessment. Faculty review is recommended for "
        "final grading, especially in cases of plagiarism alerts or significant deviations.")
    
    pdf.output(output_pdf_path)
