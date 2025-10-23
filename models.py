from datetime import datetime, timezone
from database import db


class Item(db.Model):
    __tablename__ = 'items'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)

    quantity = db.Column(db.Float, nullable=False, default=1.0)
    unit = db.Column(db.String(32), nullable=True)
    price = db.Column(db.Float, nullable=True)

    added_date = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    expiry_date = db.Column(db.Date, nullable=True)

    remaining_quantity = db.Column(db.Float, nullable=True)
    consumption_per_day = db.Column(db.Float, nullable=True)

    def __repr__(self):
        return f'<Item {self.id} {self.name}>'


class SurveyResponse(db.Model):
    __tablename__ = 'survey_responses'
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=False)
    responded_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    use_per_day = db.Column(db.Float, nullable=False)
    remaining = db.Column(db.Float, nullable=False)

    item = db.relationship('Item', backref=db.backref('surveys', lazy=True))


class CookedRecipe(db.Model):
    __tablename__ = 'cooked_recipes'
    id = db.Column(db.Integer, primary_key=True)
    recipe_title = db.Column(db.String(200), nullable=False)
    cooked_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    
    # Store ingredients used as JSON
    ingredients_used = db.Column(db.Text, nullable=True)  # JSON string
    total_items_used = db.Column(db.Integer, default=0)
    
    def __repr__(self):
        return f'<CookedRecipe {self.id} {self.recipe_title}>'
