"""
Nutrition Calculator - Calculate accurate nutrition from ingredients
"""
import json
import os
from typing import Dict, List, Any, Optional
from fuzzywuzzy import fuzz


def load_nutrition_data() -> Dict:
    """Load nutrition database from JSON file."""
    base_dir = os.path.dirname(os.path.dirname(__file__))
    nutrition_file = os.path.join(base_dir, 'nutrition_data.json')
    
    try:
        with open(nutrition_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: nutrition_data.json not found at {nutrition_file}")
        return {}


def find_nutrition_match(ingredient_name: str, nutrition_db: Dict) -> Optional[Dict]:
    """
    Find nutrition data for an ingredient using fuzzy matching.
    
    Args:
        ingredient_name: Name of the ingredient
        nutrition_db: Nutrition database dictionary
    
    Returns:
        Nutrition data dict or None if not found
    """
    ingredient_lower = ingredient_name.lower().strip()
    
    # Direct match first
    for category, items in nutrition_db.items():
        if ingredient_lower in items:
            return items[ingredient_lower]
    
    # Fuzzy match
    best_match = None
    best_score = 0
    
    for category, items in nutrition_db.items():
        for item_name, nutrition in items.items():
            score = fuzz.ratio(ingredient_lower, item_name)
            if score > best_score and score >= 70:  # 70% threshold
                best_score = score
                best_match = nutrition
    
    return best_match


def calculate_ingredient_nutrition(ingredient_name: str, quantity_grams: float, nutrition_db: Dict) -> Dict[str, float]:
    """
    Calculate nutrition for a single ingredient.
    
    Args:
        ingredient_name: Name of the ingredient
        quantity_grams: Quantity in grams
        nutrition_db: Nutrition database
    
    Returns:
        Dict with calories, protein_g, carbs_g, fat_g, fiber_g
    """
    nutrition_per_100g = find_nutrition_match(ingredient_name, nutrition_db)
    
    if not nutrition_per_100g:
        # Return zeros if not found
        return {
            'calories': 0,
            'protein_g': 0.0,
            'carbs_g': 0.0,
            'fat_g': 0.0,
            'fiber_g': 0.0
        }
    
    # Calculate based on actual quantity
    multiplier = quantity_grams / 100.0
    
    return {
        'calories': round(nutrition_per_100g['calories_per_100g'] * multiplier),
        'protein_g': round(nutrition_per_100g['protein_g'] * multiplier, 1),
        'carbs_g': round(nutrition_per_100g['carbs_g'] * multiplier, 1),
        'fat_g': round(nutrition_per_100g['fat_g'] * multiplier, 1),
        'fiber_g': round(nutrition_per_100g['fiber_g'] * multiplier, 1)
    }


def convert_to_grams(quantity: float, unit: str) -> float:
    """
    Convert quantity to grams based on unit.
    
    Args:
        quantity: Quantity value
        unit: Unit string (kg, g, l, ml, etc.)
    
    Returns:
        Quantity in grams
    """
    unit_lower = unit.lower().strip() if unit else 'g'
    
    # Weight conversions
    if unit_lower in ['kg', 'kgs', 'kilogram', 'kilograms']:
        return quantity * 1000
    elif unit_lower in ['g', 'gm', 'gms', 'gram', 'grams']:
        return quantity
    elif unit_lower in ['mg', 'milligram', 'milligrams']:
        return quantity / 1000
    
    # Volume conversions (approximate for liquids)
    elif unit_lower in ['l', 'ltr', 'litre', 'liter', 'litres', 'liters']:
        return quantity * 1000  # 1L ≈ 1kg for water-based liquids
    elif unit_lower in ['ml', 'milliliter', 'millilitre']:
        return quantity  # 1ml ≈ 1g for water-based liquids
    
    # Pieces/units (rough estimates)
    elif unit_lower in ['piece', 'pieces', 'pc', 'pcs']:
        return quantity * 100  # Assume 100g per piece
    elif unit_lower in ['cup', 'cups']:
        return quantity * 200  # 1 cup ≈ 200g
    elif unit_lower in ['tbsp', 'tablespoon', 'tablespoons']:
        return quantity * 15  # 1 tbsp ≈ 15g
    elif unit_lower in ['tsp', 'teaspoon', 'teaspoons']:
        return quantity * 5  # 1 tsp ≈ 5g
    
    # Default: assume grams
    return quantity


def calculate_recipe_nutrition(ingredients: List[Dict]) -> Dict[str, Any]:
    """
    Calculate total nutrition for a recipe from its ingredients.
    
    Args:
        ingredients: List of ingredient dicts with 'name', 'qty', 'unit'
    
    Returns:
        Dict with total nutrition and breakdown
    """
    nutrition_db = load_nutrition_data()
    
    total_nutrition = {
        'calories': 0,
        'protein_g': 0.0,
        'carbs_g': 0.0,
        'fat_g': 0.0,
        'fiber_g': 0.0
    }
    
    ingredient_breakdown = []
    
    for ing in ingredients:
        name = ing.get('name', '')
        qty = ing.get('qty', 0)
        unit = ing.get('unit', 'g')
        
        # Convert to grams
        qty_grams = convert_to_grams(qty, unit)
        
        # Calculate nutrition
        ing_nutrition = calculate_ingredient_nutrition(name, qty_grams, nutrition_db)
        
        # Add to total
        for key in total_nutrition:
            total_nutrition[key] += ing_nutrition[key]
        
        # Store breakdown
        ingredient_breakdown.append({
            'name': name,
            'quantity': f"{qty} {unit}",
            'nutrition': ing_nutrition
        })
    
    # Round totals
    total_nutrition['calories'] = round(total_nutrition['calories'])
    total_nutrition['protein_g'] = round(total_nutrition['protein_g'], 1)
    total_nutrition['carbs_g'] = round(total_nutrition['carbs_g'], 1)
    total_nutrition['fat_g'] = round(total_nutrition['fat_g'], 1)
    total_nutrition['fiber_g'] = round(total_nutrition['fiber_g'], 1)
    
    return {
        'total': total_nutrition,
        'breakdown': ingredient_breakdown
    }


def get_nutrition_insights(nutrition: Dict[str, float]) -> List[str]:
    """
    Generate simple insights from nutrition data.
    
    Args:
        nutrition: Dict with calories, protein_g, carbs_g, fat_g
    
    Returns:
        List of insight strings
    """
    insights = []
    
    calories = nutrition.get('calories', 0)
    protein = nutrition.get('protein_g', 0)
    carbs = nutrition.get('carbs_g', 0)
    fat = nutrition.get('fat_g', 0)
    
    # Calorie insights
    if calories < 300:
        insights.append("🟢 Low calorie meal - great for weight management")
    elif calories > 600:
        insights.append("🔴 High calorie meal - good for energy needs")
    else:
        insights.append("🟡 Moderate calorie meal - balanced energy")
    
    # Protein insights
    if protein >= 20:
        insights.append("💪 High protein - excellent for muscle building")
    elif protein < 10:
        insights.append("⚠️ Low protein - consider adding protein sources")
    
    # Macro balance
    total_macros = protein + carbs + fat
    if total_macros > 0:
        protein_pct = (protein * 4 / (total_macros * 4)) * 100  # 4 cal per g
        carbs_pct = (carbs * 4 / (total_macros * 4)) * 100
        fat_pct = (fat * 9 / (total_macros * 9)) * 100
        
        if carbs_pct > 60:
            insights.append("🍚 Carb-heavy meal - provides quick energy")
        elif protein_pct > 30:
            insights.append("🥩 Protein-rich meal - great for satiety")
        elif fat_pct > 40:
            insights.append("🧈 Fat-rich meal - provides sustained energy")
        else:
            insights.append("✅ Well-balanced macros")
    
    return insights


def compare_with_average(current_nutrition: Dict, historical_avg: Dict) -> List[str]:
    """
    Compare current meal nutrition with historical average.
    
    Args:
        current_nutrition: Current meal nutrition
        historical_avg: Average nutrition from past meals
    
    Returns:
        List of comparison insights
    """
    comparisons = []
    
    if not historical_avg:
        return ["📊 This is your first tracked meal!"]
    
    cal_diff = current_nutrition['calories'] - historical_avg.get('calories', 0)
    protein_diff = current_nutrition['protein_g'] - historical_avg.get('protein_g', 0)
    
    if abs(cal_diff) > 100:
        if cal_diff > 0:
            comparisons.append(f"📈 {abs(cal_diff)} more calories than your average meal")
        else:
            comparisons.append(f"📉 {abs(cal_diff)} fewer calories than your average meal")
    
    if abs(protein_diff) > 5:
        if protein_diff > 0:
            comparisons.append(f"💪 {abs(protein_diff):.1f}g more protein than usual")
        else:
            comparisons.append(f"⚠️ {abs(protein_diff):.1f}g less protein than usual")
    
    if not comparisons:
        comparisons.append("✅ Similar to your typical meal")
    
    return comparisons
