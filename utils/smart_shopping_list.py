"""
Smart Shopping List Generator
Auto-generates shopping lists based on consumption patterns and low stock items.
"""

from datetime import datetime, timedelta, UTC
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from models import Item
from utils.item_categorizer import categorize_item, get_category_info
from utils.expiry_utils import predict_finish_date


@dataclass
class ShoppingItem:
    """Represents an item in the shopping list."""
    name: str
    category: str
    suggested_quantity: float
    unit: str
    priority: str  # 'urgent', 'high', 'medium', 'low'
    reason: str
    estimated_days_until_needed: int
    current_stock: float
    avg_consumption_per_day: float


class SmartShoppingListGenerator:
    """Generates intelligent shopping lists based on consumption patterns."""
    
    def __init__(self):
        self.priority_weights = {
            'urgent': 4,    # Out of stock or expires today
            'high': 3,      # Low stock, expires within 3 days
            'medium': 2,    # Will run out within a week
            'low': 1        # Will run out within 2 weeks
        }
    
    def generate_shopping_list(self, items: List[Item], days_ahead: int = 14) -> List[ShoppingItem]:
        """
        Generate a smart shopping list based on current inventory and consumption patterns.
        
        Args:
            items: List of current inventory items
            days_ahead: How many days ahead to plan for
            
        Returns:
            List of ShoppingItem objects sorted by priority
        """
        shopping_items = []
        today = datetime.now(UTC).date()
        
        # Group items by name (canonical name)
        item_groups = self._group_items_by_name(items)
        
        for canonical_name, item_list in item_groups.items():
            # Calculate total remaining quantity and average consumption
            total_remaining = sum(item.remaining_quantity or 0 for item in item_list)
            
            # Try to get consumption data from usage tracker first
            consumption_per_day = 0.0
            unit = ''
            
            # Check usage tracker for actual consumption patterns
            try:
                from utils.usage_tracker import get_usage_tracker
                # Use a more robust way to get upload folder
                import os
                upload_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
                tracker = get_usage_tracker(upload_folder)
                for item in item_list:
                    tracked_rate = tracker.get_consumption_rate(item.id)
                    if tracked_rate > 0:
                        consumption_per_day = tracked_rate
                        unit = item.unit or ''
                        break
            except Exception:
                pass
            
            # Fallback to stored consumption_per_day
            if consumption_per_day == 0:
                for item in sorted(item_list, key=lambda x: x.added_date or datetime.min, reverse=True):
                    if item.consumption_per_day and item.consumption_per_day > 0:
                        consumption_per_day = item.consumption_per_day
                        unit = item.unit or ''
                        break
            
            # Final fallback: estimate based on category
            if consumption_per_day == 0:
                category, _ = categorize_item(canonical_name)
                consumption_per_day = self._estimate_consumption_rate(category, canonical_name)
                unit = item_list[0].unit or ''
            
            # Calculate when we'll run out
            days_until_empty = float('inf')
            if consumption_per_day > 0:
                days_until_empty = total_remaining / consumption_per_day
            
            # Determine if we need to add to shopping list
            shopping_item = self._evaluate_shopping_need(
                canonical_name, total_remaining, consumption_per_day, 
                unit, days_until_empty, days_ahead, item_list
            )
            
            if shopping_item:
                shopping_items.append(shopping_item)
        
        # Add frequently bought items that are completely out of stock
        missing_items = self._identify_missing_essentials(item_groups)
        shopping_items.extend(missing_items)
        
        # Sort by priority and days until needed
        shopping_items.sort(key=lambda x: (
            -self.priority_weights[x.priority],
            x.estimated_days_until_needed
        ))
        
        return shopping_items
    
    def _group_items_by_name(self, items: List[Item]) -> Dict[str, List[Item]]:
        """Group items by canonical name."""
        groups = {}
        for item in items:
            name = (item.name or '').strip().lower()
            if name:
                if name not in groups:
                    groups[name] = []
                groups[name].append(item)
        return groups
    
    def _estimate_consumption_rate(self, category: str, item_name: str) -> float:
        """Estimate daily consumption rate per person based on realistic Indian household consumption."""
        
        item_lower = item_name.lower()
        
        # Comprehensive daily consumption rates for Indian items (per person per day)
        
        # GRAINS & CEREALS (100g-400g per day)
        grains_cereals = {
            'rice': 0.15, 'basmati rice': 0.12, 'brown rice': 0.1, 'white rice': 0.15,
            'wheat': 0.2, 'atta': 0.2, 'whole wheat flour': 0.2, 'maida': 0.05, 'refined flour': 0.05,
            'besan': 0.02, 'gram flour': 0.02, 'chickpea flour': 0.02,
            'rava': 0.03, 'sooji': 0.03, 'semolina': 0.03, 'suji': 0.03,
            'oats': 0.05, 'quinoa': 0.03, 'barley': 0.02, 'millet': 0.03,
            'ragi': 0.03, 'finger millet': 0.03, 'jowar': 0.03, 'bajra': 0.03,
            'cornflour': 0.01, 'corn starch': 0.005, 'arrowroot': 0.005,
            'bread': 0.1, 'white bread': 0.1, 'brown bread': 0.08, 'pav': 0.05, 'bun': 0.03,
            'roti': 0.15, 'chapati': 0.15, 'naan': 0.05, 'paratha': 0.08
        }
        
        # PULSES & LEGUMES (30g-80g per day)
        pulses_legumes = {
            'dal': 0.06, 'lentil': 0.06, 'lentils': 0.06,
            'toor dal': 0.05, 'arhar dal': 0.05, 'pigeon pea': 0.05,
            'moong dal': 0.04, 'mung dal': 0.04, 'green gram': 0.04,
            'urad dal': 0.03, 'black gram': 0.03, 'black lentil': 0.03,
            'masoor dal': 0.04, 'red lentil': 0.04, 'masur dal': 0.04,
            'chana dal': 0.04, 'bengal gram': 0.04, 'split chickpea': 0.04,
            'rajma': 0.08, 'kidney bean': 0.08, 'red kidney bean': 0.08,
            'kabuli chana': 0.06, 'chickpea': 0.06, 'white chickpea': 0.06,
            'black chana': 0.05, 'kala chana': 0.05, 'black chickpea': 0.05,
            'soybean': 0.03, 'soya chunks': 0.02, 'soya granules': 0.02
        }
        
        # SPICES & CONDIMENTS (1g-20g per day)
        spices_condiments = {
            'salt': 0.008, 'sugar': 0.025, 'jaggery': 0.015, 'gud': 0.015,
            'turmeric': 0.002, 'haldi': 0.002, 'turmeric powder': 0.002,
            'red chili powder': 0.003, 'lal mirch': 0.003, 'chili powder': 0.003,
            'coriander powder': 0.002, 'dhania powder': 0.002,
            'cumin powder': 0.001, 'jeera powder': 0.001,
            'garam masala': 0.001, 'curry powder': 0.002, 'chat masala': 0.0005,
            'black pepper': 0.0005, 'kali mirch': 0.0005, 'pepper': 0.0005,
            'cardamom': 0.0003, 'elaichi': 0.0003, 'green cardamom': 0.0003,
            'cinnamon': 0.0002, 'dalchini': 0.0002, 'clove': 0.0001, 'laung': 0.0001,
            'bay leaf': 0.0001, 'tej patta': 0.0001, 'star anise': 0.0001,
            'nutmeg': 0.0001, 'jaiphal': 0.0001, 'mace': 0.0001, 'javitri': 0.0001,
            'fenugreek': 0.001, 'methi': 0.001, 'mustard seeds': 0.001, 'rai': 0.001,
            'cumin seeds': 0.001, 'jeera': 0.001, 'coriander seeds': 0.001, 'dhania': 0.001,
            'fennel seeds': 0.0005, 'saunf': 0.0005, 'carom seeds': 0.0003, 'ajwain': 0.0003,
            'asafoetida': 0.0001, 'hing': 0.0001, 'dry ginger': 0.0005, 'sonth': 0.0005,
            'tamarind': 0.005, 'imli': 0.005, 'kokum': 0.002, 'amchur': 0.001,
            'vinegar': 0.005, 'soy sauce': 0.003, 'tomato sauce': 0.01, 'ketchup': 0.01,
            'pickle': 0.01, 'achar': 0.01, 'chutney': 0.015, 'jam': 0.01, 'honey': 0.005
        }
        
        # OILS & FATS (15ml-30ml per day)
        oils_fats = {
            'oil': 0.025, 'cooking oil': 0.025, 'vegetable oil': 0.025,
            'sunflower oil': 0.025, 'mustard oil': 0.02, 'sarson oil': 0.02,
            'coconut oil': 0.015, 'nariyal oil': 0.015, 'olive oil': 0.01,
            'groundnut oil': 0.025, 'peanut oil': 0.025, 'sesame oil': 0.005, 'til oil': 0.005,
            'ghee': 0.015, 'clarified butter': 0.015, 'desi ghee': 0.015,
            'butter': 0.01, 'makhan': 0.008, 'white butter': 0.005, 'margarine': 0.005, 'vanaspati': 0.01
        }
        
        # VEGETABLES (50g-300g per day)
        vegetables = {
            # Leafy greens (20g-100g per day)
            'spinach': 0.08, 'palak': 0.08, 'lettuce': 0.03, 'cabbage': 0.1, 'patta gobi': 0.1,
            'coriander': 0.01, 'dhania': 0.01, 'mint': 0.005, 'pudina': 0.005, 'fenugreek leaves': 0.05, 'methi': 0.05,
            'mustard greens': 0.06, 'sarson': 0.06, 'amaranth': 0.04, 'chaulai': 0.04,
            
            # Root vegetables (50g-200g per day)
            'potato': 0.15, 'aloo': 0.15, 'sweet potato': 0.08, 'shakarkand': 0.08,
            'onion': 0.08, 'pyaz': 0.08, 'garlic': 0.005, 'lahsun': 0.005, 'ginger': 0.003, 'adrak': 0.003,
            'carrot': 0.06, 'gajar': 0.06, 'radish': 0.04, 'mooli': 0.04, 'beetroot': 0.05, 'chukandar': 0.05,
            'turnip': 0.04, 'shalgam': 0.04, 'yam': 0.06, 'jimikand': 0.06,
            
            # Gourds & squashes (100g-200g per day)
            'bottle gourd': 0.12, 'lauki': 0.12, 'ridge gourd': 0.1, 'tori': 0.1,
            'bitter gourd': 0.08, 'karela': 0.08, 'snake gourd': 0.1, 'chichinda': 0.1,
            'pumpkin': 0.1, 'kaddu': 0.1, 'ash gourd': 0.08, 'petha': 0.08,
            
            # Other vegetables (50g-150g per day)
            'tomato': 0.1, 'tamatar': 0.1, 'cucumber': 0.06, 'kheera': 0.06,
            'eggplant': 0.1, 'brinjal': 0.1, 'baingan': 0.1, 'okra': 0.08, 'bhindi': 0.08,
            'capsicum': 0.05, 'bell pepper': 0.05, 'shimla mirch': 0.05,
            'green chili': 0.01, 'hari mirch': 0.01, 'cauliflower': 0.1, 'gobi': 0.1,
            'broccoli': 0.06, 'green beans': 0.08, 'french beans': 0.08,
            'peas': 0.06, 'matar': 0.06, 'corn': 0.05, 'makka': 0.05, 'baby corn': 0.03,
            'mushroom': 0.04, 'khumb': 0.04, 'drumstick': 0.05, 'sahjan': 0.05
        }
        
        # FRUITS (100g-300g per day)
        fruits = {
            # Citrus fruits (100g-200g per day)
            'orange': 0.15, 'santra': 0.15, 'lemon': 0.02, 'nimbu': 0.02, 'lime': 0.02,
            'sweet lime': 0.12, 'mosambi': 0.12, 'grapefruit': 0.1,
            
            # Tropical fruits (100g-250g per day)
            'mango': 0.2, 'aam': 0.2, 'banana': 0.15, 'kela': 0.15, 'papaya': 0.12, 'papita': 0.12,
            'pineapple': 0.1, 'ananas': 0.1, 'coconut': 0.05, 'nariyal': 0.05,
            'guava': 0.12, 'amrud': 0.12, 'jackfruit': 0.08, 'kathal': 0.08,
            
            # Temperate fruits (100g-200g per day)
            'apple': 0.15, 'seb': 0.15, 'pear': 0.12, 'nashpati': 0.12, 'peach': 0.1, 'aadu': 0.1,
            'plum': 0.08, 'aloo bukhara': 0.08, 'apricot': 0.06, 'khubani': 0.06,
            'cherry': 0.05, 'grapes': 0.1, 'angur': 0.1, 'pomegranate': 0.08, 'anar': 0.08,
            
            # Melons (150g-300g per day)
            'watermelon': 0.25, 'tarbuj': 0.25, 'muskmelon': 0.2, 'kharbuja': 0.2,
            'honeydew': 0.15, 'cantaloupe': 0.15,
            
            # Berries (50g-100g per day)
            'strawberry': 0.08, 'blueberry': 0.05, 'blackberry': 0.05, 'raspberry': 0.05,
            
            # Dried fruits (10g-30g per day)
            'dates': 0.02, 'khajur': 0.02, 'raisins': 0.01, 'kishmish': 0.01,
            'almonds': 0.01, 'badam': 0.01, 'cashews': 0.008, 'kaju': 0.008,
            'walnuts': 0.006, 'akhrot': 0.006, 'pistachios': 0.005, 'pista': 0.005,
            'peanuts': 0.015, 'moongfali': 0.015, 'figs': 0.008, 'anjeer': 0.008
        }
        
        # DAIRY PRODUCTS (100ml-500ml per day)
        dairy = {
            'milk': 0.25, 'doodh': 0.25, 'full cream milk': 0.2, 'toned milk': 0.3,
            'curd': 0.15, 'dahi': 0.15, 'yogurt': 0.12, 'greek yogurt': 0.08,
            'buttermilk': 0.2, 'chaas': 0.2, 'lassi': 0.15,
            'paneer': 0.05, 'cottage cheese': 0.05, 'fresh paneer': 0.05,
            'cheese': 0.02, 'processed cheese': 0.015, 'mozzarella': 0.01, 'cheddar': 0.01,
            'butter': 0.01, 'makhan': 0.008, 'cream': 0.02, 'malai': 0.015,
            'khoya': 0.01, 'mawa': 0.01, 'condensed milk': 0.005, 'evaporated milk': 0.005,
            'ice cream': 0.03, 'kulfi': 0.02
        }
        
        # MEAT, FISH & EGGS (50g-150g per day)
        meat_fish_eggs = {
            'chicken': 0.1, 'murga': 0.1, 'mutton': 0.08, 'goat meat': 0.08, 'lamb': 0.08,
            'beef': 0.08, 'pork': 0.06, 'fish': 0.1, 'machli': 0.1, 'prawns': 0.05, 'jhinga': 0.05,
            'crab': 0.03, 'eggs': 1.0, 'ande': 1.0, 'duck eggs': 0.5, 'quail eggs': 2.0,  # pieces per day
            'frozen chicken': 0.1, 'frozen fish': 0.1, 'frozen mutton': 0.08
        }
        
        # BEVERAGES (200ml-1000ml per day)
        beverages = {
            'tea': 0.01, 'chai': 0.01, 'black tea': 0.008, 'green tea': 0.005,  # dry tea leaves
            'coffee': 0.008, 'instant coffee': 0.005, 'coffee beans': 0.01,
            'juice': 0.2, 'fresh juice': 0.25, 'packaged juice': 0.15,
            'coconut water': 0.15, 'nariyal pani': 0.15, 'sugarcane juice': 0.2,
            'lassi': 0.15, 'buttermilk': 0.2, 'milk shake': 0.12,
            'soft drink': 0.1, 'soda': 0.1, 'energy drink': 0.05
        }
        
        # PACKAGED & PROCESSED FOODS (20g-100g per day)
        packaged = {
            'biscuit': 0.04, 'cookies': 0.03, 'crackers': 0.02, 'namkeen': 0.03,
            'chips': 0.02, 'popcorn': 0.015, 'cornflakes': 0.04, 'oats': 0.05,
            'pasta': 0.06, 'noodles': 0.06, 'maggi': 0.06, 'instant noodles': 0.06,
            'vermicelli': 0.04, 'sevaiyan': 0.04, 'poha': 0.05, 'murmura': 0.02,
            'papad': 0.01, 'pickle': 0.01, 'sauce': 0.01, 'ready to eat': 0.08
        }
        
        # Combine all categories
        all_consumption_rates = {**grains_cereals, **pulses_legumes, **spices_condiments, 
                               **oils_fats, **vegetables, **fruits, **dairy, 
                               **meat_fish_eggs, **beverages, **packaged}
        
        # Check for exact matches first
        if item_lower in all_consumption_rates:
            return all_consumption_rates[item_lower]
        
        # Check for partial matches
        for item_name_key, rate in all_consumption_rates.items():
            if item_name_key in item_lower or item_lower in item_name_key:
                return rate
        
        # Fallback to category-based rates
        category_fallbacks = {
            'fruits': 0.12,          # 120g per day
            'vegetables': 0.1,       # 100g per day
            'dairy': 0.2,            # 200ml per day
            'meat_fish': 0.08,       # 80g per day
            'grains_cereals': 0.15,  # 150g per day
            'legumes': 0.05,         # 50g per day
            'spices_condiments': 0.005,  # 5g per day
            'oils_fats': 0.02,       # 20ml per day
            'beverages': 0.15,       # 150ml per day
            'snacks_sweets': 0.03,   # 30g per day
        }
        
        return category_fallbacks.get(category, 0.05)  # Default 50g per day
    
    def _evaluate_shopping_need(
        self, name: str, current_stock: float, consumption_rate: float,
        unit: str, days_until_empty: float, planning_days: int, items: List[Item]
    ) -> Optional[ShoppingItem]:
        """Evaluate if an item needs to be added to shopping list."""
        
        category, _ = categorize_item(name)
        today = datetime.now(UTC).date()
        
        # Check if any items are expired or expiring soon
        urgent_expiry = False
        for item in items:
            if item.expiry_date:
                days_to_expiry = (item.expiry_date - today).days
                if days_to_expiry <= 1:
                    urgent_expiry = True
                    break
        
        # Determine priority and reason based on stock levels and consumption
        priority = 'low'
        reason = 'Regular restocking'
        
        if current_stock == 0:
            priority = 'urgent'
            reason = 'Out of stock'
        elif days_until_empty <= 1:
            priority = 'urgent'
            reason = 'Will run out today'
        elif days_until_empty <= 3:
            priority = 'high'
            reason = 'Will run out in 2-3 days'
        elif days_until_empty <= 7:
            priority = 'medium'
            reason = 'Will run out this week'
        elif days_until_empty <= planning_days:
            priority = 'low'
            reason = f'Will run out in {int(days_until_empty)} days'
        elif urgent_expiry and current_stock > 0:
            # Only mark as urgent due to expiry if we actually need to replace soon
            if days_until_empty <= planning_days + 3:  # Within planning period + small buffer
                priority = 'medium'
                reason = 'Current stock expired/expiring - replacement needed soon'
            else:
                # If we have plenty of time, don't add to shopping list yet
                return None
        else:
            # Don't add to shopping list if we have enough for planning period
            return None
        
        # Calculate suggested quantity
        suggested_quantity = self._calculate_suggested_quantity(
            consumption_rate, category, planning_days
        )
        
        return ShoppingItem(
            name=name.title(),
            category=category,
            suggested_quantity=suggested_quantity,
            unit=unit,
            priority=priority,
            reason=reason,
            estimated_days_until_needed=max(0, int(days_until_empty)),
            current_stock=current_stock,
            avg_consumption_per_day=consumption_rate
        )
    
    def _calculate_suggested_quantity(
        self, consumption_rate: float, category: str, planning_days: int
    ) -> float:
        """Calculate suggested purchase quantity."""
        
        # Base quantity for planning period
        base_quantity = consumption_rate * planning_days
        
        # Add buffer based on category
        buffer_multipliers = {
            'fruits': 1.2,          # 20% buffer for spoilage
            'vegetables': 1.3,      # 30% buffer for spoilage
            'dairy': 1.1,           # 10% buffer
            'meat_fish': 1.1,       # 10% buffer
            'grains_cereals': 2.0,  # Buy in bulk
            'legumes': 2.0,         # Buy in bulk
            'spices_condiments': 3.0,  # Buy larger quantities
            'oils_fats': 2.0,       # Buy in bulk
            'beverages': 1.5,       # 50% buffer
            'snacks_sweets': 1.0,   # No buffer needed
        }
        
        multiplier = buffer_multipliers.get(category, 1.2)
        suggested = base_quantity * multiplier
        
        # Round to reasonable quantities
        if suggested < 0.1:
            return 0.1
        elif suggested < 1:
            return round(suggested, 1)
        else:
            return round(suggested)
    
    def _identify_missing_essentials(self, current_groups: Dict[str, List[Item]]) -> List[ShoppingItem]:
        """Identify essential items that are completely missing from inventory."""
        
        essentials = [
            ('milk', 'dairy', 1.0, 'l'),
            ('bread', 'grains_cereals', 1.0, 'pcs'),
            ('rice', 'grains_cereals', 2.0, 'kg'),
            ('oil', 'oils_fats', 1.0, 'l'),
            ('salt', 'spices_condiments', 1.0, 'kg'),
            ('onion', 'vegetables', 1.0, 'kg'),
            ('potato', 'vegetables', 2.0, 'kg'),
            ('tomato', 'vegetables', 1.0, 'kg'),
        ]
        
        missing_items = []
        
        for name, category, default_qty, unit in essentials:
            # Check if we have any variant of this essential item
            found = False
            for existing_name in current_groups.keys():
                if name in existing_name or existing_name in name:
                    found = True
                    break
            
            if not found:
                missing_items.append(ShoppingItem(
                    name=name.title(),
                    category=category,
                    suggested_quantity=default_qty,
                    unit=unit,
                    priority='medium',
                    reason='Essential item missing from inventory',
                    estimated_days_until_needed=0,
                    current_stock=0.0,
                    avg_consumption_per_day=self._estimate_consumption_rate(category, name)
                ))
        
        return missing_items
    
    def categorize_shopping_list(self, shopping_items: List[ShoppingItem]) -> Dict[str, List[ShoppingItem]]:
        """Group shopping items by category for better organization."""
        categorized = {}
        
        for item in shopping_items:
            if item.category not in categorized:
                categorized[item.category] = []
            categorized[item.category].append(item)
        
        # Sort categories by priority (most urgent items first)
        for category_items in categorized.values():
            category_items.sort(key=lambda x: -self.priority_weights[x.priority])
        
        return categorized
    
    def get_shopping_summary(self, shopping_items: List[ShoppingItem]) -> Dict:
        """Get summary statistics for the shopping list."""
        if not shopping_items:
            return {
                'total_items': 0,
                'urgent_items': 0,
                'categories': 0,
                'estimated_cost': 0.0
            }
        
        urgent_count = sum(1 for item in shopping_items if item.priority == 'urgent')
        categories = len(set(item.category for item in shopping_items))
        
        return {
            'total_items': len(shopping_items),
            'urgent_items': urgent_count,
            'high_priority_items': sum(1 for item in shopping_items if item.priority == 'high'),
            'categories': categories,
            'most_urgent_category': max(
                set(item.category for item in shopping_items if item.priority == 'urgent'),
                key=lambda cat: sum(1 for item in shopping_items if item.category == cat and item.priority == 'urgent'),
                default='none'
            ) if urgent_count > 0 else 'none'
        }


# Global instance
shopping_list_generator = SmartShoppingListGenerator()


def generate_smart_shopping_list(items: List[Item], days_ahead: int = 14) -> List[ShoppingItem]:
    """Convenience function to generate shopping list."""
    return shopping_list_generator.generate_shopping_list(items, days_ahead)
