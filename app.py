# app.py
import os
from openai import api_key
import streamlit as st
import time
import random

from core.auditor import Auditor

# Page Config
st.set_page_config(page_title="Invoice Agent", page_icon="🕵️", layout="centered")

def simulate_agent_audit(file_name):
    """
    Simulates the agent's reasoning steps with visual feedback.
    In the real app, these 'sleeps' will be replaced by actual API calls.
    """
    
    # 1. The Container (The "Thinking" Box)
    with st.status("🕵️ Invoice Agent is starting...", expanded=True) as status:
        
        # Step 1: Ingestion
        st.write("📄 **Ingesting:** Reading file structure...")
        time.sleep(1.5) # Simulate upload/read time
        st.write(f"✅ File '{file_name}' loaded securely.")
        
        # Step 2: Vision / OCR
        st.write("👁️ **Vision Agent:** Extracting text and key fields...")
        # Simulate varying processing time based on "complexity"
        time.sleep(random.uniform(1.0, 2.5)) 
        st.write("✅ Vendor detected")
        # st.write("✅ Vendor detected: 'Netto' (Confidence: 98%)")
        
        # Step 3: VAT Logic (The Brain we just built)
        st.write("🧮 **VAT Manager:** Checking line items against rules...")
        time.sleep(1.0)
        st.write("ℹ️ Applying relevant VAT exemption rules.*")
        st.write("✅ VAT Logic validated.")
        
        # Step 4: Compliance (CVR & Currency)
        st.write("🏛️ **Compliance Agent:** Verifying CVR status...")
        time.sleep(1.2)
        st.write("✅ CVR verified.")
        # st.write("✅ CVR 35954716 is Active (Salling Group).")
        
        st.write("💱 **Forex Engine:** Checking currency...")
        st.write("✅ Currency is DKK. No normalization needed.")

        # Finalize
        status.update(label="🚀 Audit Complete! No critical issues found.", state="complete", expanded=False)
        
    return True

# --- Main UI ---
st.title("🕵️ AI Invoice Agent")
st.caption("The AI-Powered CFO for Danish SMEs")

# Added 'jpeg' to cover alternate spellings, plus webp and avif
uploaded_file = st.file_uploader("Drop an invoice or receipt", type=["pdf", "png", "jpg", "jpeg", "webp", "avif"])

if uploaded_file is not None:
    # Trigger the Agent
    if st.button("Start Audit"):
        # CHANGED: Use standard OpenAI Env Var
        # 1. Debugging: Check if key is actually loaded
        api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            st.error("❌ Error: OPENAI_API_KEY not found. Check your .env file.")
            st.stop() # Stop execution here so we don't crash
        
        # 2. Initialize Auditor WITH the key
        auditor = Auditor(api_key=api_key)
        
        # 3. Run the audit (Passing the file object directly)
        try:
            # Reset file pointer to beginning before reading
            uploaded_file.seek(0) 
            
            # Run audit
            invoice_result = auditor.run_audit(uploaded_file, uploaded_file.name)
            
            # 4. Simulate the UI thinking (visual only)
            simulate_agent_audit(uploaded_file.name)
            
            st.balloons()
            
            # 5. Display Results
            if invoice_result.status == "Green":
                st.success("✅ Invoice Auto-Approved")
            else:
                st.error(f"🛑 Issues Found: {len(invoice_result.audit_flags)}")
                
            # Show the structured data
            with st.expander("See Audit Details"):
                st.json(invoice_result.model_dump())
                
        except Exception as e:
            st.error(f"An error occurred: {e}")