from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple, Optional
import json
import os
import re

from datetime import datetime
from utils.alias_resolver import normalize_name
from utils.expiry_utils import compute_status
from utils.item_categorizer import categorize_item


@dataclass
class PantryItem:
    id: int
    name: str
    unit: str | None
    remaining: float
    expiry: Any  # date or None


def load_recipes(base_dir: str) -> List[Dict[str, Any]]:
    path = os.path.join(base_dir, 'recipes.json')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


def _ingredient_match(pname: str, ing_name: str, subs: List[str]) -> Tuple[bool, float]:
    """Enhanced ingredient matching with confidence scoring and category awareness."""
    pn = normalize_name(pname).lower()
    ing_norm = normalize_name(ing_name).lower()
    
    # Exact match
    if ing_norm == pn:
        return True, 1.0
    
    # Substring match
    if ing_norm in pn or pn in ing_norm:
        return True, 0.8
    
    # Word overlap
    p_words = set(pn.split())
    i_words = set(ing_norm.split())
    overlap = len(p_words & i_words) / len(p_words | i_words) if p_words | i_words else 0
    if overlap > 0.5:
        return True, overlap
    
    # Category-based matching (new enhancement)
    p_category, p_conf = categorize_item(pname)
    i_category, i_conf = categorize_item(ing_name)
    
    # If both items are in the same category with high confidence
    if p_category == i_category and p_category != 'unknown' and p_conf > 0.7 and i_conf > 0.7:
        # Check for common substitutions within category
        category_substitutions = {
            'vegetables': ['onion', 'shallot', 'scallion', 'leek'],
            'dairy': ['milk', 'cream', 'yogurt', 'buttermilk'],
            'oils_fats': ['oil', 'butter', 'ghee'],
            'spices_condiments': ['salt', 'pepper', 'spice', 'seasoning'],
            'grains_cereals': ['flour', 'wheat', 'rice', 'grain']
        }
        
        if p_category in category_substitutions:
            for sub_group in category_substitutions[p_category]:
                if sub_group in pn and sub_group in ing_norm:
                    return True, 0.6
    
    # Enhanced substitution matching
    if any(sub.lower() in pn for sub in subs) and any(sub.lower() in ing_norm for sub in subs):
        return True, 0.7
    
    # Check substitutes
    for sub in subs or []:
        sub_norm = normalize_name(sub).lower()
        if sub_norm in pn or pn in sub_norm:
            return True, 0.6
    
    # Fuzzy matching
    try:
        from rapidfuzz import fuzz
        similarity = fuzz.ratio(pn, ing_norm) / 100.0
        if similarity > 0.7:
            return True, similarity
    except ImportError:
        pass
    
    return False, 0.0


def _convert_units(quantity: float, from_unit: str, to_unit: str) -> float:
    """Convert quantity from one unit to another."""
    if not from_unit or not to_unit or from_unit == to_unit:
        return quantity
    
    # Normalize units
    from_unit = from_unit.lower().strip()
    to_unit = to_unit.lower().strip()
    
    # Weight conversions
    weight_conversions = {
        ('g', 'kg'): 0.001,
        ('kg', 'g'): 1000,
        ('gm', 'kg'): 0.001,
        ('kg', 'gm'): 1000,
        ('gram', 'kg'): 0.001,
        ('kg', 'gram'): 1000,
    }
    
    # Volume conversions
    volume_conversions = {
        ('ml', 'l'): 0.001,
        ('l', 'ml'): 1000,
        ('litre', 'l'): 1.0,
        ('l', 'litre'): 1.0,
        ('liter', 'l'): 1.0,
        ('l', 'liter'): 1.0,
    }
    
    # Check weight conversions
    conversion_key = (from_unit, to_unit)
    if conversion_key in weight_conversions:
        return quantity * weight_conversions[conversion_key]
    
    # Check volume conversions
    if conversion_key in volume_conversions:
        return quantity * volume_conversions[conversion_key]
    
    # If no conversion found, return original quantity
    return quantity


def score_recipes(recipes: List[Dict[str, Any]], pantry: List[PantryItem], today, preferences: Optional[Dict] = None) -> List[Tuple[float, Dict[str, Any], Dict[str, Any]]]:
    """
    Enhanced recipe scoring with confidence, nutrition, and preference weighting.
    Returns list of (score, recipe, match_info) with detailed matching information.
    """
    scored: List[Tuple[float, Dict[str, Any], Dict[str, Any]]] = []
    preferences = preferences or {}
    
    for recipe in recipes:
        base_score = 0.0
        ingredient_matches = []
        total_ingredients = len(recipe.get('ingredients', []))
        matched_count = 0
        expiring_count = 0
        confidence_sum = 0.0
        
        for ing in recipe.get('ingredients', []):
            ing_name = ing.get('name', '')
            required_qty = float(ing.get('qty', 0))
            required_unit = ing.get('unit', '').lower()
            substitutes = ing.get('sub', [])
            
            best_match = None
            best_confidence = 0.0
            
            # Find best matching pantry item
            for pantry_item in pantry:
                is_match, confidence = _ingredient_match(pantry_item.name, ing_name, substitutes)
                if is_match and confidence > best_confidence:
                    best_confidence = confidence
                    available_qty = pantry_item.remaining or 0
                    
                    # Convert units if needed
                    converted_qty = _convert_units(available_qty, (pantry_item.unit or '').lower(), required_unit)
                    
                    # Check expiry status
                    status, days_left = compute_status(pantry_item.expiry, today)
                    is_expiring = status in ['expired', 'soon']
                    
                    best_match = {
                        'pantry_item': pantry_item,
                        'confidence': confidence,
                        'available_qty': converted_qty,
                        'required_qty': required_qty,
                        'coverage': min(1.0, converted_qty / required_qty) if required_qty > 0 else 0.0,
                        'is_expiring': is_expiring,
                        'days_left': days_left,
                        'unit_match': required_unit == (pantry_item.unit or '').lower()
                    }
            
            if best_match:
                matched_count += 1
                confidence_sum += best_confidence
                if best_match['is_expiring']:
                    expiring_count += 1
                ingredient_matches.append({
                    'ingredient': ing_name,
                    'match': best_match,
                    'status': 'matched'
                })
            else:
                ingredient_matches.append({
                    'ingredient': ing_name,
                    'match': None,
                    'status': 'missing'
                })
        
        # Calculate comprehensive score
        coverage_ratio = matched_count / total_ingredients if total_ingredients > 0 else 0
        avg_confidence = confidence_sum / matched_count if matched_count > 0 else 0
        
        # Base scoring components
        expiring_bonus = expiring_count * 3.0  # High priority for expiring items
        coverage_score = coverage_ratio * 2.0
        confidence_score = avg_confidence * 1.5
        missing_penalty = (total_ingredients - matched_count) * 0.5
        
        base_score = expiring_bonus + coverage_score + confidence_score - missing_penalty
        
        # Apply preference bonuses
        preference_bonus = 0.0
        recipe_tags = recipe.get('tags', [])
        cook_time = recipe.get('time_min', 30)
        
        # Time preference
        preferred_time = preferences.get('max_cook_time', 60)
        if cook_time <= preferred_time:
            preference_bonus += 0.5
        
        # Dietary preferences
        preferred_tags = preferences.get('preferred_tags', [])
        for tag in preferred_tags:
            if tag in recipe_tags:
                preference_bonus += 0.3
        
        # Difficulty preference (if available)
        difficulty = recipe.get('difficulty', 'medium')
        preferred_difficulty = preferences.get('difficulty', 'medium')
        if difficulty == preferred_difficulty:
            preference_bonus += 0.2
        
        final_score = base_score + preference_bonus
        
        # Compile match information
        match_info = {
            'ingredient_matches': ingredient_matches,
            'coverage_ratio': round(coverage_ratio, 2),
            'avg_confidence': round(avg_confidence, 2),
            'expiring_ingredients': expiring_count,
            'missing_ingredients': total_ingredients - matched_count,
            'estimated_portions': _estimate_portions(ingredient_matches),
            'nutrition_estimate': _estimate_nutrition(recipe, ingredient_matches)
        }
        
        scored.append((final_score, recipe, match_info))
    
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored


def plan_meals(scored: List[Tuple[float, Dict[str, Any], Dict[str, Any]]], days: int = 3, preferences: Optional[Dict] = None) -> List[Dict[str, Any]]:
    """Generate optimized meal plan considering variety, nutrition, and preferences."""
    plan: List[Dict[str, Any]] = []
    used_titles: set[str] = set()
    used_categories: List[str] = []
    preferences = preferences or {}
    
    # Track ingredient usage to avoid conflicts
    reserved_ingredients: Dict[str, float] = {}
    
    for score, recipe, match_info in scored:
        if len(plan) >= days:
            break
            
        title = recipe.get('title', '')
        if title in used_titles or score <= 0:
            continue
            
        # Check for variety (avoid same category back-to-back)
        recipe_tags = recipe.get('tags', [])
        main_category = recipe_tags[0] if recipe_tags else 'other'
        
        variety_penalty = 0
        if len(used_categories) > 0 and main_category == used_categories[-1]:
            variety_penalty = 1.0
            
        # Check ingredient conflicts
        conflict_penalty = 0
        for ing_match in match_info['ingredient_matches']:
            if ing_match['status'] == 'matched':
                ing_name = ing_match['ingredient']
                required = ing_match['match'].get('required_qty', 0)
                available = ing_match['match'].get('available_qty', 0)
                already_reserved = reserved_ingredients.get(ing_name, 0)
                
                if required > 0 and already_reserved + required > available:
                    conflict_penalty += 0.5
        
        adjusted_score = score - variety_penalty - conflict_penalty
        
        if adjusted_score > 0:
            # Reserve ingredients
            for ing_match in match_info['ingredient_matches']:
                if ing_match['status'] == 'matched':
                    ing_name = ing_match['ingredient']
                    required = ing_match['match'].get('required_qty', 0)
                    if required > 0:
                        reserved_ingredients[ing_name] = reserved_ingredients.get(ing_name, 0) + required
            
            plan.append({
                'title': title,
                'time_min': recipe.get('time_min'),
                'difficulty': recipe.get('difficulty', 'medium'),
                'tags': recipe_tags,
                'score': round(adjusted_score, 2),
                'expiring_ingredients': match_info['expiring_ingredients'],
                'coverage_ratio': match_info['coverage_ratio'],
                'estimated_portions': match_info['estimated_portions'],
                'nutrition': match_info['nutrition_estimate'],
                'ingredients': recipe.get('ingredients', [])
            })
            
            used_titles.add(title)
            used_categories.append(main_category)
    
    return plan


def _estimate_portions(ingredient_matches: List[Dict]) -> int:
    """Estimate number of portions based on ingredient availability."""
    min_portions = float('inf')
    
    for match in ingredient_matches:
        if match['status'] == 'matched' and match['match']['required_qty'] > 0:
            portions = match['match']['available_qty'] / match['match']['required_qty']
            min_portions = min(min_portions, portions)
    
    return max(1, int(min_portions)) if min_portions != float('inf') else 2


def _estimate_nutrition(recipe: Dict, ingredient_matches: List[Dict]) -> Dict[str, Any]:
    """Estimate nutritional information based on ingredients."""
    # Simple nutrition estimation based on ingredient categories
    nutrition = {
        'calories_estimate': 0,
        'protein_level': 'medium',
        'carb_level': 'medium',
        'fat_level': 'low',
        'fiber_level': 'medium',
        'healthiness_score': 0.5
    }
    
    ingredient_names = [match['ingredient'].lower() for match in ingredient_matches]
    
    # Calorie estimation
    base_calories = 200  # Base recipe calories
    for name in ingredient_names:
        if any(word in name for word in ['oil', 'ghee', 'butter']):
            base_calories += 100
        elif any(word in name for word in ['rice', 'flour', 'bread']):
            base_calories += 150
        elif any(word in name for word in ['meat', 'paneer', 'egg']):
            base_calories += 120
        elif any(word in name for word in ['vegetable', 'fruit']):
            base_calories += 30
    
    nutrition['calories_estimate'] = base_calories
    
    # Protein level
    protein_ingredients = [name for name in ingredient_names 
                         if any(word in name for word in ['paneer', 'dal', 'lentil', 'egg', 'meat', 'fish'])]
    nutrition['protein_level'] = 'high' if len(protein_ingredients) >= 2 else 'medium' if protein_ingredients else 'low'
    
    # Healthiness score
    healthy_ingredients = [name for name in ingredient_names 
                         if any(word in name for word in ['vegetable', 'fruit', 'dal', 'lentil'])]
    unhealthy_ingredients = [name for name in ingredient_names 
                           if any(word in name for word in ['oil', 'sugar', 'fried'])]
    
    health_score = (len(healthy_ingredients) * 0.2) - (len(unhealthy_ingredients) * 0.1)
    nutrition['healthiness_score'] = max(0.1, min(1.0, 0.5 + health_score))
    
    return nutrition


def generate_recipe_suggestions(pantry_items: List[PantryItem], preferences: Optional[Dict] = None) -> Dict[str, Any]:
    """Generate AI-powered recipe suggestions based on available ingredients."""
    base_dir = os.path.dirname(os.path.dirname(__file__))
    recipes = load_recipes(base_dir)
    today = datetime.now().date()
    
    if not recipes or not today:
        return {'suggestions': [], 'meta': {'error': 'No recipes or date available'}}
    
    scored_recipes = score_recipes(recipes, pantry_items, today, preferences)
    meal_plan = plan_meals(scored_recipes, preferences=preferences, days=3)
    
    # Extract top suggestions with detailed info
    suggestions = []
    for score, recipe, match_info in scored_recipes[:5]:
        if score > 0:
            suggestions.append({
                'title': recipe.get('title'),
                'score': round(score, 2),
                'time_min': recipe.get('time_min'),
                'difficulty': recipe.get('difficulty', 'medium'),
                'tags': recipe.get('tags', []),
                'coverage': match_info['coverage_ratio'],
                'expiring_ingredients': match_info['expiring_ingredients'],
                'missing_ingredients': match_info['missing_ingredients'],
                'nutrition': match_info['nutrition_estimate'],
                'estimated_portions': match_info['estimated_portions'],
                'ingredients': recipe.get('ingredients', []),  # Include full ingredient list
                'ingredient_matches': match_info['ingredient_matches']  # Include match details
            })
    
    return {
        'suggestions': suggestions,
        'meal_plan': meal_plan,
        'meta': {
            'total_recipes_evaluated': len(recipes),
            'viable_recipes': len([s for s in scored_recipes if s[0] > 0]),
            'preferences_applied': bool(preferences)
        }
    }
