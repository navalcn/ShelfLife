"""
Default expiry durations (in days) for common food items
"""

# Default expiry in days for different food categories
DEFAULT_EXPIRY = {
    # Grains & Pulses
    'rice': 365, 'wheat': 180, 'dal': 180, 'pulses': 180, 'flour': 90,
    'besan': 90, 'rava': 90, 'poha': 60, 'vermicelli': 180,
    
    # Spices & Masalas
    'turmeric': 180, 'cumin': 180, 'coriander': 180, 'garam masala': 120,
    'chili powder': 120, 'mustard seeds': 180, 'fenugreek': 180, 'asafoetida': 365,
    'sambar powder': 120, 'rasam powder': 120, 'curry leaves': 7, 'cinnamon': 180,
    'cardamom': 180, 'cloves': 180, 'pepper': 180, 'fennel': 180,
    
    # Oils & Fats
    'oil': 180, 'ghee': 90, 'butter': 30, 'vanaspati': 180,
    
    # Dairy & Alternatives
    'milk': 2, 'curd': 3, 'paneer': 4, 'cheese': 7, 'cream': 5,
    'buttermilk': 2, 'khoya': 3, 'yogurt': 3,
    
    # Vegetables
    'potato': 14, 'onion': 21, 'tomato': 5, 'carrot': 10, 'beans': 5,
    'cabbage': 7, 'cauliflower': 5, 'brinjal': 4, 'ladyfinger': 3, 'cucumber': 5,
    'beetroot': 14, 'radish': 7, 'pumpkin': 14, 'capsicum': 7, 'ginger': 14,
    'garlic': 14, 'green chili': 5, 'lemon': 10, 'coriander leaves': 3,
    'mint leaves': 3, 'curry leaves': 5, 'spinach': 3, 'drumstick': 5,
    'raw banana': 7, 'yam': 14, 'sweet potato': 14,
    
    # Fruits
    'banana': 3, 'apple': 14, 'orange': 10, 'mango': 5, 'papaya': 3,
    'watermelon': 5, 'muskmelon': 5, 'grapes': 4, 'pomegranate': 14,
    
    # Nuts & Dry Fruits
    'cashew': 180, 'almond': 180, 'peanut': 90, 'raisin': 180, 'walnut': 180,
    'pistachio': 180, 'dates': 180, 'figs': 180, 'coconut': 30, 'grated coconut': 5,
    
    # Meat & Seafood
    'chicken': 2, 'mutton': 2, 'fish': 1, 'prawn': 1, 'egg': 14,
    
    # Packaged & Processed
    'pasta': 180, 'noodles': 180, 'biscuits': 90, 'chips': 60, 'sauce': 90,
    'ketchup': 90, 'jam': 180, 'pickle': 365, 'honey': 365, 'vinegar': 180,
    'soy sauce': 180, 'chocolate': 180, 'coffee': 180, 'tea': 180,
    
    # Default fallback
    'default': 7
}

import re

def get_default_expiry(item_name):
    """
    Get default expiry in days for a given item
    Returns tuple of (expiry_days, is_approximate)
    """
    item_lower = item_name.lower()
    
    # Exact match
    if item_lower in DEFAULT_EXPIRY:
        return DEFAULT_EXPIRY[item_lower], False
        
    # Partial match (e.g., 'red chili powder' contains 'chili powder') but only whole words
    for key, days in DEFAULT_EXPIRY.items():
        # Create a regex pattern that matches the key as a whole word
        pattern = r'\b' + re.escape(key) + r'\b'
        if re.search(pattern, item_lower):
            return days, True
            
    # Check categories
    if any(x in item_lower for x in ['masala', 'powder', 'spice']):
        return 120, True
    if any(x in item_lower for x in ['dal', 'lentil']):
        return 180, True
    if any(x in item_lower for x in ['vegetable', 'sabzi']):
        return 7, True
        
    return DEFAULT_EXPIRY['default'], True
