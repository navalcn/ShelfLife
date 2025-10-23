from __future__ import annotations
import json
import os
from datetime import datetime, date, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

UTC = timezone.utc

@dataclass
class UsageEntry:
    """Represents a single usage entry for an item."""
    item_id: int
    item_name: str
    quantity_used: float
    unit: str
    timestamp: datetime
    usage_type: str  # 'cooking', 'direct', 'auto_detected', 'meal_logging'
    meal_context: Optional[str] = None  # breakfast, lunch, dinner, snack
    recipe_name: Optional[str] = None

class UsageTracker:
    """Comprehensive usage tracking system for daily consumption patterns."""
    
    def __init__(self, upload_folder: str):
        self.upload_folder = upload_folder
        self.usage_log_path = os.path.join(upload_folder, 'daily_usage.json')
        self.consumption_patterns_path = os.path.join(upload_folder, 'consumption_patterns.json')
        os.makedirs(upload_folder, exist_ok=True)
    
    def log_usage(self, item_id: int, item_name: str, quantity_used: float, 
                  unit: str, usage_type: str = 'direct', 
                  meal_context: Optional[str] = None, 
                  recipe_name: Optional[str] = None) -> None:
        """Log usage of an item."""
        try:
            usage_entry = UsageEntry(
                item_id=item_id,
                item_name=item_name,
                quantity_used=quantity_used,
                unit=unit,
                timestamp=datetime.now(UTC),
                usage_type=usage_type,
                meal_context=meal_context,
                recipe_name=recipe_name
            )
            
            # Load existing usage log
            usage_log = self._load_usage_log()
            
            # Add new entry
            usage_log.append({
                'item_id': usage_entry.item_id,
                'item_name': usage_entry.item_name,
                'quantity_used': usage_entry.quantity_used,
                'unit': usage_entry.unit,
                'timestamp': usage_entry.timestamp.isoformat(),
                'usage_type': usage_entry.usage_type,
                'meal_context': usage_entry.meal_context,
                'recipe_name': usage_entry.recipe_name
            })
            
            # Keep only last 90 days of data
            cutoff_date = datetime.now(UTC) - timedelta(days=90)
            usage_log = [entry for entry in usage_log 
                        if datetime.fromisoformat(entry['timestamp']) > cutoff_date]
            
            # Save updated log
            with open(self.usage_log_path, 'w', encoding='utf-8') as f:
                json.dump(usage_log, f, ensure_ascii=False, indent=2)
            
            # Update consumption patterns
            self._update_consumption_patterns()
            
        except Exception:
            # Best-effort logging; ignore failures
            pass
    
    def _load_usage_log(self) -> List[Dict[str, Any]]:
        """Load the usage log from file."""
        if not os.path.exists(self.usage_log_path):
            return []
        
        try:
            with open(self.usage_log_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    
    def _update_consumption_patterns(self) -> None:
        """Analyze usage log and update consumption patterns."""
        usage_log = self._load_usage_log()
        
        # Group usage by item and calculate daily averages
        item_patterns = {}
        
        for entry in usage_log:
            try:
                item_id = entry['item_id']
                quantity = entry['quantity_used']
                timestamp = datetime.fromisoformat(entry['timestamp'])
                
                if item_id not in item_patterns:
                    item_patterns[item_id] = {
                        'item_name': entry['item_name'],
                        'unit': entry['unit'],
                        'daily_usage': {},
                        'weekly_pattern': {},
                        'meal_distribution': {},
                        'total_usage': 0,
                        'usage_days': set()
                    }
                
                # Track daily usage
                date_key = timestamp.date().isoformat()
                if date_key not in item_patterns[item_id]['daily_usage']:
                    item_patterns[item_id]['daily_usage'][date_key] = 0
                item_patterns[item_id]['daily_usage'][date_key] += quantity
                
                # Track weekly patterns (day of week)
                day_of_week = timestamp.strftime('%A')
                if day_of_week not in item_patterns[item_id]['weekly_pattern']:
                    item_patterns[item_id]['weekly_pattern'][day_of_week] = 0
                item_patterns[item_id]['weekly_pattern'][day_of_week] += quantity
                
                # Track meal distribution
                meal_context = entry.get('meal_context', 'unknown')
                if meal_context not in item_patterns[item_id]['meal_distribution']:
                    item_patterns[item_id]['meal_distribution'][meal_context] = 0
                item_patterns[item_id]['meal_distribution'][meal_context] += quantity
                
                # Update totals
                item_patterns[item_id]['total_usage'] += quantity
                item_patterns[item_id]['usage_days'].add(date_key)
                
            except Exception:
                continue
        
        # Calculate averages and save patterns
        for item_id, pattern in item_patterns.items():
            usage_days = len(pattern['usage_days'])
            if usage_days > 0:
                pattern['avg_daily_consumption'] = pattern['total_usage'] / usage_days
                pattern['usage_frequency'] = usage_days / 30  # Usage frequency per month
            else:
                pattern['avg_daily_consumption'] = 0
                pattern['usage_frequency'] = 0
            
            # Convert set to list for JSON serialization
            pattern['usage_days'] = list(pattern['usage_days'])
        
        # Save consumption patterns
        try:
            with open(self.consumption_patterns_path, 'w', encoding='utf-8') as f:
                json.dump(item_patterns, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    
    def get_consumption_rate(self, item_id: int, days: int = 30) -> float:
        """Get the calculated consumption rate for an item based on usage history."""
        try:
            with open(self.consumption_patterns_path, 'r', encoding='utf-8') as f:
                patterns = json.load(f)
            
            item_pattern = patterns.get(str(item_id))
            if item_pattern:
                return item_pattern.get('avg_daily_consumption', 0)
            
        except Exception:
            pass
        
        return 0
    
    def get_usage_insights(self, item_id: int) -> Dict[str, Any]:
        """Get detailed usage insights for an item."""
        try:
            with open(self.consumption_patterns_path, 'r', encoding='utf-8') as f:
                patterns = json.load(f)
            
            item_pattern = patterns.get(str(item_id), {})
            
            return {
                'avg_daily_consumption': item_pattern.get('avg_daily_consumption', 0),
                'usage_frequency': item_pattern.get('usage_frequency', 0),
                'weekly_pattern': item_pattern.get('weekly_pattern', {}),
                'meal_distribution': item_pattern.get('meal_distribution', {}),
                'total_usage_30_days': item_pattern.get('total_usage', 0),
                'active_usage_days': len(item_pattern.get('usage_days', []))
            }
            
        except Exception:
            return {}
    
    def predict_next_usage(self, item_id: int) -> Optional[date]:
        """Predict when an item will likely be used next based on patterns."""
        insights = self.get_usage_insights(item_id)
        
        if insights.get('usage_frequency', 0) == 0:
            return None
        
        # Simple prediction: if used every N days on average
        avg_days_between_usage = 30 / max(insights['usage_frequency'], 0.1)
        
        # Get last usage date
        usage_log = self._load_usage_log()
        last_usage = None
        
        for entry in reversed(usage_log):
            if entry['item_id'] == item_id:
                last_usage = datetime.fromisoformat(entry['timestamp']).date()
                break
        
        if last_usage:
            next_usage = last_usage + timedelta(days=int(avg_days_between_usage))
            return next_usage
        
        return None
    
    def get_daily_usage_summary(self, target_date: Optional[date] = None) -> Dict[str, Any]:
        """Get summary of usage for a specific date."""
        if target_date is None:
            target_date = date.today()
        
        usage_log = self._load_usage_log()
        daily_summary = {
            'date': target_date.isoformat(),
            'total_items_used': 0,
            'items_by_meal': {'breakfast': [], 'lunch': [], 'dinner': [], 'snack': [], 'unknown': []},
            'items_by_type': {},
            'total_usage_events': 0
        }
        
        target_date_str = target_date.isoformat()
        
        for entry in usage_log:
            try:
                entry_date = datetime.fromisoformat(entry['timestamp']).date().isoformat()
                if entry_date == target_date_str:
                    daily_summary['total_usage_events'] += 1
                    
                    meal_context = entry.get('meal_context', 'unknown')
                    daily_summary['items_by_meal'][meal_context].append({
                        'item_name': entry['item_name'],
                        'quantity_used': entry['quantity_used'],
                        'unit': entry['unit'],
                        'usage_type': entry['usage_type']
                    })
                    
                    usage_type = entry['usage_type']
                    if usage_type not in daily_summary['items_by_type']:
                        daily_summary['items_by_type'][usage_type] = 0
                    daily_summary['items_by_type'][usage_type] += 1
                    
            except Exception:
                continue
        
        # Count unique items used
        used_items = set()
        for meal_items in daily_summary['items_by_meal'].values():
            for item in meal_items:
                used_items.add(item['item_name'])
        
        daily_summary['total_items_used'] = len(used_items)
        
        return daily_summary
    
    def suggest_items_to_log(self) -> List[Dict[str, Any]]:
        """Suggest items that user might have used today based on patterns."""
        today = date.today()
        day_of_week = today.strftime('%A')
        
        try:
            with open(self.consumption_patterns_path, 'r', encoding='utf-8') as f:
                patterns = json.load(f)
        except Exception:
            return []
        
        suggestions = []
        
        for item_id, pattern in patterns.items():
            # Check if item is typically used on this day of week
            weekly_usage = pattern.get('weekly_pattern', {}).get(day_of_week, 0)
            avg_daily = pattern.get('avg_daily_consumption', 0)
            
            if weekly_usage > 0 and avg_daily > 0:
                # Check if already logged today
                today_summary = self.get_daily_usage_summary(today)
                already_logged = any(
                    item['item_name'].lower() == pattern['item_name'].lower()
                    for meal_items in today_summary['items_by_meal'].values()
                    for item in meal_items
                )
                
                if not already_logged:
                    suggestions.append({
                        'item_id': int(item_id),
                        'item_name': pattern['item_name'],
                        'suggested_quantity': avg_daily,
                        'unit': pattern['unit'],
                        'confidence': min(weekly_usage / 7, 1.0),  # Normalize confidence
                        'typical_meals': [meal for meal, qty in pattern.get('meal_distribution', {}).items() if qty > 0]
                    })
        
        # Sort by confidence
        suggestions.sort(key=lambda x: x['confidence'], reverse=True)
        return suggestions[:10]  # Return top 10 suggestions

# Global instance
usage_tracker = None

def get_usage_tracker(upload_folder: str) -> UsageTracker:
    """Get or create the global usage tracker instance."""
    global usage_tracker
    if usage_tracker is None:
        usage_tracker = UsageTracker(upload_folder)
    return usage_tracker
