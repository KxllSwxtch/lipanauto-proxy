"""
KZ Model Name Mapper Service
Maps Encar model names to kz-table.xlsx model names

This service handles the discrepancy between detailed Encar model names
(e.g., "The New Sorento 4") and simplified kz-table.xlsx names (e.g., "SORENTO")
"""

from typing import Optional, Dict
import re


class KZModelNameMapper:
    """
    Service to normalize and map Encar model names to kz-table.xlsx model names
    """

    # Known model name mappings (Encar name → kz-table name)
    MODEL_MAPPINGS: Dict[str, str] = {
        # Kia models
        "the new sorento": "sorento",
        "the new sorento 4": "sorento",
        "all new sorento": "sorento",
        "new sorento": "sorento",
        "sorento r": "sorento",
        "the new k5": "k5",
        "all new k5": "k5",
        "new k5": "k5",
        "the new k8": "k8",
        "all new k8": "k8",
        "new k8": "k8",
        "the new k9": "k9",
        "all new k9": "k9",
        "new k9": "k9",
        "the new carnival": "carnival",
        "all new carnival": "carnival",
        "new carnival": "carnival",
        "the new sportage": "sportage",
        "all new sportage": "sportage",
        "new sportage": "sportage",

        # Hyundai models
        "the new grandeur": "grandeur",
        "all new grandeur": "grandeur",
        "new grandeur": "grandeur",
        "the new avante": "avante",
        "all new avante": "avante",
        "new avante": "avante",
        "the new sonata": "sonata",
        "all new sonata": "sonata",
        "new sonata": "sonata",
        "the new tucson": "tucson",
        "all new tucson": "tucson",
        "new tucson": "tucson",
        "the new santa fe": "santa fe",
        "all new santa fe": "santa fe",
        "new santa fe": "santa fe",

        # Genesis models
        "genesis g70": "g70",
        "genesis g80": "g80",
        "genesis g90": "g90",
        "genesis gv70": "gv70",
        "genesis gv80": "gv80",

        # Add more mappings as needed
    }

    # Patterns to strip from model names
    STRIP_PATTERNS = [
        r"the new\s+",
        r"all new\s+",
        r"new\s+",
        r"\d{1,2}세대",  # Generation markers (e.g., "5세대")
        r"\s+\d{1,2}$",  # Trailing generation numbers (e.g., "Sorento 4")
        r"\s+r$",  # R suffix
        r"\s+hybrid$",  # Hybrid suffix (sometimes)
        r"\s+electric$",  # Electric suffix
        r"\s+ev$",  # EV suffix
    ]

    def normalize_model_name(self, model: str) -> str:
        """
        Normalize a model name by:
        1. Converting to lowercase
        2. Removing common prefixes/suffixes
        3. Trimming whitespace

        Args:
            model: Raw model name from Encar

        Returns:
            Normalized model name
        """
        if not model:
            return ""

        # Convert to lowercase
        normalized = model.lower().strip()

        # Apply strip patterns
        for pattern in self.STRIP_PATTERNS:
            normalized = re.sub(pattern, "", normalized, flags=re.IGNORECASE)

        # Clean up multiple spaces
        normalized = re.sub(r"\s+", " ", normalized).strip()

        return normalized

    def map_model_name(self, manufacturer: str, model: str) -> str:
        """
        Map Encar model name to kz-table.xlsx model name

        Strategy:
        1. Check direct mapping in MODEL_MAPPINGS
        2. Try normalized version
        3. Return original if no mapping found

        Args:
            manufacturer: Car manufacturer (e.g., "Kia", "Hyundai")
            model: Model name from Encar (e.g., "The New Sorento 4")

        Returns:
            Model name compatible with kz-table.xlsx
        """
        if not model:
            return model

        # Normalize the model name
        normalized = self.normalize_model_name(model)

        # Check direct mapping (case-insensitive)
        normalized_lower = normalized.lower()
        if normalized_lower in self.MODEL_MAPPINGS:
            mapped = self.MODEL_MAPPINGS[normalized_lower]
            print(f"📋 Model name mapped: '{model}' → '{mapped}'")
            return mapped

        # If no mapping found, return normalized version
        print(f"📋 Model name normalized: '{model}' → '{normalized}'")
        return normalized

    def add_mapping(self, from_name: str, to_name: str):
        """
        Add a custom model name mapping

        Args:
            from_name: Source model name (will be normalized)
            to_name: Target model name in kz-table.xlsx
        """
        normalized_from = self.normalize_model_name(from_name)
        self.MODEL_MAPPINGS[normalized_from.lower()] = to_name.lower()
        print(f"✅ Added model mapping: '{from_name}' → '{to_name}'")

    def get_all_mappings(self) -> Dict[str, str]:
        """Get all current model name mappings"""
        return self.MODEL_MAPPINGS.copy()


# Global singleton instance
kz_model_name_mapper = KZModelNameMapper()
