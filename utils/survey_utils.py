from models import Item


def update_item_from_survey(item: Item, per_day: float, remaining: float):
    item.consumption_per_day = max(0.0, float(per_day))
    item.remaining_quantity = max(0.0, float(remaining))
