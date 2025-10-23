from __future__ import annotations
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Tuple
from collections import defaultdict

from utils.expiry_utils import compute_status

UTC = timezone.utc


class WasteAnalytics:
    """Analytics engine for waste tracking, savings calculations, and insights."""
    
    def __init__(self, upload_folder: str):
        self.upload_folder = upload_folder
        self.analytics_path = os.path.join(upload_folder, 'analytics.json')
        
    def compute_analytics(self, items: List[Any]) -> Dict[str, Any]:
        """Compute comprehensive analytics from current items and historical data."""
        today = datetime.now(UTC).date()
        
        # Load historical data
        historical = self._load_historical_data()
        
        # Current inventory analysis
        inventory_stats = self._analyze_current_inventory(items, today)
        
        # Waste trends
        waste_trends = self._analyze_waste_trends(historical, days=30)
        
        # Consumption patterns
        consumption_patterns = self._analyze_consumption_patterns(items)
        
        # Predictions
        predictions = self._generate_predictions(items, historical, today)
        
        analytics = {
            'generated_at': today.isoformat(),
            'inventory': inventory_stats,
            'waste_trends': waste_trends,
            'consumption': consumption_patterns,
            'predictions': predictions,
            'insights': self._generate_insights(inventory_stats, waste_trends)
        }
        
        # Save analytics
        self._save_analytics(analytics)
        
        return analytics
        
    def _analyze_current_inventory(self, items: List[Any], today) -> Dict[str, Any]:
        """Analyze current inventory status."""
        total_items = len(items)
        total_value = 0.0
        categories = defaultdict(int)
        status_counts = defaultdict(int)
        
        for item in items:
            # Count by category
            category = self._categorize_item(item.name)
            categories[category] += 1
            
            # Count by status
            status, _ = compute_status(item.expiry_date, today)
            status_counts[status] += 1
            
            # Estimate value (if price available)
            if hasattr(item, 'price') and item.price:
                total_value += float(item.price or 0)
                
        return {
            'total_items': total_items,
            'estimated_value': round(total_value, 2),
            'categories': dict(categories),
            'status_distribution': dict(status_counts),
            'freshness_score': self._calculate_freshness_score(status_counts, total_items)
        }
        
    def _analyze_waste_trends(self, historical: Dict, days: int = 30) -> Dict[str, Any]:
        """Analyze waste trends over the specified period."""
        cutoff = datetime.now(UTC) - timedelta(days=days)
        
        waste_events = []
        for event in historical.get('waste_events', []):
            event_date = datetime.fromisoformat(event['date'])
            if event_date >= cutoff:
                waste_events.append(event)
                
        # Calculate waste metrics
        total_waste_items = len(waste_events)
        waste_by_category = defaultdict(int)
        waste_by_reason = defaultdict(int)
        estimated_waste_value = 0.0
        
        for event in waste_events:
            category = self._categorize_item(event['item_name'])
            waste_by_category[category] += 1
            waste_by_reason[event.get('reason', 'expired')] += 1
            estimated_waste_value += event.get('estimated_value', 0)
            
        return {
            'period_days': days,
            'total_waste_items': total_waste_items,
            'waste_by_category': dict(waste_by_category),
            'waste_by_reason': dict(waste_by_reason),
            'estimated_waste_value': round(estimated_waste_value, 2),
            'waste_rate': round(total_waste_items / days, 2) if days > 0 else 0
        }
        
        
    def _analyze_consumption_patterns(self, items: List[Any]) -> Dict[str, Any]:
        """Analyze consumption patterns and efficiency."""
        patterns = {
            'high_consumption': [],
            'low_consumption': [],
            'efficient_items': [],
            'avg_consumption_rate': 0.0
        }
        
        consumption_rates = []
        for item in items:
            if hasattr(item, 'consumption_per_day') and item.consumption_per_day:
                rate = item.consumption_per_day
                consumption_rates.append(rate)
                
                if rate > 0.5:  # High consumption
                    patterns['high_consumption'].append({
                        'name': item.name,
                        'rate': rate,
                        'unit': item.unit
                    })
                elif rate < 0.1:  # Low consumption
                    patterns['low_consumption'].append({
                        'name': item.name,
                        'rate': rate,
                        'unit': item.unit
                    })
                    
                # Efficient items (good consumption rate vs expiry)
                if item.expiry_date and rate > 0:
                    from utils.expiry_utils import compute_status
                    status, days_left = compute_status(item.expiry_date)
                    if days_left and days_left > 0:
                        efficiency = rate * days_left / (item.remaining_quantity or 1)
                        if efficiency > 0.8:  # Will be consumed efficiently
                            patterns['efficient_items'].append({
                                'name': item.name,
                                'efficiency_score': round(efficiency, 2)
                            })
                            
        patterns['avg_consumption_rate'] = round(
            sum(consumption_rates) / len(consumption_rates), 3
        ) if consumption_rates else 0.0
        
        return patterns
        
    def _generate_predictions(self, items: List[Any], historical: Dict, today) -> Dict[str, Any]:
        """Generate predictions for waste, consumption, and shopping needs."""
        predictions = {
            'waste_risk_items': [],
            'finish_soon': [],
            'reorder_suggestions': []
        }
        
        for item in items:
            if item.expiry_date and item.remaining_quantity:
                from utils.expiry_utils import compute_status, predict_finish_date
                
                status, days_left = compute_status(item.expiry_date, today)
                finish_date = predict_finish_date(
                    item.consumption_per_day, 
                    item.remaining_quantity, 
                    today
                )
                
                # Waste risk prediction
                if finish_date and item.expiry_date:
                    if finish_date > item.expiry_date:
                        risk_days = (finish_date - item.expiry_date).days
                        predictions['waste_risk_items'].append({
                            'name': item.name,
                            'risk_level': 'high' if risk_days > 3 else 'medium',
                            'excess_days': risk_days,
                            'suggested_action': 'increase_consumption' if risk_days > 5 else 'cook_soon'
                        })
                        
                # Finishing soon
                if finish_date and (finish_date - today).days <= 7:
                    predictions['finish_soon'].append({
                        'name': item.name,
                        'finish_date': finish_date.isoformat(),
                        'days_remaining': (finish_date - today).days
                    })
                    
                # Reorder suggestions
                if finish_date and (finish_date - today).days <= 3:
                    predictions['reorder_suggestions'].append({
                        'name': item.name,
                        'suggested_quantity': item.quantity or 1,
                        'urgency': 'high' if (finish_date - today).days <= 1 else 'medium'
                    })
                    
        return predictions
        
    def _generate_insights(self, inventory: Dict, waste_trends: Dict) -> List[str]:
        """Generate actionable insights from analytics."""
        insights = []
        
        # Freshness insights
        freshness = inventory.get('freshness_score', 0)
        if freshness > 0.8:
            insights.append("🌟 Excellent! Your inventory freshness is very high.")
        elif freshness < 0.6:
            insights.append("⚠️ Consider using items sooner - freshness score is low.")
            
        # Waste insights
        waste_rate = waste_trends.get('waste_rate', 0)
        if waste_rate < 0.5:
            insights.append("✅ Great job! Your waste rate is very low.")
        elif waste_rate > 2.0:
            insights.append("📉 High waste detected. Consider smaller purchases or faster consumption.")
            
        # Category insights
        waste_by_category = waste_trends.get('waste_by_category', {})
        if waste_by_category:
            top_waste_category = max(waste_by_category.items(), 
                                   key=lambda x: x[1], default=(None, 0))
            if top_waste_category[0] and top_waste_category[1] > 2:
                insights.append(f"🥬 Most waste in {top_waste_category[0]} - consider buying less or using faster.")
        
        # Inventory insights
        total_items = inventory.get('total_items', 0)
        if total_items == 0:
            insights.append("📦 Your pantry is empty. Time to go shopping!")
        elif total_items > 20:
            insights.append("📦 You have a well-stocked pantry. Good planning!")
            
        return insights
        
    def _categorize_item(self, name: str) -> str:
        """Categorize item by name."""
        name_lower = (name or '').lower()
        
        if any(word in name_lower for word in ['milk', 'curd', 'yogurt', 'cheese', 'paneer', 'butter']):
            return 'dairy'
        elif any(word in name_lower for word in ['spinach', 'carrot', 'onion', 'potato', 'tomato', 'vegetable']):
            return 'vegetables'
        elif any(word in name_lower for word in ['apple', 'banana', 'orange', 'fruit']):
            return 'fruits'
        elif any(word in name_lower for word in ['rice', 'wheat', 'flour', 'dal', 'lentil']):
            return 'grains_pulses'
        elif any(word in name_lower for word in ['bread', 'biscuit', 'cake']):
            return 'bakery'
        elif any(word in name_lower for word in ['oil', 'ghee']):
            return 'oils'
        else:
            return 'other'
            
    def _calculate_freshness_score(self, status_counts: Dict, total: int) -> float:
        """Calculate overall freshness score (0-1)."""
        if total == 0:
            return 1.0
            
        fresh_count = status_counts.get('fresh', 0)
        soon_count = status_counts.get('soon', 0)
        expired_count = status_counts.get('expired', 0)
        
        # Weight: fresh=1.0, soon=0.5, expired=0.0
        score = (fresh_count * 1.0 + soon_count * 0.5) / total if total > 0 else 0.0
        return round(score, 2)
        
    def _load_historical_data(self) -> Dict[str, Any]:
        """Load historical analytics data."""
        try:
            if os.path.exists(self.analytics_path):
                with open(self.analytics_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return {'waste_events': [], 'avg_waste_rate': 1.0}
        
    def _save_analytics(self, analytics: Dict[str, Any]):
        """Save analytics data."""
        try:
            with open(self.analytics_path, 'w', encoding='utf-8') as f:
                json.dump(analytics, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
            
    def log_waste_event(self, item_name: str, reason: str = 'expired', estimated_value: float = 0.0):
        """Log a waste event for analytics."""
        historical = self._load_historical_data()
        
        event = {
            'date': datetime.now(UTC).isoformat(),
            'item_name': item_name,
            'reason': reason,
            'estimated_value': estimated_value
        }
        
        historical['waste_events'].append(event)
        
        # Keep only last 90 days of events
        cutoff = datetime.now(UTC) - timedelta(days=90)
        historical['waste_events'] = [
            e for e in historical['waste_events']
            if datetime.fromisoformat(e['date']) >= cutoff
        ]
        
        try:
            with open(self.analytics_path, 'w', encoding='utf-8') as f:
                json.dump(historical, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
