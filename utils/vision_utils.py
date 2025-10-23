import io
import os
import re
from datetime import datetime
from typing import List, Dict, Any

import easyocr
try:
    import torch
except Exception:  # pragma: no cover
    torch = None
from utils.ai_receipt import parse_receipt_with_donut, DonutUnavailable


def extract_items_from_bill(image_path: str):
    """Extract basic items from a grocery bill image using Donut first, then EasyOCR fallback.

    Returns a list of dicts: {name, quantity, unit, price?}
    """
    text = ''
    meta = {
        'engine': 'donut+easyocr',
        'langs': ['en'],
        'error': None,
        'donut_used': False,
    }
    # Try Donut
    items: list[dict] = []
    raw_json = None
    try:
        donut_res = parse_receipt_with_donut(image_path)
        raw_json = donut_res.get('raw')
        items = donut_res.get('items') or []
        if items:
            meta['donut_used'] = True
    except DonutUnavailable as _:
        pass
    except Exception as e:
        meta['error'] = f"donut: {e}"

    # Always dump Donut raw JSON for debugging
    try:
        donut_dump = os.path.join(os.path.dirname(image_path), '_last_donut.json')
        with open(donut_dump, 'w', encoding='utf-8') as f:
            f.write(raw_json or '')
    except Exception:
        pass
    meta['donut_items'] = len(items)
    # If Donut produced items, short-circuit after writing meta
    if items:
        try:
            meta_path = os.path.join(os.path.dirname(image_path), '_last_ocr_meta.txt')
            with open(meta_path, 'w', encoding='utf-8') as f:
                for k, v in meta.items():
                    f.write(f"{k}: {v}\n")
        except Exception:
            pass
        return items

    # Fallback to EasyOCR to extract text and parse
    try:
        use_gpu = bool(torch and torch.cuda.is_available())
        reader = easyocr.Reader(['en'], gpu=use_gpu)
        results = reader.readtext(image_path, detail=1, paragraph=False)
        lines = [r[1] for r in results if isinstance(r, (list, tuple)) and len(r) >= 2]
        text = "\n".join([ln.strip() for ln in lines if str(ln).strip()])
    except Exception as e:
        meta['error'] = (meta['error'] or '') + f"; easyocr: {e}"
        text = ''

    # Write OCR dump for debugging next to the uploaded file
    try:
        dump_path = os.path.join(os.path.dirname(image_path), '_last_ocr.txt')
        with open(dump_path, 'w', encoding='utf-8') as f:
            f.write(text or '')
    except Exception:
        pass

    # Write meta
    try:
        meta_path = os.path.join(os.path.dirname(image_path), '_last_ocr_meta.txt')
        with open(meta_path, 'w', encoding='utf-8') as f:
            for k, v in meta.items():
                f.write(f"{k}: {v}\n")
    except Exception:
        pass

    lines = [ln.strip() for ln in text.split('\n') if ln.strip()]
    items = []

    # Enhanced patterns for Indian grocery bills
    hsn_like = re.compile(r'^[0-9]{6,}$')
    ean_like = re.compile(r'^EAN[#:]?\s*[0-9]{10,}$', re.I)
    
    # Improved name pattern for Indian products
    name_like = re.compile(r'^[A-Za-z][A-Za-z\s\-/&\.]+?(?:\s+(?:KG|EA|PKT|PACK|PCS|G|ML|L|PP|RD|DELI|CK|CHOCO|MUSHROOM))?$', re.I)
    
    # Enhanced numeric patterns for Indian bill formats
    # Pattern 1: QTY MRP OurPrice Total (Reliance Fresh format)
    numeric_row1 = re.compile(
        r'(?P<qty>\d+(?:[\.,]\d{1,3})?)\s+(?P<mrp>\d+(?:[\.,]\d{1,2})?)\s+(?P<price>\d+(?:[\.,]\d{1,2})?)\s+(?P<total>\d+(?:[\.,]\d{1,2})?)'
    )
    
    # Pattern 2: Traditional format
    numeric_row2 = re.compile(
        r'(?P<price>\d+(?:[\.,]\d{1,2})?)\s+(?P<qty>\d+(?:[\.,]\d{1,3})?)\s+(?P<value>\d+(?:[\.,]\d{1,2})?)'
    )
    
    # Pattern 3: Single line with product name and numbers
    product_line = re.compile(
        r'^([A-Za-z][A-Za-z\s\-/&\.]+?)\s+(\d+(?:[\.,]\d{1,3})?)\s+(\d+(?:[\.,]\d{1,2})?)\s+(\d+(?:[\.,]\d{1,2})?)\s+(\d+(?:[\.,]\d{1,2})?)$'
    )

    pending_name: str | None = None
    pending_unit: str | None = None
    
    # Common Indian grocery units
    unit_mapping = {
        'KG': 'kg', 'G': 'g', 'L': 'l', 'ML': 'ml',
        'PCS': 'pcs', 'PKT': 'pack', 'PACK': 'pack', 'EA': 'pcs',
        'PP': 'pack', 'DELI': 'pack', 'RD': 'kg'
    }

    def _norm_float(s: str) -> float:
        return float(s.replace(',', '.'))

    for ln in lines:
        # Skip HSN codes and EAN codes
        if hsn_like.match(ln) or ean_like.match(ln):
            continue
            
        # Try single-line product pattern first (for Reliance Fresh format)
        product_match = product_line.match(ln)
        if product_match:
            name = product_match.group(1).strip()
            qty = _norm_float(product_match.group(2))
            price = _norm_float(product_match.group(5))  # Total price
            
            # Extract unit from name if present
            unit = ''
            unit_match = re.search(r'\b(KG|G|L|ML|PCS|PKT|PACK|PP|RD)\b', name, re.I)
            if unit_match:
                unit = unit_mapping.get(unit_match.group(1).upper(), unit_match.group(1).lower())
                # Clean unit from name
                name = re.sub(r'\s+\b(KG|G|L|ML|PCS|PKT|PACK|PP|RD)\b', '', name, flags=re.I).strip()
            
            items.append({
                'name': name,
                'quantity': qty,
                'unit': unit,
                'price': price,
            })
            continue

        # Check for product names
        m_name = name_like.match(ln)
        if m_name:
            pending_name = ln
            unit_match = re.search(r'\b(KG|EA|PKT|PACK|PCS|G|ML|L|PP|RD|DELI|CK)\b', ln, re.I)
            if unit_match:
                pending_unit = unit_mapping.get(unit_match.group(1).upper(), unit_match.group(1).lower())
                # Clean unit from name
                pending_name = re.sub(r'\s+\b(KG|EA|PKT|PACK|PCS|G|ML|L|PP|RD|DELI|CK)\b', '', pending_name, flags=re.I).strip()
            else:
                pending_unit = ''
            continue

        # Try numeric patterns
        m_num1 = numeric_row1.search(ln)
        m_num2 = numeric_row2.search(ln)
        
        if (m_num1 or m_num2) and pending_name:
            try:
                if m_num1:
                    qty = _norm_float(m_num1.group('qty'))
                    price = _norm_float(m_num1.group('total'))
                else:
                    qty = _norm_float(m_num2.group('qty'))
                    price = _norm_float(m_num2.group('value'))
            except Exception:
                qty = 1.0
                price = None
                
            items.append({
                'name': pending_name,
                'quantity': qty,
                'unit': pending_unit or '',
                'price': price,
            })
            pending_name = None
            pending_unit = None

    # Enhanced fallback: try to extract specific Indian grocery items
    if not items:
        # First, try to parse the specific Reliance Fresh format from OCR text
        reliance_items = []
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Look for product names that match Reliance Fresh pattern
            if re.match(r'^[A-Z][A-Z\s\-]+(?:\s+(?:RD|PP|CK|DELI|Kg|Try))*$', line, re.I):
                product_name = line
                
                # Clean up the product name
                product_name = re.sub(r'\s+(RD|PP|CK|DELI|Kg|Try)\s*$', '', product_name, flags=re.I).strip()
                
                # Look ahead for quantity and price info
                qty = 1.0
                price = None
                unit = ''
                
                # Check next few lines for numbers
                for j in range(i + 1, min(i + 6, len(lines))):
                    next_line = lines[j].strip()
                    
                    # Skip EAN codes
                    if next_line.startswith('EAN#'):
                        continue
                    
                    # Look for quantity (decimal number less than 10)
                    qty_match = re.match(r'^(\d+(?:\.\d{1,3})?)$', next_line)
                    if qty_match and float(qty_match.group(1)) < 10:
                        qty = float(qty_match.group(1))
                        continue
                    
                    # Look for price patterns (numbers with .00)
                    price_match = re.match(r'^(\d+(?:\.\d{2}))$', next_line)
                    if price_match:
                        potential_price = float(price_match.group(1))
                        if potential_price > 10:  # Likely a total price
                            price = potential_price
                            break
                
                # Determine unit from original line
                if 'Kg' in line:
                    unit = 'kg'
                elif 'PP' in line or 'DELI' in line or 'CK' in line:
                    unit = 'pack'
                elif 'Try' in line:
                    unit = 'pcs'
                
                if price:  # Only add if we found a price
                    reliance_items.append({
                        'name': product_name,
                        'quantity': qty,
                        'unit': unit,
                        'price': price,
                    })
            
            i += 1
        
        if reliance_items:
            items.extend(reliance_items)
        
        # Pattern for items like "APPLE RD DELI PP 6", "BRT CHOCO CK 60 g", etc.
        enhanced_item_re = re.compile(
            r'([A-Z][A-Z\s\-]+?(?:\s+(?:RD|PP|CK|DELI))*)\s+(\d+(?:[\.,]\d{1,3})?)\s*([A-Z]*)\s+(\d+(?:[\.,]\d{1,2})?)\s+(\d+(?:[\.,]\d{1,2})?)\s+(\d+(?:[\.,]\d{1,2})?)',
            re.I
        )
        
        # Simple item pattern
        simple_item_re = re.compile(r'([A-Za-z][A-Za-z\s\-]+?)\s+(\d+[\./\d]*)\s*(kg|g|l|ml|pcs|pkt|unit|units)?', re.I)
        price_re = re.compile(r'(\d+[\.,]?\d*)$')
        
        for line in lines:
            # Try enhanced pattern first
            enhanced_match = enhanced_item_re.search(line)
            if enhanced_match:
                name = enhanced_match.group(1).strip()
                qty = _norm_float(enhanced_match.group(2))
                unit_text = enhanced_match.group(3).strip()
                price = _norm_float(enhanced_match.group(6))  # Total price
                
                # Map unit
                unit = unit_mapping.get(unit_text.upper(), unit_text.lower() if unit_text else '')
                
                # Clean up name
                name = re.sub(r'\s+(RD|PP|CK|DELI)\s*$', '', name, flags=re.I).strip()
                
                items.append({
                    'name': name,
                    'quantity': qty,
                    'unit': unit,
                    'price': price,
                })
                continue
            
            # Try simple pattern
            m = simple_item_re.search(line)
            if m:
                name = m.group(1).strip()
                qty_txt = m.group(2).replace('/', '.')
                try:
                    qty = float(qty_txt)
                except ValueError:
                    qty = 1.0
                unit = (m.group(3) or '').lower()
                price = None
                pm = price_re.search(line)
                if pm and pm.group(1) and pm.group(1) != qty_txt:
                    try:
                        price = float(pm.group(1).replace(',', ''))
                    except ValueError:
                        price = None
                items.append({'name': name, 'quantity': qty, 'unit': unit, 'price': price})

    return items


def extract_expiry_date_from_image(image_path: str):
    """Extract expiry date from a product photo using Vision OCR and date regex.

    Supports formats like: 2025-01-31, 31/01/2025, 31-01-25, 2025/01/31.
    Returns a date (datetime.date) or None.
    """
    text = ''
    try:
        reader = easyocr.Reader(['en'], gpu=False)
        results = reader.readtext(image_path, detail=1, paragraph=False)
        lines = [r[1] for r in results if isinstance(r, (list, tuple)) and len(r) >= 2]
        text = "\n".join([ln.strip() for ln in lines if str(ln).strip()])
    except Exception:
        text = ''

    # Try to detect keywords followed by date
    # Common tokens: EXP, EXPIRY, BEST BEFORE, USE BY
    date_patterns = [
        r'(?:exp|expiry|best before|use by)[:\s-]*([0-3]?\d[\-/][01]?\d[\-/](?:\d{2}|\d{4}))',
        r'([0-3]?\d[\-/][01]?\d[\-/](?:\d{2}|\d{4}))',
        r'((?:\d{4})[\-/](?:0?\d|1[0-2])[\-/](?:0?\d|[12]\d|3[01]))',
    ]

    for pat in date_patterns:
        m = re.search(pat, text, re.I)
        if m:
            date_str = m.group(1)
            for fmt in ('%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d', '%Y/%m/%d', '%d/%m/%y', '%d-%m-%y'):
                try:
                    return datetime.strptime(date_str, fmt).date()
                except ValueError:
                    continue
    return None
