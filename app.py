# app.py
import asyncio
import logging

from dotenv import load_dotenv
import streamlit as st

load_dotenv()

from invoice_auditor.agent.auditor import run_audit

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)

# Page Config
st.set_page_config(page_title="Invoice Agent", page_icon="🕵️", layout="centered")

# --- Main UI ---
st.title("🕵️ AI Invoice Agent")
st.caption("The AI-Powered CFO for Danish SMEs")

uploaded_file = st.file_uploader("Drop an invoice or receipt", type=["pdf", "png", "jpg", "jpeg", "webp", "avif"])

if uploaded_file is not None:
    if st.button("Start Audit"):
        with st.status("🕵️ Invoice Agent is auditing...", expanded=True) as status:
            st.write("📄 Processing image...")

            try:
                uploaded_file.seek(0)
                invoice_result = asyncio.run(run_audit(uploaded_file, uploaded_file.name))

                status.update(label="🚀 Audit Complete!", state="complete", expanded=False)

                st.balloons()

                if invoice_result.status == "Green":
                    st.success("✅ Invoice Auto-Approved")
                elif invoice_result.status == "Review":
                    st.warning(f"⚠️ Review Needed: {len(invoice_result.audit_flags)} flag(s)")
                else:
                    st.error(f"🛑 Issues Found: {len(invoice_result.audit_flags)}")

                with st.expander("See Audit Details"):
                    st.json(invoice_result.model_dump())

            except Exception as e:
                logging.getLogger(__name__).error("Audit failed for %s: %s", uploaded_file.name, e, exc_info=True)
                status.update(label="❌ Audit Failed", state="error", expanded=False)
                st.error(f"An error occurred: {e}")
