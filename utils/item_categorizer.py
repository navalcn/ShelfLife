"""
Smart Item Categorization System
Auto-categorizes grocery items into categories like fruits, vegetables, dairy, etc.
"""

import re
from typing import Dict, List, Tuple, Optional


class ItemCategorizer:
    """Categorizes grocery items based on name patterns and keywords."""
    
    def __init__(self):
        self.categories = {
            'fruits': {
                'keywords': [
                    'apple', 'banana', 'orange', 'mango', 'grape', 'strawberry', 'blueberry',
                    'pineapple', 'watermelon', 'melon', 'papaya', 'guava', 'pomegranate',
                    'kiwi', 'peach', 'pear', 'plum', 'cherry', 'apricot', 'lemon', 'lime',
                    'coconut', 'avocado', 'fig', 'date', 'raisin', 'cranberry'
                ],
                'patterns': [
                    r'\b(fruit|fruits)\b',
                    r'\b\w+berry\b',  # strawberry, blueberry, etc.
                ],
                'icon': 'apple',
                'color': 'red'
            },
            'vegetables': {
                'keywords': [
                    'tomato', 'onion', 'potato', 'carrot', 'cabbage', 'spinach', 'lettuce',
                    'broccoli', 'cauliflower', 'cucumber', 'bell pepper', 'capsicum',
                    'eggplant', 'brinjal', 'okra', 'peas', 'beans', 'corn', 'beetroot',
                    'radish', 'turnip', 'ginger', 'garlic', 'chilli', 'chili', 'green chilli',
                    'red chilli', 'pepper', 'mushroom', 'celery', 'asparagus', 'zucchini',
                    'squash', 'pumpkin', 'sweet potato', 'drumstick'
                ],
                'patterns': [
                    r'\b(vegetable|vegetables|veggie|veggies)\b',
                    r'\b\w+root\b',  # beetroot, etc.
                    r'\bchil+i\b',  # chilli, chili variations
                ],
                'icon': 'carrot',
                'color': 'green'
            },
            'dairy': {
                'keywords': [
                    'milk', 'cheese', 'butter', 'yogurt', 'yoghurt', 'curd', 'cream',
                    'paneer', 'ghee', 'lassi', 'buttermilk', 'ice cream', 'cottage cheese',
                    'mozzarella', 'cheddar', 'parmesan', 'feta'
                ],
                'patterns': [
                    r'\b(dairy|milk)\b',
                    r'\bcheese\b',
                ],
                'icon': 'milk',
                'color': 'blue'
            },
            'meat_fish': {
                'keywords': [
                    'chicken', 'mutton', 'beef', 'pork', 'lamb', 'fish', 'salmon', 'tuna',
                    'prawns', 'shrimp', 'crab', 'lobster', 'eggs', 'egg', 'bacon', 'ham',
                    'sausage', 'meat', 'turkey', 'duck'
                ],
                'patterns': [
                    r'\b(meat|fish|seafood|poultry)\b',
                    r'\begg[s]?\b',
                ],
                'icon': 'fish',
                'color': 'pink'
            },
            'bakery': {
                'keywords': [
                    'bread', 'bun', 'pav', 'baguette', 'croissant', 'bagel', 'roll',
                    'toast', 'loaf', 'sandwich bread', 'white bread', 'brown bread',
                    'whole wheat bread', 'multigrain bread', 'roti', 'chapati', 'naan',
                    'paratha', 'kulcha', 'bhatura'
                ],
                'patterns': [
                    r'\b(bread|bun|pav|roti|chapati)\b',
                ],
                'icon': 'bread',
                'color': 'amber'
            },
            'grains_cereals': {
                'keywords': [
                    'rice', 'wheat', 'flour', 'atta', 'maida', 'pasta', 'noodles',
                    'oats', 'quinoa', 'barley', 'millet', 'ragi', 'jowar', 'bajra',
                    'cereal', 'cornflakes', 'muesli', 'granola', 'biscuit', 'cookie',
                    'cracker', 'rusk'
                ],
                'patterns': [
                    r'\b(grain|grains|cereal|flour)\b',
                    r'\b\w*atta\b',  # wheat atta, etc.
                ],
                'icon': 'wheat',
                'color': 'yellow'
            },
            'legumes': {
                'keywords': [
                    'dal', 'lentil', 'chickpea', 'chana', 'rajma', 'kidney bean',
                    'black bean', 'pinto bean', 'navy bean', 'lima bean', 'soybean',
                    'tofu', 'tempeh', 'hummus', 'moong', 'toor', 'urad', 'masoor'
                ],
                'patterns': [
                    r'\b(dal|lentil|bean|legume)\b',
                    r'\b\w+dal\b',  # moong dal, etc.
                ],
                'icon': 'bean',
                'color': 'brown'
            },
            'spices_condiments': {
                'keywords': [
                    'salt', 'sugar', 'pepper', 'turmeric', 'cumin', 'coriander', 'cardamom',
                    'cinnamon', 'clove', 'nutmeg', 'bay leaf', 'oregano', 'basil', 'thyme',
                    'rosemary', 'paprika', 'chili powder', 'garam masala', 'curry powder',
                    'vinegar', 'soy sauce', 'ketchup', 'mustard', 'mayonnaise', 'pickle',
                    'jam', 'jelly', 'honey', 'syrup', 'sauce'
                ],
                'patterns': [
                    r'\b(spice|spices|masala|powder|sauce)\b',
                    r'\b\w+masala\b',  # garam masala, etc.
                ],
                'icon': 'pepper',
                'color': 'orange'
            },
            'oils_fats': {
                'keywords': [
                    'oil', 'olive oil', 'coconut oil', 'sunflower oil', 'mustard oil',
                    'sesame oil', 'groundnut oil', 'ghee', 'butter', 'margarine',
                    'cooking oil', 'vegetable oil'
                ],
                'patterns': [
                    r'\b(oil|ghee|fat)\b',
                    r'\b\w+oil\b',  # coconut oil, etc.
                ],
                'icon': 'droplet',
                'color': 'amber'
            },
            'beverages': {
                'keywords': [
                    'water', 'juice', 'tea', 'coffee', 'soda', 'cola', 'beer', 'wine',
                    'whiskey', 'rum', 'vodka', 'energy drink', 'sports drink',
                    'coconut water', 'lemonade', 'smoothie', 'shake', 'lassi'
                ],
                'patterns': [
                    r'\b(drink|beverage|juice|tea|coffee)\b',
                    r'\b\w+juice\b',  # orange juice, etc.
                ],
                'icon': 'coffee',
                'color': 'cyan'
            },
            'snacks_sweets': {
                'keywords': [
                    'chips', 'crackers', 'nuts', 'almonds', 'cashews', 'peanuts', 'walnuts',
                    'chocolate', 'candy', 'sweet', 'mithai', 'laddu', 'barfi', 'halwa',
                    'cake', 'pastry', 'donut', 'muffin', 'cookies', 'biscuits'
                ],
                'patterns': [
                    r'\b(snack|sweet|chocolate|candy|nuts)\b',
                    r'\b\w+nuts?\b',  # peanuts, etc.
                ],
                'icon': 'cookie',
                'color': 'purple'
            },
            'frozen': {
                'keywords': [
                    'frozen', 'ice cream', 'frozen vegetables', 'frozen fruits',
                    'frozen meat', 'frozen fish', 'popsicle', 'ice'
                ],
                'patterns': [
                    r'\b(frozen|ice)\b',
                ],
                'icon': 'snowflake',
                'color': 'blue'
            },
            'household': {
                'keywords': [
                    'detergent', 'soap', 'shampoo', 'toothpaste', 'tissue', 'toilet paper',
                    'cleaning', 'disinfectant', 'bleach', 'fabric softener'
                ],
                'patterns': [
                    r'\b(cleaning|soap|detergent)\b',
                ],
                'icon': 'home',
                'color': 'gray'
            }
        }
        
        # Default expiry predictions by category (in days)
        self.default_expiry_days = {
            'fruits': 7,
            'vegetables': 5,
            'dairy': 7,
            'meat_fish': 3,
            'bakery': 4,
            'grains_cereals': 365,
            'legumes': 730,
            'spices_condiments': 730,
            'oils_fats': 365,
            'beverages': 30,
            'snacks_sweets': 180,
            'frozen': 90,
            'household': 365
        }
    
    def categorize_item(self, item_name: str) -> Tuple[str, float]:
        """
        Categorize an item and return category with confidence score.
        
        Args:
            item_name: Name of the item to categorize
            
        Returns:
            Tuple of (category_name, confidence_score)
        """
        if not item_name:
            return 'unknown', 0.0
        
        item_name_lower = item_name.lower().strip()
        best_category = 'unknown'
        best_score = 0.0
        
        for category, data in self.categories.items():
            score = 0.0
            matched_count = 0
            
            # Check exact keyword matches
            for keyword in data['keywords']:
                if keyword in item_name_lower:
                    matched_count += 1
                    # Exact word match gets higher score
                    if re.search(r'\b' + re.escape(keyword) + r'\b', item_name_lower):
                        score += 1.0
                    else:
                        score += 0.5
            
            # Check pattern matches
            for pattern in data.get('patterns', []):
                if re.search(pattern, item_name_lower, re.IGNORECASE):
                    matched_count += 1
                    score += 0.8
            
            # Normalize score based on matches found (not total criteria)
            if matched_count > 0:
                score = score / matched_count
            
            if score > best_score:
                best_score = score
                best_category = category
        
        return best_category, min(best_score, 1.0)
    
    def get_category_info(self, category: str) -> Dict:
        """Get display information for a category."""
        if category in self.categories:
            return {
                'name': category.replace('_', ' ').title(),
                'icon': self.categories[category]['icon'],
                'color': self.categories[category]['color']
            }
        return {
            'name': 'Unknown',
            'icon': 'help-circle',
            'color': 'gray'
        }
    
    def predict_expiry_days(self, category: str, item_name: str = '') -> Optional[int]:
        """Predict expiry days based on category and item name."""
        if category in self.default_expiry_days:
            base_days = self.default_expiry_days[category]
            
            # Adjust based on specific item characteristics
            item_lower = item_name.lower()
            
            # Canned/packaged items last longer
            if any(word in item_lower for word in ['canned', 'packaged', 'dried', 'powder']):
                return base_days * 2
            
            # Fresh items expire sooner
            if any(word in item_lower for word in ['fresh', 'organic', 'ripe']):
                return max(1, base_days // 2)
            
            return base_days
        
        return None
    
    def get_all_categories(self) -> List[Dict]:
        """Get all available categories with their info."""
        return [
            {
                'key': category,
                'name': category.replace('_', ' ').title(),
                'icon': data['icon'],
                'color': data['color'],
                'count': len(data['keywords'])
            }
            for category, data in self.categories.items()
        ]


# Global instance
item_categorizer = ItemCategorizer()


def categorize_item(item_name: str) -> Tuple[str, float]:
    """Convenience function to categorize an item."""
    return item_categorizer.categorize_item(item_name)


def get_category_info(category: str) -> Dict:
    """Convenience function to get category info."""
    return item_categorizer.get_category_info(category)


def predict_expiry_days(category: str, item_name: str = '') -> Optional[int]:
    """Convenience function to predict expiry days."""
    return item_categorizer.predict_expiry_days(category, item_name)
