from __future__ import annotations
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta, timezone
import json
import os
from utils.ml_unit_predictor import predict_unit_and_category
from utils.event_log import compute_rolling_cpd

UTC = timezone.utc

class AISurveyEngine:
    """AI-powered survey system for intelligent consumption prediction and learning."""
    
    def __init__(self, upload_folder: str):
        self.upload_folder = upload_folder
        self.priors_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'consumption_priors.json')
        self.settings_path = os.path.join(upload_folder, 'survey_settings.json')
        
    def analyze_consumption_confidence(self, items: List[Any]) -> Dict[str, Any]:
        """Analyze confidence levels for each item's consumption rate."""
        analysis = {
            'high_confidence': [],
            'medium_confidence': [], 
            'low_confidence': [],
            'needs_attention': [],
            'learning_opportunities': []
        }
        
        for item in items:
            confidence_score = self._calculate_confidence(item)
            item_analysis = {
                'id': item.id,
                'name': item.name,
                'confidence_score': confidence_score,
                'reasons': self._get_confidence_reasons(item, confidence_score),
                'suggested_cpd': self._get_ai_suggestion(item),
                'current_cpd': item.consumption_per_day or 0,
                'remaining': item.remaining_quantity or item.quantity or 0,
                'unit': item.unit,
                'days_until_expiry': (item.expiry_date - datetime.now(UTC).date()).days if item.expiry_date else None
            }
            
            if confidence_score >= 0.8:
                analysis['high_confidence'].append(item_analysis)
            elif confidence_score >= 0.5:
                analysis['medium_confidence'].append(item_analysis)
            else:
                analysis['low_confidence'].append(item_analysis)
                
            # Flag items needing immediate attention
            if item_analysis['days_until_expiry'] and item_analysis['days_until_expiry'] <= 3:
                analysis['needs_attention'].append(item_analysis)
                
            # Flag learning opportunities (items with usage history but poor predictions)
            if self._has_usage_history(item) and confidence_score < 0.6:
                analysis['learning_opportunities'].append(item_analysis)
        
        return analysis
    
    def _calculate_confidence(self, item: Any) -> float:
        """Calculate confidence score for an item's consumption prediction."""
        confidence_factors = []
        
        # Factor 1: Historical usage data (40% weight)
        historical_cpd = compute_rolling_cpd(item.name, days=30)
        if historical_cpd and historical_cpd > 0:
            confidence_factors.append(0.4)
        elif self._has_usage_history(item):
            confidence_factors.append(0.2)
        else:
            confidence_factors.append(0.0)
            
        # Factor 2: Category knowledge (30% weight)
        _, category = predict_unit_and_category(item.name)
        if category and category != 'unknown':
            confidence_factors.append(0.3)
        else:
            confidence_factors.append(0.1)
            
        # Factor 3: Static priors availability (20% weight)
        if self._has_static_prior(item.name):
            confidence_factors.append(0.2)
        else:
            confidence_factors.append(0.05)
            
        # Factor 4: User feedback history (10% weight)
        if self._has_user_feedback(item):
            confidence_factors.append(0.1)
        else:
            confidence_factors.append(0.0)
            
        return min(1.0, sum(confidence_factors))
    
    def _get_confidence_reasons(self, item: Any, confidence_score: float) -> List[str]:
        """Get human-readable reasons for confidence score."""
        reasons = []
        
        historical_cpd = compute_rolling_cpd(item.name, days=30)
        if historical_cpd and historical_cpd > 0:
            reasons.append(f"📊 Based on 30-day usage history ({historical_cpd:.3f}/day)")
        elif self._has_usage_history(item):
            reasons.append("📈 Some usage history available")
        else:
            reasons.append("❓ No usage history - new item")
            
        _, category = predict_unit_and_category(item.name)
        if category and category != 'unknown':
            reasons.append(f"🏷️ Categorized as {category}")
        else:
            reasons.append("🤷 Unknown category")
            
        if self._has_static_prior(item.name):
            reasons.append("📚 Based on nutrition guidelines")
        else:
            reasons.append("🔍 Estimated from similar items")
            
        if confidence_score < 0.3:
            reasons.append("⚠️ Low confidence - please review")
        elif confidence_score < 0.6:
            reasons.append("⚡ Medium confidence - may need adjustment")
        else:
            reasons.append("✅ High confidence prediction")
            
        return reasons
    
    def _get_ai_suggestion(self, item: Any) -> float:
        """Get AI-powered consumption suggestion."""
        settings = self._load_settings()
        
        # Priority 1: Historical data
        historical_cpd = compute_rolling_cpd(item.name, days=30)
        if historical_cpd and historical_cpd > 0:
            return round(historical_cpd, 3)
            
        # Priority 2: Static priors
        static_cpd = self._get_static_prior(item.name)
        if static_cpd:
            return self._adjust_for_household(static_cpd, settings)
            
        # Priority 3: Category-based estimation
        return self._estimate_from_category(item, settings)
    
    def _adjust_for_household(self, base_cpd: float, settings: Dict) -> float:
        """Adjust consumption rate for household size and cooking frequency."""
        household_size = settings.get('household_size', 2)
        cooking_freq = settings.get('cooking_frequency', 'mostly_home')
        
        cooking_multipliers = {
            'mostly_home': 1.0,
            'mixed': 0.6,
            'mostly_out': 0.35
        }
        
        multiplier = cooking_multipliers.get(cooking_freq, 1.0)
        return round(base_cpd * household_size * multiplier, 3)
    
    def _estimate_from_category(self, item: Any, settings: Dict) -> float:
        """Estimate consumption from category defaults."""
        _, category = predict_unit_and_category(item.name)
        
        # Conservative category defaults (per person per day)
        category_defaults = {
            'grain_pulse': 0.08,
            'veg_leafy': 0.12,
            'veg_root': 0.10,
            'fruit': 0.10,
            'dairy': 0.18,
            'bakery': 0.12,
            'oil': 0.02,
            'snack': 0.03,
            'spice': 0.005,
            'beverage': 0.05
        }
        
        base_cpd = category_defaults.get(category, 0.03)
        return self._adjust_for_household(base_cpd, settings)
    
    def generate_smart_questions(self, items: List[Any]) -> List[Dict[str, Any]]:
        """Generate intelligent survey questions based on confidence analysis."""
        analysis = self.analyze_consumption_confidence(items)
        questions = []
        
        # Focus on low confidence and needs attention items
        priority_items = analysis['low_confidence'] + analysis['needs_attention']
        
        for item in priority_items[:10]:  # Limit to 10 questions max
            question = {
                'type': 'consumption_rate',
                'item_id': item['id'],
                'question': self._generate_question_text(item),
                'suggested_answer': item['suggested_cpd'],
                'current_answer': item['current_cpd'],
                'confidence_reasons': item['reasons'],
                'urgency': 'high' if item in analysis['needs_attention'] else 'medium'
            }
            questions.append(question)
            
        # Add household context questions if not set
        settings = self._load_settings()
        if not settings.get('household_size'):
            questions.insert(0, {
                'type': 'household_context',
                'question': 'How many people are in your household?',
                'field': 'household_size',
                'default': 2
            })
            
        if not settings.get('cooking_frequency'):
            questions.insert(1, {
                'type': 'cooking_context', 
                'question': 'How often do you cook at home?',
                'field': 'cooking_frequency',
                'options': [
                    {'value': 'mostly_home', 'label': 'Mostly at home (5+ days/week)'},
                    {'value': 'mixed', 'label': 'Mix of home and outside (2-4 days/week)'},
                    {'value': 'mostly_out', 'label': 'Mostly outside (0-1 days/week)'}
                ],
                'default': 'mostly_home'
            })
            
        return questions
    
    def _generate_question_text(self, item: Dict) -> str:
        """Generate contextual question text for an item."""
        name = item['name']
        unit = item['unit'] or 'units'
        remaining = item['remaining']
        days_until_expiry = item['days_until_expiry']
        
        if days_until_expiry and days_until_expiry <= 3:
            return f"⚠️ {name} expires in {days_until_expiry} days! How much do you typically consume per day?"
        elif item['confidence_score'] < 0.3:
            return f"🤔 We're not sure about {name}. How much do you typically use per day?"
        else:
            return f"📊 How much {name} does your household typically consume per day?"
    
    def _load_settings(self) -> Dict:
        """Load survey settings."""
        try:
            if os.path.exists(self.settings_path):
                with open(self.settings_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return {'household_size': 2, 'cooking_frequency': 'mostly_home'}
    
    def save_settings(self, settings: Dict) -> None:
        """Save survey settings."""
        try:
            with open(self.settings_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2)
        except Exception:
            pass
    
    def _has_usage_history(self, item: Any) -> bool:
        """Check if item has any usage history."""
        # This would check event logs for any consumption events
        return compute_rolling_cpd(item.name, days=90) is not None
    
    def _has_static_prior(self, name: str) -> bool:
        """Check if item has static consumption prior."""
        return self._get_static_prior(name) is not None
    
    def _get_static_prior(self, name: str) -> Optional[float]:
        """Get static consumption prior for item."""
        try:
            if os.path.exists(self.priors_path):
                with open(self.priors_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                key = name.lower()
                for k, v in data.items():
                    if k in key:
                        return float(v.get('ppd', 0))
        except Exception:
            pass
        return None
    
    def _has_user_feedback(self, item: Any) -> bool:
        """Check if user has provided feedback on this item."""
        # This would check if user has manually adjusted CPD for this item
        return item.consumption_per_day is not None and item.consumption_per_day > 0
