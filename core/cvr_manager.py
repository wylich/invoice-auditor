# core/cvr_manager.py
import httpx
import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

# MVP uses the free/freemium endpoint. 
# In production, we use an environment variable for a paid token if needed.
CVR_API_URL = "https://cvrapi.dk/api"

# Local cache file to survive API outages
CACHE_FILE = os.path.join(os.path.dirname(__file__), 'cvr_cache.json')

class CvrManager:
    def __init__(self):
        self.cache = self._load_cache()

    def _load_cache(self) -> Dict:
        """Loads local cache of trusted CVRs."""
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_cache(self):
        """Persists cache to disk."""
        with open(CACHE_FILE, 'w') as f:
            json.dump(self.cache, f, indent=2)

    def validate_cvr(self, cvr_number: str) -> Dict[str, Any]:
        """
        Main entry point. Returns a standardized Dict with compliance flags.
        """
        # 1. Clean input
        cvr_clean = str(cvr_number).strip().replace("DK", "")
        
        # 2. Check Cache first (Minimize API costs/latency)
        cached_data = self.cache.get(cvr_clean)
        if cached_data:
            last_checked = datetime.fromisoformat(cached_data['last_checked'])
            # If cache is fresh (< 7 days), use it
            if datetime.now() - last_checked < timedelta(days=7):
                return cached_data['data']

        # 3. Fetch from Live API
        try:
            # User-Agent is polite/required by some CVR APIs
            headers = {'User-Agent': 'InvoiceAgent-MVP/1.0'}
            params = {'search': cvr_clean, 'country': 'dk'}
            
            with httpx.Client(timeout=5.0) as client:
                response = client.get(CVR_API_URL, params=params, headers=headers)
                
            if response.status_code == 200:
                raw_data = response.json()
                analyzed_data = self._analyze_risk(raw_data)
                
                # Update Cache
                self.cache[cvr_clean] = {
                    'last_checked': datetime.now().isoformat(),
                    'data': analyzed_data
                }
                self._save_cache()
                return analyzed_data
            
            elif response.status_code == 404:
                return {"valid": False, "risk_level": "High", "message": "CVR number not found in registry."}
                
        except Exception as e:
            # GRACEFUL DEGRADATION:
            # If API fails but we have OLD cache, use it with a warning.
            if cached_data:
                data = cached_data['data']
                data['warning'] = "Offline Mode: Using cached data > 7 days old."
                return data
            return {"valid": False, "risk_level": "Unknown", "message": f"API Error: {str(e)}"}

        return {"valid": False, "risk_level": "High", "message": "Unknown error."}

    def _analyze_risk(self, api_data: Dict) -> Dict:
        """
        The 'Auditor' Logic: Translates raw JSON into Business Risk.
        """
        # Default benign state
        result = {
            "valid": True,
            "company_name": api_data.get('name'),
            "risk_level": "Low",
            "message": "Company is active and valid."
        }
        
        # RISK CHECK 1: Is it active?
        # 'hovedbranche' often implies active, but specific keys vary by API version.
        # cvrapi.dk typically implies active unless specific enddate is set.
        if api_data.get('enddate'):
             result["valid"] = False
             result["risk_level"] = "High"
             result["message"] = f"Company Dissolved (Ophørt) on {api_data.get('enddate')}"
             return result

        # RISK CHECK 2: Status Text Analysis
        # Some APIs return text status like "Under konkurs"
        status_text = str(api_data).lower() # Lazy search in full dump
        if "konkurs" in status_text:
            result["valid"] = False
            result["risk_level"] = "Critical"
            result["message"] = "WARNING: Company is Bankrupt (Under Konkurs)."
        elif "tvangsopløsning" in status_text:
             result["valid"] = False
             result["risk_level"] = "Critical"
             result["message"] = "WARNING: Forced Dissolution (Tvangsopløsning)."

        return result

# --- Usage Example ---
if __name__ == "__main__":
    cvr_agent = CvrManager()
    
    # Test with a known CVR (e.g., Lego System A/S)
    print(cvr_agent.validate_cvr("47458714"))

    # Test with a fake/bad CVR
    print(cvr_agent.validate_cvr("99999999"))