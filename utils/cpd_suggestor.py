from __future__ import annotations
from typing import Optional
from utils.ml_unit_predictor import predict_unit_and_category
import json
import os

# Per-person/day priors by broad category and default unit
# Values are approximate; scaled by household_size and adjusted by cooking frequency.
PRIORS = {
    'grain_pulse': {'kg': 0.08},       # rice, atta, flours, dal
    'veg_leafy':   {'kg': 0.12},       # leafy veg
    'veg_root':    {'kg': 0.10},
    'fruit':       {'kg': 0.10},
    'dairy':       {'l': 0.18},
    'bakery':      {'pcs': 0.12},
    'oil':         {'l': 0.02},
    'snack':       {'pcs': 0.03},
}

COOKING_MULTIPLIER = {
    'mostly_home': 1.0,
    'mixed': 0.6,
    'mostly_out': 0.35,
}


def suggest_cpd(name: str, household_size: int = 2, cooking_freq: str = 'mostly_home', unit_hint: Optional[str] = None) -> float:
    unit_pred, cat = predict_unit_and_category(name or '')
    unit = unit_hint or unit_pred or 'kg'
    # Static priors from JSON if available
    per_person = None
    try:
        base_dir = os.path.dirname(os.path.dirname(__file__))
        path = os.path.join(base_dir, 'consumption_priors.json')
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            key = (name or '').lower()
            # exact and contains match
            for k, v in data.items():
                if k in key:
                    ppd = float(v.get('ppd') or 0)
                    unit_json = (v.get('unit') or unit)
                    if ppd > 0:
                        unit = unit_json or unit
                        per_person = ppd
                        break
    except Exception:
        pass
    # Fallback to category defaults
    if per_person is None:
        pri_unit_map = PRIORS.get(cat, {})
        per_person = 0.03
        if pri_unit_map:
            per_person = pri_unit_map.get(unit, next(iter(pri_unit_map.values())))
    mult = COOKING_MULTIPLIER.get(cooking_freq, 1.0)
    return round(max(0.0, per_person * max(1, household_size) * mult), 3)
