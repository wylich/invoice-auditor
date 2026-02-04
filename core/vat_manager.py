# core/vat_manager.py
import json
import os
from typing import Tuple, Dict

# Path to JSON lookup file
LOOKUP_FILE = os.path.join(os.path.dirname(__file__), 'vat_lookup.json')

class VatManager:
    def __init__(self):
        self.rules = self._load_rules()

    def _load_rules(self) -> Dict:
        """Loads the JSON dictionary from disk."""
        try:
            with open(LOOKUP_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            # Fallback if file is missing
            return {"exempt_keywords": [], "standard_defaults": {"vat_rate": 0.25}}

    def lookup_item(self, description: str) -> Tuple[float, str, str]:
        """
        Analyzes a line item description to determine VAT.
        Returns: (vat_rate, category, reason)
        """
        desc_upper = description.upper()

        # 1. Check against Exempt/0% Keywords
        for rule in self.rules.get("exempt_keywords", []):
            if rule["keyword"] in desc_upper:
                return (rule["vat_rate"], rule["category"], rule["reason"])

        # 2. Default to Standard 25% if no special keyword found
        defaults = self.rules.get("standard_defaults", {})
        return (defaults.get("vat_rate", 0.25), 
                defaults.get("category", "Standard (25%)"), 
                "Standard Rate")

    def add_custom_rule(self, keyword: str, vat_rate: float, category: str):
        """
        The 'Learning' mechanism. 
        Adds a new keyword to the JSON file based on user feedback.
        """
        new_rule = {
            "keyword": keyword.upper(),
            "vat_rate": vat_rate,
            "category": category,
            "reason": "User Custom Rule"
        }
        
        # Avoid duplicates
        existing = [r["keyword"] for r in self.rules["exempt_keywords"]]
        if new_rule["keyword"] not in existing:
            self.rules["exempt_keywords"].append(new_rule)
            self._save_rules()
            return True
        return False

    def _save_rules(self):
        with open(LOOKUP_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.rules, f, indent=2, ensure_ascii=False)

# --- Usage Example ---
if __name__ == "__main__":
    vat_agent = VatManager()
    
    # Test Cases
    items = ["Arla Sødmælk", "Politiken Avis Søndag", "Coca Cola + Pant A"]
    
    for item in items:
        rate, cat, reason = vat_agent.lookup_item(item)
        print(f"Item: {item} | VAT: {rate*100}% | Reason: {reason}")