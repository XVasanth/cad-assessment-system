# frontend/app.py
import streamlit as st
import requests
import zipfile
from io import BytesIO
from datetime import datetime

st.set_page_config(layout="wide")
BACKEND_URL = "http://127.0.0.1:5000/analyze"

st.title("🎓 CAD Assessment System")
st.markdown("---")

st.header("1. Upload Master Model")
master_file = st.file_uploader("Upload the faculty's master SOLIDWORKS Part (`.SLDPRT`)", type=['sldprt'])
if master_file: st.success(f"Loaded master file: {master_file.name}")

st.markdown("---")

st.header("2. Upload Student Submissions")
student_zip_file = st.file_uploader("Select a ZIP file containing all student `.SLDPRT` files", type=['zip'])
if student_zip_file:
    try:
        with zipfile.ZipFile(BytesIO(student_zip_file.getvalue())) as zf:
            file_list = [f for f in zf.namelist() if f.lower().endswith('.sldprt') and not f.startswith('__MACOSX')]
            st.info(f"Found {len(file_list)} student files inside {student_zip_file.name}")
    except zipfile.BadZipFile:
        st.error("This is not a valid ZIP file.")

st.markdown("---")

if st.button("🚀 Begin Analysis & Generate Reports", type="primary"):
    if not master_file or not student_zip_file:
        st.warning("⚠️ Please upload both a master file and a student ZIP file.")
    else:
        with st.spinner("Processing... This may take several minutes depending on the number of files."):
            files = {
                'master_file': (master_file.name, master_file.getvalue()),
                'student_zip': (student_zip_file.name, student_zip_file.getvalue())
            }
            try:
                response = requests.post(BACKEND_URL, files=files, timeout=600)
                if response.status_code == 200:
                    st.success("✅ Analysis Complete! Your reports are ready for download.")
                    st.download_button(
                        label="📥 Download All PDF Reports (.zip)",
                        data=response.content,
                        file_name=f"CAD_Reports_{datetime.now().strftime('%Y%m%d')}.zip",
                        mime="application/zip"
                    )
                else:
                    st.error(f"Server error: {response.status_code} - {response.text}")
            except requests.exceptions.RequestException as e:
                st.error(f"Connection to backend failed. Is it running? Details: {e}")
