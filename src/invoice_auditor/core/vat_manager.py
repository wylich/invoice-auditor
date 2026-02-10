# core/vat_manager.py
import json
import logging
from pathlib import Path
from typing import Tuple, Dict

logger = logging.getLogger(__name__)

LOOKUP_FILE = Path(__file__).parent / ".." / "storage" / "vat_lookup.json"


class VatManager:
    def __init__(self):
        self.rules = self._load_rules()

    def _load_rules(self) -> Dict:
        """Loads the JSON dictionary from disk."""
        try:
            rules = json.loads(LOOKUP_FILE.read_text(encoding="utf-8"))
            logger.info("Loaded %d VAT rules from %s", len(rules.get("exempt_keywords", [])), LOOKUP_FILE)
            return rules
        except FileNotFoundError:
            logger.warning("VAT lookup file not found at %s, using defaults", LOOKUP_FILE)
            return {"exempt_keywords": [], "standard_defaults": {"vat_rate": 0.25}}

    def lookup_item(self, description: str) -> Tuple[float, str, str]:
        """
        Analyzes a line item description to determine VAT.
        Returns: (vat_rate, category, reason)
        """
        desc_upper = description.upper()

        for rule in self.rules.get("exempt_keywords", []):
            if rule["keyword"] in desc_upper:
                return (rule["vat_rate"], rule["category"], rule["reason"])

        defaults = self.rules.get("standard_defaults", {})
        return (defaults.get("vat_rate", 0.25),
                defaults.get("category", "Standard (25%)"),
                "Standard Rate")

    def add_custom_rule(self, keyword: str, vat_rate: float, category: str):
        """Adds a new keyword to the JSON file based on user feedback."""
        new_rule = {
            "keyword": keyword.upper(),
            "vat_rate": vat_rate,
            "category": category,
            "reason": "User Custom Rule"
        }

        existing = [r["keyword"] for r in self.rules["exempt_keywords"]]
        if new_rule["keyword"] not in existing:
            self.rules["exempt_keywords"].append(new_rule)
            self._save_rules()
            return True
        return False

    def _save_rules(self):
        LOOKUP_FILE.write_text(json.dumps(self.rules, indent=2, ensure_ascii=False), encoding="utf-8")
