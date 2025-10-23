from __future__ import annotations
from typing import Tuple

# Placeholder ML predictor with rule fallback.
# Later we can load a sklearn model and use it when present.

CATEGORIES = {
    'veg_leafy': ['spinach', 'greens', 'mint', 'coriander', 'leaf'],
    'veg_root': ['potato', 'onion', 'carrot', 'beet', 'ginger', 'garlic'],
    'fruit': ['banana', 'apple', 'mango', 'orange', 'grape', 'papaya', 'guava'],
    'dairy': ['milk', 'curd', 'yogurt', 'paneer', 'cheese', 'butter', 'cream'],
    'grain_pulse': ['rice', 'dal', 'lentil', 'bean', 'peas', 'atta', 'maida', 'flour', 'wheat'],
    'oil': ['oil', 'ghee', 'vinegar'],
    'bakery': ['bread', 'bun', 'biscuit', 'cookie'],
    'snack': ['noodle', 'noodles', 'sachet', 'chocolate'],
}


def predict_unit_and_category(name: str) -> Tuple[str, str]:
    n = (name or '').lower()
    # Unit heuristic first
    if any(k in n for k in ['milk', 'curd', 'lassi', 'buttermilk', 'yogurt', 'dahi', 'cream', 'oil', 'ghee', 'juice', 'vinegar']):
        unit = 'l'
    elif any(k in n for k in ['egg', 'eggs', 'dozen', 'bread', 'bun', 'biscuit', 'cookie', 'pack', 'packet', 'chocolate', 'bar']):
        unit = 'pcs'
    else:
        unit = 'kg'
    # Category heuristic
    cat = 'other'
    for c, keys in CATEGORIES.items():
        if any(k in n for k in keys):
            cat = c
            break
    return unit, cat
