import json
import os
from datetime import date, timedelta

_EXPIRY_CACHE = None


def _load_expiry_data():
    global _EXPIRY_CACHE
    if _EXPIRY_CACHE is not None:
        return _EXPIRY_CACHE
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'expiry_data.json')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            _EXPIRY_CACHE = json.load(f)
    except Exception:
        _EXPIRY_CACHE = {}
    return _EXPIRY_CACHE


def get_default_shelf_life_days(product_name: str):
    data = _load_expiry_data()
    if not product_name:
        return None
    key = product_name.strip().lower()
    # exact match
    if key in data:
        return int(data[key])
    # fallback: startswith match
    for k, v in data.items():
        if key.startswith(k):
            return int(v)
    return None


def compute_status(expiry: date | None, today: date | None = None):
    """Return tuple(status, days_left).
    status in {'expired', 'soon', 'fresh', 'unknown'}
    """
    if today is None:
        today = date.today()
    if not expiry:
        return 'unknown', None
    delta = (expiry - today).days
    if delta < 0:
        return 'expired', delta
    if delta <= 3:
        return 'soon', delta
    return 'fresh', delta


def predict_finish_date(consumption_per_day: float | None, remaining: float | None, today: date | None = None):
    if today is None:
        today = date.today()
    
    # If no consumption rate, can't predict
    if not consumption_per_day or consumption_per_day <= 0:
        return None
    
    # If no remaining quantity, it's already finished (return today)
    if remaining is None or remaining <= 0:
        return today
    
    # Calculate days until empty
    days = int(remaining / consumption_per_day)
    return today + timedelta(days=days)
    for item_name, days in all_items.items():
        if item_name in key or key in item_name:
            return days
    
    # Fallback to category-based heuristics
    def has_any(words):
        return any(w in key for w in words)

    # Category fallbacks with updated values
    if has_any(['rice', 'atta', 'maida', 'flour', 'wheat', 'besan', 'dal', 'lentil', 'rava', 'sooji']):
        return 180  # 6 months for staples
    if has_any(['oil', 'ghee', 'vinegar']):
        return 365  # 1 year for oils
    if has_any(['spinach', 'palak', 'coriander', 'mint', 'greens', 'lettuce']):
        return 3    # 3 days for leafy greens
    if has_any(['potato', 'onion', 'carrot', 'ginger', 'garlic']):
        return 21   # 3 weeks for root vegetables
    if has_any(['tomato', 'cucumber', 'brinjal', 'okra', 'capsicum']):
        return 7    # 1 week for other vegetables
    if has_any(['banana', 'apple', 'mango', 'orange', 'grape', 'papaya', 'guava']):
        return 5    # 5 days for fruits
    if has_any(['bread', 'bun', 'roti', 'chapati']):
        return 3    # 3 days for bread items
    if has_any(['milk', 'curd', 'yogurt', 'paneer', 'cheese', 'butter', 'cream']):
        if 'paneer' in key:
            return 3
        if 'cheese' in key:
            return 21
        if 'butter' in key:
            return 30
        return 2    # 2 days for milk/curd
    if has_any(['chicken', 'mutton', 'fish', 'meat', 'egg']):
        if 'egg' in key:
            return 21
        return 2    # 2 days for fresh meat/fish


def compute_status(expiry: date | None, today: date | None = None):
    """Return tuple(status, days_left).
    status in {'expired', 'soon', 'fresh', 'unknown'}
    """
    if today is None:
        today = date.today()
    if not expiry:
        return 'unknown', None
    delta = (expiry - today).days
    if delta < 0:
        return 'expired', delta
    if delta <= 3:
        return 'soon', delta
    return 'fresh', delta


def predict_finish_date(consumption_per_day: float | None, remaining: float | None, today: date | None = None):
    if today is None:
        today = date.today()
    
    # If no consumption rate, can't predict
    if not consumption_per_day or consumption_per_day <= 0:
        return None
    
    # If no remaining quantity, it's already finished (return today)
    if remaining is None or remaining <= 0:
        return today
    
    # Calculate days until empty
    days = int(remaining / consumption_per_day)
    return today + timedelta(days=days)
