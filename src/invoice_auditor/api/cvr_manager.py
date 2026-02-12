# api/cvr_manager.py
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

import httpx

from invoice_auditor.config import settings

logger = logging.getLogger(__name__)


class CvrManager:
    def __init__(self):
        self.cache = self._load_cache()

    def _load_cache(self) -> Dict:
        """Loads local cache of trusted CVRs."""
        if settings.cvr_cache_path.exists():
            try:
                return json.loads(settings.cvr_cache_path.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _save_cache(self):
        """Persists cache to disk."""
        settings.cvr_cache_path.write_text(json.dumps(self.cache, indent=2), encoding="utf-8")

    async def validate_cvr(self, cvr_number: str, client: httpx.AsyncClient) -> Dict[str, Any]:
        """
        Main entry point. Returns a standardized Dict with compliance flags.
        """
        cvr_clean = str(cvr_number).strip().replace("DK", "")

        # Check Cache first
        cached_data = self.cache.get(cvr_clean)
        if cached_data:
            last_checked = datetime.fromisoformat(cached_data['last_checked'])
            if datetime.now() - last_checked < timedelta(days=settings.cvr_api.cache_days):
                logger.debug("CVR %s: cache hit (checked %s)", cvr_clean, cached_data['last_checked'])
                return cached_data['data']

        # Fetch from Live API
        logger.info("CVR %s: querying %s", cvr_clean, settings.cvr_api.url)
        try:
            headers = {'User-Agent': 'InvoiceAgent-MVP/2.0'}
            params = {'search': cvr_clean, 'country': 'dk'}

            response = await client.get(settings.cvr_api.url, params=params, headers=headers)

            if response.status_code == 200:
                raw_data = response.json()
                analyzed_data = self._analyze_risk(raw_data)

                self.cache[cvr_clean] = {
                    'last_checked': datetime.now().isoformat(),
                    'data': analyzed_data
                }
                self._save_cache()
                logger.info("CVR %s: %s (risk=%s)", cvr_clean, analyzed_data['message'], analyzed_data['risk_level'])
                return analyzed_data

            elif response.status_code == 404:
                logger.warning("CVR %s: not found in registry", cvr_clean)
                return {"valid": False, "risk_level": "High", "message": "CVR number not found in registry."}

        except Exception as e:
            logger.error("CVR %s: API request failed: %s", cvr_clean, e)
            if cached_data:
                data = cached_data['data']
                data['warning'] = "Offline Mode: Using cached data > 7 days old."
                return data
            return {"valid": False, "risk_level": "Unknown", "message": f"API Error: {str(e)}"}

        return {"valid": False, "risk_level": "High", "message": "Unknown error."}

    def _analyze_risk(self, api_data: Dict) -> Dict:
        """Translates raw JSON into Business Risk."""
        result = {
            "valid": True,
            "company_name": api_data.get('name'),
            "risk_level": "Low",
            "message": "Company is active and valid."
        }

        if api_data.get('enddate'):
            result["valid"] = False
            result["risk_level"] = "High"
            result["message"] = f"Company Dissolved (Ophørt) on {api_data.get('enddate')}"
            return result

        status_text = str(api_data).lower()
        if "konkurs" in status_text:
            result["valid"] = False
            result["risk_level"] = "Critical"
            result["message"] = "WARNING: Company is Bankrupt (Under Konkurs)."
        elif "tvangsopløsning" in status_text:
            result["valid"] = False
            result["risk_level"] = "Critical"
            result["message"] = "WARNING: Forced Dissolution (Tvangsopløsning)."

        return result
