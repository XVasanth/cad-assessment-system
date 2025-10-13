# frontend/app.py
import streamlit as st, requests
from datetime import datetime

st.set_page_config(layout="wide")
BACKEND_URL = "http://127.0.0.1:5000/analyze"

st.title("🎓 Comprehensive CAD Assessment System")
st.markdown("---")

st.header("1. Upload Faculty's Base Model")
st.info("The standard `.SLDPRT` file with required GD&T annotations.")
master_file = st.file_uploader("Upload the Faculty Base Part", type=['sldprt'], key="master")

st.header("2. Upload All Student Submissions")
st.info("Place all student `.SLDPRT` files (named `RegNo_PartName.sldprt`) into a single `.ZIP` archive.")
student_zip_file = st.file_uploader("Upload the Student Submissions ZIP file", type=['zip'], key="students")

st.markdown("---")

if st.button("🚀 Begin Full Analysis", type="primary"):
    if not master_file or not student_zip_file:
        st.warning("⚠️ Please upload both the base file and the student ZIP file.")
    else:
        with st.spinner("Analyzing all submissions... This may take several minutes."):
            files = {'master_file': master_file, 'student_zip': student_zip_file}
            try:
                response = requests.post(BACKEND_URL, files=files, timeout=900) # 15 min timeout
                if response.status_code == 200:
                    st.success("✅ Analysis Complete!")
                    st.download_button(
                        label="📥 Download All Reports (ZIP)",
                        data=response.content,
                        file_name=f"CAD_Reports_{datetime.now().strftime('%Y%m%d')}.zip",
                        mime="application/zip"
                    )
                else:
                    st.error(f"Server error: {response.status_code} - {response.text}")
            except requests.exceptions.RequestException as e:
                st.error(f"Connection to backend failed. Is it running? Details: {e}")
