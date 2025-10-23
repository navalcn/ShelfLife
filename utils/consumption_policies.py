import re

def is_single_use(name: str) -> bool:
    if not name:
        return False
    n = name.lower()
    keywords = [
        'corn', 'sweet corn',      # corn packs
        'biscuit', 'biscuits',
        'noodle', 'noodles', 'noodles pack',
        'masala sachet', 'sachet',
        'chocolate bar', 'chocolate',
        'mushroom', 'button mushroom',
    ]
    if any(k in n for k in keywords):
        return True
    # Pack-size hints like 200g, 250 g, 500ml, x1
    if re.search(r"\b\d+\s*(g|ml)\b", n):
        return True
    if re.search(r"\bx1\b", n):
        return True
    if 'pack' in n:
        return True
    return False
