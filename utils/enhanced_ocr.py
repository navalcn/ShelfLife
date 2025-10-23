from __future__ import annotations
import os
import json
from typing import List, Dict, Any, Tuple
from utils.ai_receipt import parse_receipt_with_donut, DonutUnavailable
import easyocr

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


class EnhancedOCRPipeline:
    """Multi-model OCR pipeline with ensemble scoring and confidence metrics."""
    
    def __init__(self):
        self.models = []
        self.confidence_threshold = 0.7
        
    def extract_with_ensemble(self, image_path: str) -> Dict[str, Any]:
        """Extract items using multiple OCR models and ensemble the results."""
        results = {
            'items': [],
            'confidence': 0.0,
            'models_used': [],
            'raw_outputs': {},
            'meta': {
                'engine': 'enhanced_ensemble',
                'error': None,
                'primary_model': None
            }
        }
        
        # Try Donut first (highest accuracy for receipts)
        donut_items = []
        try:
            donut_result = parse_receipt_with_donut(image_path)
            donut_items = donut_result.get('items', [])
            if donut_items:
                results['models_used'].append('donut')
                results['raw_outputs']['donut'] = donut_result.get('raw', '')
                results['meta']['primary_model'] = 'donut'
                results['confidence'] = 0.9  # High confidence for Donut
        except (DonutUnavailable, Exception) as e:
            results['meta']['error'] = f"donut: {str(e)}"
            
        # Try EasyOCR as fallback/ensemble
        easyocr_items = []
        try:
            use_gpu = TORCH_AVAILABLE and torch.cuda.is_available()
            reader = easyocr.Reader(['en'], gpu=use_gpu)
            ocr_results = reader.readtext(image_path, detail=1, paragraph=False)
            text_lines = [r[1] for r in ocr_results if len(r) >= 2]
            easyocr_items = self._parse_text_to_items('\n'.join(text_lines))
            
            if easyocr_items:
                results['models_used'].append('easyocr')
                results['raw_outputs']['easyocr'] = '\n'.join(text_lines)
                if not results['meta']['primary_model']:
                    results['meta']['primary_model'] = 'easyocr'
                    results['confidence'] = 0.6
                    
        except Exception as e:
            error_msg = results['meta']['error'] or ''
            results['meta']['error'] = f"{error_msg}; easyocr: {str(e)}"
            
        # Ensemble logic: prefer Donut, fallback to EasyOCR, merge if both available
        if donut_items and easyocr_items:
            # Both models succeeded - use Donut as primary, validate with EasyOCR
            results['items'] = self._merge_results(donut_items, easyocr_items)
            results['confidence'] = 0.95
        elif donut_items:
            results['items'] = donut_items
        elif easyocr_items:
            results['items'] = easyocr_items
        else:
            results['confidence'] = 0.0
            
        return results
        
    def _parse_text_to_items(self, text: str) -> List[Dict[str, Any]]:
        """Parse raw OCR text into structured items."""
        import re
        
        lines = [ln.strip() for ln in text.split('\n') if ln.strip()]
        items = []
        
        # Enhanced patterns for better extraction
        name_pattern = re.compile(r'^[A-Za-z][A-Za-z\s\-/&\.]+?(?:\s+(?:KG|EA|PKT|PACK|PCS|G|ML|L|DOZEN))?$', re.I)
        price_pattern = re.compile(r'(\d+(?:[\.,]\d{1,2})?)\s+(\d+(?:[\.,]\d{1,3})?)\s+(\d+(?:[\.,]\d{1,2})?)')
        
        pending_name = None
        pending_unit = None
        
        for line in lines:
            # Skip HSN codes and other numeric-only lines
            if re.match(r'^[0-9]{6,}$', line):
                continue
                
            # Try to match product name
            if name_pattern.match(line):
                pending_name = line
                # Extract unit from name if present
                unit_match = re.search(r'\b(KG|EA|PKT|PACK|PCS|G|ML|L|DOZEN)\b', line, re.I)
                pending_unit = unit_match.group(1).lower() if unit_match else None
                continue
                
            # Try to match price/quantity line
            price_match = price_pattern.search(line)
            if price_match and pending_name:
                try:
                    unit_price = float(price_match.group(1).replace(',', '.'))
                    quantity = float(price_match.group(2).replace(',', '.'))
                    total_price = float(price_match.group(3).replace(',', '.'))
                    
                    items.append({
                        'name': pending_name,
                        'quantity': quantity,
                        'unit': pending_unit or self._infer_unit(pending_name),
                        'price': total_price,
                        'unit_price': unit_price
                    })
                    
                except ValueError:
                    # If parsing fails, add with default quantity
                    items.append({
                        'name': pending_name,
                        'quantity': 1.0,
                        'unit': pending_unit or self._infer_unit(pending_name),
                        'price': None
                    })
                    
                pending_name = None
                pending_unit = None
                
        return items
        
    def _merge_results(self, primary_items: List[Dict], secondary_items: List[Dict]) -> List[Dict]:
        """Merge results from multiple OCR models with confidence weighting."""
        # Use primary items as base, validate quantities/prices with secondary
        merged = []
        
        for item in primary_items:
            # Look for similar item in secondary results
            best_match = None
            best_similarity = 0.0
            
            for sec_item in secondary_items:
                similarity = self._calculate_similarity(item['name'], sec_item['name'])
                if similarity > best_similarity and similarity > 0.6:
                    best_similarity = similarity
                    best_match = sec_item
                    
            if best_match:
                # Merge with validation
                merged_item = item.copy()
                # Use average quantity if both models detected it
                if 'quantity' in best_match and best_match['quantity']:
                    avg_qty = (item.get('quantity', 1) + best_match['quantity']) / 2
                    merged_item['quantity'] = round(avg_qty, 2)
                merged.append(merged_item)
            else:
                merged.append(item)
                
        return merged
        
    def _calculate_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two product names."""
        try:
            from rapidfuzz import fuzz
            return fuzz.ratio(name1.lower(), name2.lower()) / 100.0
        except ImportError:
            # Fallback to simple similarity
            name1_words = set(name1.lower().split())
            name2_words = set(name2.lower().split())
            intersection = name1_words & name2_words
            union = name1_words | name2_words
            return len(intersection) / len(union) if union else 0.0
            
    def _infer_unit(self, name: str) -> str:
        """Infer unit from product name."""
        name_lower = name.lower()
        
        # Liquid items
        if any(word in name_lower for word in ['milk', 'oil', 'juice', 'water', 'curd', 'yogurt']):
            return 'l'
        
        # Countable items
        if any(word in name_lower for word in ['egg', 'bread', 'biscuit', 'packet']):
            return 'pcs'
            
        # Default to weight
        return 'kg'


# Global instance
enhanced_ocr = EnhancedOCRPipeline()
