import os
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from apscheduler.schedulers.background import BackgroundScheduler

from database import db, init_db
from models import Item, SurveyResponse, CookedRecipe
from utils.vision_utils import extract_items_from_bill, extract_expiry_date_from_image
from utils.expiry_utils import compute_status, get_default_shelf_life_days, predict_finish_date
from utils.survey_utils import update_item_from_survey
from utils.consumption_policies import is_single_use
from utils.alias_resolver import resolve_alias, normalize_name
from utils.ml_unit_predictor import predict_unit_and_category
from utils.cpd_suggestor import suggest_cpd
from utils.event_log import log_event, compute_rolling_cpd
from utils.recipe_engine import load_recipes, PantryItem, score_recipes, plan_meals, generate_recipe_suggestions
from utils.enhanced_ocr import enhanced_ocr
from utils.analytics import WasteAnalytics
from utils.ai_survey import AISurveyEngine
from utils.item_categorizer import categorize_item, get_category_info, predict_expiry_days
from utils.smart_shopping_list import generate_smart_shopping_list
from utils.usage_tracker import get_usage_tracker



def infer_unit(pname: str) -> str:
    n = (pname or '').lower()
    # eggs/packaged pieces
    if any(k in n for k in ['egg', 'eggs', 'dozen']):
        return 'pcs'
    # dairy liquids
    if any(k in n for k in ['milk', 'curd', 'lassi', 'buttermilk', 'yogurt', 'dahi', 'cream']):
        return 'l'
    # common bulk foods default to kg
    if any(k in n for k in [
        'flour', 'atta', 'maida', 'suji', 'rava', 'rice', 'dal', 'lentil', 'bean', 'peas', 'channa', 'gram',
        'wheat', 'millet', 'ragi', 'jowar', 'bajra',
        'sugar', 'salt',
        'vegetable', 'tomato', 'onion', 'potato', 'ginger', 'garlic', 'cabbage', 'brinjal', 'chilli', 'capsicum',
        'carrot', 'beet', 'cucumber', 'spinach', 'greens', 'leaf',
        'orange', 'banana', 'apple', 'grape', 'mango', 'papaya', 'guava', 'corn',
        'paneer', 'cheese', 'tofu',
        'meat', 'chicken', 'mutton', 'fish'
    ]):
        return 'kg'
    # edible oils, ghee, juices typically in liters
    if any(k in n for k in ['oil', 'ghee', 'juice', 'syrup', 'vinegar']):
        return 'l'
    # bakery or packaged items default to pieces/pack
    if any(k in n for k in ['bread', 'bun', 'pack', 'packet', 'biscuit', 'cookie', 'chocolate', 'bar']):
        return 'pcs'
    return ''

def load_notifications(upload_folder: str) -> dict:
    """Load notifications from JSON file."""
    notifications = {'expiring_soon': [], 'low_stock': [], 'generated_at': None}
    try:
        import json
        notif_path = os.path.join(upload_folder, 'notifications.json')
        if os.path.exists(notif_path):
            with open(notif_path, 'r', encoding='utf-8') as f:
                notifications = json.load(f)
    except Exception:
        pass
    return notifications

def low_stock_threshold(name: str, unit: str | None) -> float:
    """Determine low stock threshold based on item type and unit."""
    u = (unit or '').lower()
    n = (name or '').lower()
    
    # Zero stock is always considered low stock
    # Use small thresholds to catch items with very low quantities
    
    if u in ('kg', 'g', 'gm', 'gram', 'grams'):
        if any(word in n for word in ['rice', 'flour', 'atta', 'dal', 'sugar', 'salt']):
            return 0.5  # Staples - 500g threshold
        elif any(word in n for word in ['spice', 'masala', 'powder']):
            return 0.05  # Spices - 50g threshold
        else:
            return 0.2  # Other items - 200g threshold
    
    elif u in ('l', 'lt', 'liter', 'litre', 'liters', 'litres', 'ml'):
        if any(word in n for word in ['milk', 'oil', 'ghee']):
            return 0.2  # Essential liquids - 200ml threshold
        else:
            return 0.1  # Other liquids - 100ml threshold
    
    elif u in ('pcs', 'pc', 'piece', 'pieces', 'pack', 'packet'):
        if 'egg' in n:
            return 2.0  # Eggs - 2 pieces threshold
        elif any(word in n for word in ['bread', 'biscuit', 'milk']):
            return 0.5  # Essential items - 0.5 pieces threshold
        else:
            return 0.5  # Other countable items - 0.5 pieces threshold
    
    # Default threshold for unknown units - very low to catch zero quantities
    return 0.1


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///shelflife.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    upload_dir = os.path.join(os.path.dirname(__file__), 'uploads')
    os.makedirs(upload_dir, exist_ok=True)
    app.config['UPLOAD_FOLDER'] = upload_dir

    # Scheduler: compute notifications daily and refresh rolling CPD
    def compute_notifications():
        with app.app_context():
            items = Item.query.all()
            today = datetime.now(timezone.utc).date()
            expiring_soon = []
            low_stock = []
            shopping_list = []
            # Rolling CPD from event logs (last 14 days)
            try:
                rolling = compute_rolling_cpd(app.config['UPLOAD_FOLDER'], days=14)
            except Exception:
                rolling = {}
            # Apply rolling CPD if higher confidence than zero and differs significantly
            for it in items:
                if it.id in rolling:
                    est = rolling[it.id]
                    if est and est > 0:
                        # adopt if current is missing or differs by >30%
                        if not it.consumption_per_day or abs((it.consumption_per_day - est) / max(est, 1e-6)) > 0.3:
                            it.consumption_per_day = est
                status, days_left = compute_status(it.expiry_date, today)
                thr = low_stock_threshold(it.name, it.unit)
                # Calculate finish prediction for both notifications and shopping list
                finish_pred = predict_finish_date(it.consumption_per_day, it.remaining_quantity, today)
                
                if status == 'expired' or (days_left is not None and days_left <= 3):
                    expiring_soon.append({
                        'id': it.id,
                        'name': it.name,
                        'days_left': days_left,
                        'expiry_date': str(it.expiry_date) if it.expiry_date else None,
                    })
                if (it.remaining_quantity or 0) < thr:
                    low_stock.append({
                        'id': it.id,
                        'name': it.name,
                        'remaining': it.remaining_quantity,
                        'unit': it.unit,
                        'threshold': thr,
                        'finish_pred': str(finish_pred) if finish_pred else None,
                    })
                # Build shopping list: if below threshold OR predicted to finish within 5d
                soon = False
                if finish_pred:
                    try:
                        soon = (finish_pred - today).days <= 5
                    except Exception:
                        soon = False
                if (it.remaining_quantity or 0) < thr or soon:
                    shopping_list.append({
                        'id': it.id,
                        'name': it.name,
                        'suggested_qty': max(thr - (it.remaining_quantity or 0), 0),
                        'unit': it.unit,
                        'reason': 'low' if (it.remaining_quantity or 0) < thr else 'soon',
                        'finish_pred': str(finish_pred) if finish_pred else None,
                    })
            try:
                import json
                notif_path = os.path.join(app.config['UPLOAD_FOLDER'], 'notifications.json')
                db.session.commit()
                with open(notif_path, 'w', encoding='utf-8') as f:
                    json.dump({'expiring_soon': expiring_soon, 'low_stock': low_stock, 'generated_at': str(today)}, f, ensure_ascii=False, indent=2)
                shop_path = os.path.join(app.config['UPLOAD_FOLDER'], 'shopping_list.json')
                with open(shop_path, 'w', encoding='utf-8') as f:
                    json.dump({'items': shopping_list, 'generated_at': str(today)}, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(compute_notifications, 'interval', days=1, id='daily_notifications', replace_existing=True)
    try:
        scheduler.start()
    except Exception:
        pass

    init_db(app)

    @app.route('/')
    def index():
        return redirect(url_for('dashboard'))

    @app.route('/upload_bill', methods=['GET', 'POST'])
    def upload_bill():
        if request.method == 'POST':
            file = request.files.get('bill_image')
            if not file or file.filename == '':
                flash('Please select an image file.')
                return redirect(request.url)
            filename = secure_filename(file.filename)
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(path)

            # Extract but do not save yet; show review screen
            items = extract_items_from_bill(path)
            session['pending_items'] = items
            session['pending_upload_path'] = path
            if not items:
                flash('No items detected from OCR. You can adjust in the review screen or add manually.')
            notifications = load_notifications(app.config['UPLOAD_FOLDER'])
            return render_template('result.html', items=items, notifications=notifications)

        notifications = load_notifications(app.config['UPLOAD_FOLDER'])
        return render_template('index.html', notifications=notifications)

    @app.route('/confirm_bill', methods=['POST'])
    def confirm_bill():
        # Save reviewed items from form
        rows = []
        n = int(request.form.get('row_count', 0))
        for i in range(n):
            name = request.form.get(f'name_{i}', '').strip()
            qty = request.form.get(f'qty_{i}', '0').strip()
            unit = request.form.get(f'unit_{i}', '').strip()
            price = request.form.get(f'price_{i}', '0').strip()
            if not name:
                continue
            try:
                qty_f = float(qty or 0) or 0.0
            except ValueError:
                qty_f = 0.0
            try:
                price_f = float(price or 0) or 0.0
            except ValueError:
                price_f = 0.0
            rows.append({'name': name, 'quantity': qty_f, 'unit': unit, 'price': price_f})

        created = 0
        today = datetime.now(timezone.utc).date()

        # Gather existing names once for alias resolution (tuples -> first element)
        existing_names = [row[0] for row in Item.query.with_entities(Item.name).all()]
        for it in rows:
            # Alias resolution
            canonical, changed = resolve_alias(it['name'], existing_names)
            name_final = canonical
            if changed:
                flash(f"Merged '{it['name']}' into existing '{canonical}'")
                # Keep list in sync for subsequent rows
                existing_names.append(canonical)
            # Unit prediction (fallback to rule)
            unit_final = it['unit'] or predict_unit_and_category(name_final)[0] or infer_unit(name_final) or None
            default_days = get_default_shelf_life_days(name_final)
            expiry_date = None
            if default_days:
                expiry_date = today + timedelta(days=default_days)
            # Merge into existing row if same canonical name and same expiry_date
            existing_match = None
            if expiry_date is not None:
                for ex in Item.query.filter(Item.name.ilike(name_final)).all():
                    if ex.expiry_date == expiry_date:
                        existing_match = ex
                        break
            else:
                for ex in Item.query.filter(Item.name.ilike(name_final)).all():
                    if ex.expiry_date is None:
                        existing_match = ex
                        break
            if existing_match:
                # Increase quantities
                existing_match.quantity = (existing_match.quantity or 0) + it['quantity']
                existing_match.remaining_quantity = (existing_match.remaining_quantity or 0) + it['quantity']
                # Prefer a unit if missing
                if not existing_match.unit and unit_final:
                    existing_match.unit = unit_final
                created += 0  # merged
            else:
                item = Item(
                    name=name_final,
                    quantity=it['quantity'],
                    unit=unit_final,
                    price=it['price'],
                    added_date=datetime.now(timezone.utc),
                    expiry_date=expiry_date,
                    remaining_quantity=it['quantity'],
                    consumption_per_day=None,
                )
                db.session.add(item)
                created += 1
        db.session.commit()
        session.pop('pending_items', None)
        session.pop('pending_upload_path', None)
        flash(f'Added {created} items.')
        return redirect(url_for('dashboard'))

    @app.route('/dashboard', methods=['GET', 'POST'])
    def dashboard():
        items = Item.query.order_by(Item.added_date.desc()).all()

        # Handle actions
        if request.method == 'POST':
            action = request.form.get('action')

            # Handle add_item first (no item_id required)
            if action == 'add_item':
                name = (request.form.get('new_name') or '').strip()
                if not name:
                    flash('Name is required to add an item')
                    return redirect(url_for('dashboard'))
                try:
                    qty = float(request.form.get('new_qty') or 0)
                except ValueError:
                    qty = 0.0
                unit = (request.form.get('new_unit') or '').strip()
                price = 0.0
                exp = request.form.get('new_expiry')
                expiry_date = None
                if exp:
                    try:
                        expiry_date = datetime.strptime(exp, '%Y-%m-%d').date()
                    except ValueError:
                        expiry_date = None
                if not expiry_date:
                    # Try smart categorization for expiry prediction
                    category, confidence = categorize_item(name)
                    predicted_days = predict_expiry_days(category, name)
                    if predicted_days:
                        expiry_date = datetime.now(timezone.utc).date() + timedelta(days=predicted_days)
                    else:
                        # Fallback to original method
                        default_days = get_default_shelf_life_days(name)
                        if default_days:
                            expiry_date = datetime.now(timezone.utc).date() + timedelta(days=default_days)
                # Alias + unit prediction
                existing_names = [row[0] for row in Item.query.with_entities(Item.name).all()]
                canonical, changed = resolve_alias(name, existing_names)
                if changed:
                    flash(f"Merged '{name}' into existing '{canonical}'")
                unit_pred = predict_unit_and_category(canonical)[0]
                final_unit = (unit or unit_pred or infer_unit(canonical) or None)
                # Merge with existing if same name + same expiry
                merged = False
                if expiry_date is not None:
                    ex = Item.query.filter(Item.name.ilike(canonical), Item.expiry_date == expiry_date).first()
                else:
                    ex = Item.query.filter(Item.name.ilike(canonical), Item.expiry_date.is_(None)).first()
                if ex:
                    ex.quantity = (ex.quantity or 0) + qty
                    ex.remaining_quantity = (ex.remaining_quantity or 0) + qty
                    if not ex.unit and final_unit:
                        ex.unit = final_unit
                    merged = True
                else:
                    it = Item(
                        name=canonical,
                        quantity=qty,
                        unit=final_unit,
                        price=price,
                        added_date=datetime.now(timezone.utc),
                        expiry_date=expiry_date,
                        remaining_quantity=qty,
                        consumption_per_day=None,
                    )
                    db.session.add(it)
                db.session.commit()
                try:
                    compute_notifications()
                except Exception:
                    pass
                flash('Item merged' if merged else 'Item added')
                return redirect(url_for('dashboard'))

            # Handle bulk actions
            if action == 'bulk_delete':
                item_ids = request.form.getlist('item_ids')
                if item_ids:
                    try:
                        # Remove dependent survey rows first
                        for item_id in item_ids:
                            SurveyResponse.query.filter_by(item_id=int(item_id)).delete()
                        # Delete items
                        Item.query.filter(Item.id.in_(item_ids)).delete(synchronize_session=False)
                        db.session.commit()
                        flash(f'Deleted {len(item_ids)} items')
                    except Exception as e:
                        db.session.rollback()
                        flash('Error deleting items')
                return redirect(url_for('dashboard'))

            if action == 'bulk_update_expiry':
                item_ids = request.form.getlist('item_ids')
                expiry_date_str = request.form.get('expiry_date')
                if item_ids and expiry_date_str:
                    try:
                        expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
                        items_to_update = Item.query.filter(Item.id.in_(item_ids)).all()
                        for item in items_to_update:
                            item.expiry_date = expiry_date
                        db.session.commit()
                        flash(f'Updated expiry date for {len(item_ids)} items')
                    except ValueError:
                        flash('Invalid date format')
                    except Exception as e:
                        db.session.rollback()
                        flash('Error updating expiry dates')
                return redirect(url_for('dashboard'))

            # Handle recipe actions (no specific item required)
            if action == 'cook_recipe':
                title = (request.form.get('recipe_title') or '').strip()
                # Recompute best usage and deduct from pantry
                today_local = datetime.now(timezone.utc).date()
                # Build pantry snapshot
                pantry = [
                    PantryItem(id=it.id, name=it.name, unit=it.unit, remaining=it.remaining_quantity or 0, expiry=it.expiry_date)
                    for it in items
                ]
                base_dir = os.path.dirname(__file__)
                recipes = load_recipes(base_dir)
                scored = score_recipes(recipes, pantry, today_local)
                usage_map = None
                for score, r, match_info in scored:
                    if r.get('title') == title:
                        # Create usage map from recipe ingredients and match info
                        usage_map = {}
                        for ing in r.get('ingredients', []):
                            ing_name = ing.get('name', '')
                            required_qty = float(ing.get('qty', 0))
                            if ing_name and required_qty > 0:
                                usage_map[ing_name] = required_qty
                        break
                if usage_map:
                    # Track ingredients used for cooking history
                    ingredients_used = []
                    items_used_count = 0
                    
                    # Deduct quantities from the first matching batches for each ingredient
                    for ing_name, use_qty in usage_map.items():
                        if use_qty and use_qty > 0:
                            # Find first matching item by normalized name
                            for it in items:
                                n = (it.name or '')
                                if ing_name.lower() in (n or '').lower():
                                    prev = it.remaining_quantity or 0.0
                                    actual_used = min(use_qty, prev)  # Can't use more than available
                                    it.remaining_quantity = max(0.0, prev - actual_used)
                                    
                                    # Track what was used
                                    ingredients_used.append({
                                        'name': it.name,
                                        'required': use_qty,
                                        'used': actual_used,
                                        'unit': it.unit or '',
                                        'remaining_after': it.remaining_quantity
                                    })
                                    items_used_count += 1
                                    
                                    try:
                                        log_event(app.config['UPLOAD_FOLDER'], item_id=it.id, prev_remaining=prev, new_remaining=it.remaining_quantity)
                                        # Log usage for consumption tracking
                                        tracker = get_usage_tracker(app.config['UPLOAD_FOLDER'])
                                        tracker.log_usage(it.id, it.name, actual_used, it.unit or '', 'cooking', recipe_name=title)
                                    except Exception:
                                        pass
                                    break
                    
                    # Calculate nutrition for the recipe
                    nutrition_data = None
                    try:
                        from utils.nutrition_calculator import calculate_recipe_nutrition
                        # Get recipe ingredients for nutrition calculation
                        recipe_ingredients = []
                        for score, r, match_info in scored:
                            if r.get('title') == title:
                                recipe_ingredients = r.get('ingredients', [])
                                break
                        
                        if recipe_ingredients:
                            nutrition_result = calculate_recipe_nutrition(recipe_ingredients)
                            nutrition_data = nutrition_result['total']
                    except Exception as e:
                        print(f"Error calculating nutrition: {e}")
                    
                    # Save cooking history with nutrition
                    try:
                        import json
                        cooked_recipe = CookedRecipe(
                            recipe_title=title,
                            ingredients_used=json.dumps(ingredients_used),
                            total_items_used=items_used_count,
                            calories=nutrition_data['calories'] if nutrition_data else None,
                            protein_g=nutrition_data['protein_g'] if nutrition_data else None,
                            carbs_g=nutrition_data['carbs_g'] if nutrition_data else None,
                            fat_g=nutrition_data['fat_g'] if nutrition_data else None,
                            fiber_g=nutrition_data['fiber_g'] if nutrition_data else None
                        )
                        db.session.add(cooked_recipe)
                    except Exception as e:
                        print(f"Error saving cooking history: {e}")
                    
                    db.session.commit()
                    
                    # Create detailed flash message
                    ingredient_summary = ", ".join([f"{ing['name']} ({ing['used']:.1f} {ing['unit']})" for ing in ingredients_used[:3]])
                    if len(ingredients_used) > 3:
                        ingredient_summary += f" and {len(ingredients_used) - 3} more"
                    
                    flash(f"🍳 Cooked {title}! Used: {ingredient_summary}", 'success')
                else:
                    flash('Could not compute usage for recipe', 'error')
                return redirect(url_for('dashboard'))

            # For other actions, we require an existing item
            item_id_raw = request.form.get('item_id')
            try:
                item_id_int = int(item_id_raw)
            except (TypeError, ValueError):
                flash('Item not found')
                return redirect(request.url)
            item = db.session.get(Item, item_id_int)
            if not item:
                flash('Item not found')
                return redirect(request.url)

            if action == 'upload_expiry_photo':
                ef = request.files.get('expiry_image')
                if ef and ef.filename:
                    filename = secure_filename(f"expiry_{item.id}_" + ef.filename)
                    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    ef.save(path)
                    date = extract_expiry_date_from_image(path)
                    if date:
                        item.expiry_date = date
                        db.session.commit()
                        try:
                            compute_notifications()
                        except Exception:
                            pass
                        flash(f'Expiry date set to {date} for {item.name}')
                    else:
                        flash('Could not detect expiry date from image')
                else:
                    flash('Please select an expiry image')
                return redirect(url_for('dashboard'))

            if action == 'update_remaining':
                try:
                    remaining = float(request.form.get('remaining_quantity') or 0)
                except ValueError:
                    flash('Invalid remaining quantity')
                    return redirect(url_for('dashboard'))
                prev = item.remaining_quantity or 0.0
                item.remaining_quantity = max(0.0, remaining)
                db.session.commit()
                try:
                    log_event(app.config['UPLOAD_FOLDER'], item_id=item.id, prev_remaining=prev, new_remaining=item.remaining_quantity)
                    # Log usage if quantity decreased
                    if prev > item.remaining_quantity:
                        used_qty = prev - item.remaining_quantity
                        tracker = get_usage_tracker(app.config['UPLOAD_FOLDER'])
                        tracker.log_usage(item.id, item.name, used_qty, item.unit or '', 'direct')
                except Exception:
                    pass
                try:
                    compute_notifications()
                except Exception:
                    pass
                flash('Remaining quantity updated')
                return redirect(url_for('dashboard'))

            if action == 'consume_pack':
                # Single-use convenience: mark as consumed
                prev = item.remaining_quantity or 0.0
                item.remaining_quantity = 0.0
                db.session.commit()
                try:
                    log_event(app.config['UPLOAD_FOLDER'], item_id=item.id, prev_remaining=prev, new_remaining=item.remaining_quantity)
                except Exception:
                    pass
                try:
                    compute_notifications()
                except Exception:
                    pass
                flash('Marked pack as consumed')
                return redirect(url_for('dashboard'))

            if action == 'update_item':
                # Inline edit for name/unit/price
                new_name = (request.form.get('name') or item.name).strip()
                item.name = new_name
                u = (request.form.get('unit') or item.unit or '').strip()
                if not u:
                    u = infer_unit(new_name)
                item.unit = u or None
                try:
                    price = request.form.get('price')
                    if price is not None and price != '':
                        item.price = float(price)
                except ValueError:
                    pass
                # Optional direct expiry date from date input
                exp = request.form.get('expiry_date')
                if exp:
                    try:
                        item.expiry_date = datetime.strptime(exp, '%Y-%m-%d').date()
                    except ValueError:
                        pass
                db.session.commit()
                try:
                    compute_notifications()
                except Exception:
                    pass
                flash('Item updated')
                return redirect(url_for('dashboard'))

            # (add_item handled earlier)

            if action == 'delete_item':
                # Remove dependent survey rows first to avoid FK issues
                try:
                    SurveyResponse.query.filter_by(item_id=item.id).delete()
                except Exception:
                    pass
                db.session.delete(item)
                db.session.commit()
                try:
                    compute_notifications()
                except Exception:
                    pass
                flash('Item deleted')
                return redirect(url_for('dashboard'))

        # Prepare view model
        vm = []
        today = datetime.now(timezone.utc).date()
        # Order items alphabetically by name (case-insensitive), then by expiry date (None last)
        items_sorted = sorted(items, key=lambda x: (x.name.lower() if x.name else '', x.expiry_date or datetime.max.date()))
        for it in items_sorted:
            status, days_left = compute_status(it.expiry_date, today)
            finish_pred = predict_finish_date(it.consumption_per_day, it.remaining_quantity, today)
            thr = low_stock_threshold(it.name, it.unit)
            is_low_qty = (it.remaining_quantity or 0) < thr
            is_low_time = False
            if finish_pred:
                try:
                    is_low_time = (finish_pred - today).days <= 3
                except Exception:
                    is_low_time = False
            # Single-use detection: keywords OR small pack sizes by unit/quantity
            u = (it.unit or '').lower()
            qty = it.quantity if it.quantity is not None else (it.remaining_quantity or 0)
            small_pack = False
            if u in ('g', 'gm', 'gram', 'grams') and qty and qty <= 300:
                small_pack = True
            if u in ('ml',) and qty and qty <= 500:
                small_pack = True
            if 'pack' in (it.name or '').lower() or 'sachet' in (it.name or '').lower():
                small_pack = True
            single_flag = is_single_use(it.name) or small_pack
            vm.append({
                'item': it,
                'status': status,
                'days_left': days_left,
                'finish_pred': finish_pred,
                'is_low': is_low_qty or is_low_time,
                'low_reason': 'qty' if is_low_qty else ('time' if is_low_time else ''),
                'low_threshold': thr,
                'is_single_use': single_flag,
            })

        # Chart data
        expiring_counts = {
            'Expired/Today': sum(1 for x in vm if x['status'] == 'expired'),
            'Soon (<=3d)': sum(1 for x in vm if x['status'] == 'soon'),
            'Safe (>3d)': sum(1 for x in vm if x['status'] == 'fresh'),
            'No Date': sum(1 for x in vm if x['status'] == 'unknown'),
        }
        consumption_series = [
            {'name': it.name, 'cpd': it.consumption_per_day or 0} for it in items
        ]

        low_items = [x for x in vm if x['is_low']]
        # Enhanced recipe suggestions and analytics
        try:
            pantry = [
                PantryItem(id=it.id, name=it.name, unit=it.unit, remaining=it.remaining_quantity or 0, expiry=it.expiry_date)
                for it in items
            ]
            
            # Generate enhanced recipe suggestions
            recipe_data = generate_recipe_suggestions(pantry, preferences={})
            top_recipes = recipe_data.get('suggestions', [])[:8]  # Show more recipes
            meal_plan = recipe_data.get('meal_plan', [])
            
        except Exception as e:
            print(f"ERROR generating recipes: {e}")
            import traceback
            traceback.print_exc()
            top_recipes = []
            meal_plan = []
        
        # Get recent cooked recipes
        try:
            recent_cooked = CookedRecipe.query.order_by(CookedRecipe.cooked_at.desc()).limit(5).all()
        except Exception as e:
            print(f"ERROR loading cooked recipes: {e}")
            recent_cooked = []
        
        # Compute analytics
        try:
            analytics_engine = WasteAnalytics(app.config['UPLOAD_FOLDER'])
            analytics = analytics_engine.compute_analytics(items)
        except Exception as e:
            print(f"ERROR in analytics: {e}")
            analytics = {'insights': [], 'savings': {}, 'waste_trends': {}, 'inventory': {}}
        # Keep notifications/shopping list fresh on each dashboard load
        try:
            compute_notifications()
        except Exception:
            pass
        # Load shopping list JSON
        shopping_list = []
        try:
            import json
            shop_path = os.path.join(app.config['UPLOAD_FOLDER'], 'shopping_list.json')
            if os.path.exists(shop_path):
                with open(shop_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    shopping_list = data.get('items', [])
        except Exception:
            shopping_list = []
        # Load notifications JSON
        notifications = {'expiring_soon': [], 'low_stock': [], 'generated_at': None}
        try:
            import json
            notif_path = os.path.join(app.config['UPLOAD_FOLDER'], 'notifications.json')
            if os.path.exists(notif_path):
                with open(notif_path, 'r', encoding='utf-8') as f:
                    notifications = json.load(f)
        except Exception:
            pass
        return render_template(
            'dashboard.html',
            items_vm=vm,
            low_items=low_items,
            expiring_counts=expiring_counts,
            consumption_series=consumption_series,
            shopping_list=shopping_list,
            notifications=notifications,
            top_recipes=top_recipes,
            meal_plan=meal_plan,
            recent_cooked=recent_cooked,
            analytics=analytics,
            get_category_info=lambda name: get_category_info(categorize_item(name)[0]),
        )

    @app.route('/consume_pack', methods=['POST'])
    def consume_pack():
        try:
            item_id = int(request.form.get('item_id'))
        except (TypeError, ValueError):
            flash('Item not found')
            return redirect(url_for('dashboard'))
        item = db.session.get(Item, item_id)
        if not item:
            flash('Item not found')
            return redirect(url_for('dashboard'))
        item.remaining_quantity = 0.0
        db.session.commit()
        flash('Marked pack as consumed')
        return redirect(url_for('dashboard'))

    @app.route('/survey', methods=['GET', 'POST'])
    def survey():
        items = Item.query.order_by(Item.added_date.desc()).all()
        ai_survey = AISurveyEngine(app.config['UPLOAD_FOLDER'])

        if request.method == 'POST':
            action = request.form.get('action') or ''
            
            if action == 'save_settings':
                try:
                    hs = int(request.form.get('household_size') or 2)
                except ValueError:
                    hs = 2
                cf = (request.form.get('cooking_frequency') or 'mostly_home').strip()
                settings = {'household_size': max(1, hs), 'cooking_frequency': cf or 'mostly_home'}
                ai_survey.save_settings(settings)
                flash('Settings saved successfully! AI will use this to improve predictions.')
                return redirect(url_for('survey'))

            if action == 'save_item':
                try:
                    item_id = int(request.form.get('item_id'))
                    per_day = float(request.form.get('per_day') or 0)
                except (TypeError, ValueError):
                    flash('Invalid input')
                    return redirect(url_for('survey'))
                    
                item = Item.query.get(item_id)
                if not item:
                    flash('Item not found')
                    return redirect(url_for('survey'))
                    
                # Update consumption rate
                old_cpd = item.consumption_per_day or 0
                item.consumption_per_day = max(0.0, per_day)
                
                # Log the learning event
                log_event(item.name, 'cpd_updated', {
                    'old_cpd': old_cpd,
                    'new_cpd': per_day,
                    'source': 'ai_survey'
                })
                
                db.session.commit()
                flash(f'Updated {item.name} consumption rate. AI is learning from your input!')
                return redirect(url_for('survey'))

        # Generate AI analysis and questions
        settings = ai_survey._load_settings()
        analysis = ai_survey.analyze_consumption_confidence(items)
        questions = ai_survey.generate_smart_questions(items)

        notifications = load_notifications(app.config['UPLOAD_FOLDER'])
        return render_template('survey.html', 
                             items=items, 
                             settings=settings, 
                             analysis=analysis,
                             questions=questions,
                             notifications=notifications)

    @app.route('/daily-usage')
    def daily_usage():
        """Daily usage logging interface."""
        items = Item.query.all()
        tracker = get_usage_tracker(app.config['UPLOAD_FOLDER'])
        
        # Get today's usage summary
        today_summary = tracker.get_daily_usage_summary()
        
        # Get suggested items to log
        suggestions = tracker.suggest_items_to_log()
        
        # Get recent usage patterns for display
        recent_patterns = {}
        for item in items[:20]:  # Show patterns for first 20 items
            insights = tracker.get_usage_insights(item.id)
            if insights.get('avg_daily_consumption', 0) > 0:
                recent_patterns[item.id] = {
                    'item': item,
                    'insights': insights
                }
        
        notifications = load_notifications(app.config['UPLOAD_FOLDER'])
        return render_template('daily_usage.html',
                             items=items,
                             today_summary=today_summary,
                             suggestions=suggestions,
                             recent_patterns=recent_patterns,
                             notifications=notifications)
    
    @app.route('/nutrition-tracker')
    def nutrition_tracker():
        """Nutrition tracking and insights page."""
        from utils.nutrition_calculator import get_nutrition_insights, compare_with_average
        from datetime import timedelta
        
        # Get all cooked recipes with nutrition data
        all_recipes = CookedRecipe.query.order_by(CookedRecipe.cooked_at.desc()).all()
        
        # Filter recipes with nutrition data
        recipes_with_nutrition = [r for r in all_recipes if r.calories is not None]
        
        # Today's meals
        today = datetime.now(timezone.utc).date()
        today_meals = [r for r in recipes_with_nutrition 
                      if r.cooked_at.date() == today]
        
        # Calculate today's totals
        today_totals = {
            'calories': sum(r.calories or 0 for r in today_meals),
            'protein_g': sum(r.protein_g or 0 for r in today_meals),
            'carbs_g': sum(r.carbs_g or 0 for r in today_meals),
            'fat_g': sum(r.fat_g or 0 for r in today_meals),
            'fiber_g': sum(r.fiber_g or 0 for r in today_meals),
            'meal_count': len(today_meals)
        }
        
        # Last 7 days data for charts
        seven_days_ago = today - timedelta(days=6)
        weekly_data = []
        for i in range(7):
            day = seven_days_ago + timedelta(days=i)
            day_meals = [r for r in recipes_with_nutrition 
                        if r.cooked_at.date() == day]
            daily_total = {
                'date': day.strftime('%b %d'),
                'calories': sum(r.calories or 0 for r in day_meals),
                'protein_g': sum(r.protein_g or 0 for r in day_meals),
                'carbs_g': sum(r.carbs_g or 0 for r in day_meals),
                'fat_g': sum(r.fat_g or 0 for r in day_meals)
            }
            weekly_data.append(daily_total)
        
        # Calculate historical average (last 30 days)
        thirty_days_ago = today - timedelta(days=30)
        historical_meals = [r for r in recipes_with_nutrition 
                           if r.cooked_at.date() >= thirty_days_ago]
        
        historical_avg = {}
        if historical_meals:
            historical_avg = {
                'calories': sum(r.calories or 0 for r in historical_meals) / len(historical_meals),
                'protein_g': sum(r.protein_g or 0 for r in historical_meals) / len(historical_meals),
                'carbs_g': sum(r.carbs_g or 0 for r in historical_meals) / len(historical_meals),
                'fat_g': sum(r.fat_g or 0 for r in historical_meals) / len(historical_meals)
            }
        
        # Generate insights for today
        insights = []
        if today_totals['calories'] > 0:
            insights = get_nutrition_insights(today_totals)
        
        # Compare with average
        comparisons = []
        if today_totals['calories'] > 0 and historical_avg:
            comparisons = compare_with_average(today_totals, historical_avg)
        
        # Recent meals (last 10)
        recent_meals = recipes_with_nutrition[:10]
        
        notifications = load_notifications(app.config['UPLOAD_FOLDER'])
        return render_template('nutrition_tracker.html',
                             today_totals=today_totals,
                             today_meals=today_meals,
                             weekly_data=weekly_data,
                             historical_avg=historical_avg,
                             insights=insights,
                             comparisons=comparisons,
                             recent_meals=recent_meals,
                             notifications=notifications)
    
    @app.route('/log-usage', methods=['POST'])
    def log_usage():
        """Log usage of items."""
        try:
            item_id = int(request.form.get('item_id'))
            quantity_used = float(request.form.get('quantity_used', 0))
            meal_context = request.form.get('meal_context', 'unknown')
            usage_type = request.form.get('usage_type', 'meal_logging')
            
            item = Item.query.get(item_id)
            if not item:
                flash('Item not found')
                return redirect(url_for('daily_usage'))
            
            if quantity_used <= 0:
                flash('Please enter a valid quantity')
                return redirect(url_for('daily_usage'))
            
            # Log the usage
            tracker = get_usage_tracker(app.config['UPLOAD_FOLDER'])
            tracker.log_usage(item.id, item.name, quantity_used, item.unit or '', 
                            usage_type, meal_context)
            
            # Update remaining quantity if requested
            if request.form.get('update_remaining') == 'true':
                prev = item.remaining_quantity or 0.0
                item.remaining_quantity = max(0.0, prev - quantity_used)
                db.session.commit()
                
                # Log the quantity change
                try:
                    log_event(app.config['UPLOAD_FOLDER'], item_id=item.id, 
                            prev_remaining=prev, new_remaining=item.remaining_quantity)
                except Exception:
                    pass
            
            flash(f'Logged usage: {quantity_used} {item.unit} of {item.name}')
            
        except (ValueError, TypeError):
            flash('Invalid input values')
        except Exception as e:
            flash('Error logging usage')
        
        return redirect(url_for('daily_usage'))

    @app.route('/shopping-list')
    def shopping_list():
        """Generate and display smart shopping list."""
        items = Item.query.all()
        
        # Generate smart shopping list
        shopping_items = generate_smart_shopping_list(items, days_ahead=14)
        
        # Categorize items for better display
        from utils.smart_shopping_list import shopping_list_generator
        categorized_items = shopping_list_generator.categorize_shopping_list(shopping_items)
        summary = shopping_list_generator.get_shopping_summary(shopping_items)
        
        # Get category info for display
        category_info = {}
        for category in categorized_items.keys():
            category_info[category] = get_category_info(category)
        
        notifications = load_notifications(app.config['UPLOAD_FOLDER'])
        return render_template('shopping_list.html',
                             shopping_items=shopping_items,
                             categorized_items=categorized_items,
                             category_info=category_info,
                             summary=summary,
                             notifications=notifications)

    @app.route('/favicon.ico')
    def favicon():
        return app.send_static_file('favicon.svg')

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
