# ShelfLife+ 🥬

A comprehensive **AI-powered food inventory management system** with smart expiry tracking, recipe suggestions, waste analytics, and intelligent meal planning.

Built with **Flask**, **SQLite**, **Donut OCR**, **EasyOCR**, and **Machine Learning**.

---

## ✨ Features

### 📸 **Bill Scanning & OCR**
- Upload grocery bill images
- Multi-model OCR: Donut (primary) + EasyOCR (fallback) for accurate item extraction
- Automatic item categorization and unit prediction
- Enhanced OCR pipeline with ensemble scoring
- No external API dependencies - works completely offline

### 🥗 **Smart Recipe Engine**
- AI-powered recipe suggestions based on available ingredients
- Fuzzy matching with category-aware ingredient matching
- Meal planning with variety and ingredient conflict detection
- Nutritional estimation and difficulty scaling
- Expiring ingredient prioritization

### 📊 **Analytics & Insights**
- Waste tracking and trend analysis
- Consumption pattern recognition
- Freshness scoring and inventory health
- Predictive waste risk assessment
- Cost and savings analytics

### 🛒 **Smart Shopping List**
- Intelligent recommendations based on consumption patterns
- Low-stock alerts
- Category-based organization
- Price tracking and budget optimization

### 📅 **Expiry Management**
- Automatic expiry date prediction
- Smart categorization (vegetables, dairy, meat, etc.)
- Color-coded status (fresh, soon, expired)
- Consumption rate tracking
- Finish date prediction

### 📈 **Dashboard & Tracking**
- Real-time inventory overview
- Color-coded items by expiry status
- Daily usage tracking
- Survey-based consumption refinement
- Event logging for analytics

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- pip
- Git

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/navalcn/ShelfLife.git
cd ShelfLife
```

2. **Create virtual environment:**
```bash
python -m venv .venv312
.venv312\Scripts\activate  # On Windows
source .venv312/bin/activate  # On macOS/Linux
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Run the application:**
```bash
python app.py
```

5. **Open in browser:**
```
http://localhost:5000
```

---

## 📁 Project Structure

```
ShelfLife/
├── app.py                      # Main Flask application
├── models.py                   # SQLAlchemy database models
├── database.py                 # Database initialization
├── requirements.txt            # Python dependencies
├── recipes.json                # Recipe database (30+ recipes)
├── expiry_data.json            # Default expiry times
├── consumption_priors.json     # Consumption patterns
│
├── utils/                      # Utility modules
│   ├── recipe_engine.py        # Recipe scoring & meal planning
│   ├── item_categorizer.py     # Smart item categorization
│   ├── analytics.py            # Waste & consumption analytics
│   ├── expiry_utils.py         # Expiry date calculations
│   ├── vision_utils.py         # OCR utilities (Donut + EasyOCR)
│   ├── enhanced_ocr.py         # Enhanced OCR pipeline with ensemble scoring
│   ├── alias_resolver.py       # Item name normalization
│   ├── consumption_policies.py # Single-use item detection
│   ├── event_log.py            # Usage event tracking
│   ├── usage_tracker.py        # Consumption rate estimation
│   ├── ml_unit_predictor.py    # Unit prediction
│   ├── smart_shopping_list.py  # Shopping recommendations
│   ├── ai_receipt.py           # Receipt parsing
│   ├── ai_survey.py            # Survey-based learning
│   ├── cpd_suggestor.py        # Consumption rate suggestions
│   └── survey_utils.py         # Survey utilities
│
├── templates/                  # HTML templates
│   ├── base.html               # Base template
│   ├── dashboard.html          # Main dashboard
│   ├── daily_usage.html        # Usage tracking
│   ├── survey.html             # Consumption survey
│   ├── shopping_list.html      # Shopping recommendations
│   └── [more templates]
│
├── static/                     # Static files
│   ├── css/style.css           # Custom CSS (minimal - uses TailwindCSS)
│   └── js/script.js            # Toast notifications & date picker
│
└── uploads/                    # Temporary files & data
```

---

## 🎯 Key Technologies

- **Backend**: Flask, SQLAlchemy, SQLite
- **Frontend**: HTML5, TailwindCSS, JavaScript, Flatpickr, Lucide Icons
- **ML/AI**: Donut OCR, EasyOCR, RapidFuzz, Transformers, PyTorch
- **Data**: JSON, Event logging, Analytics engine
- **Deployment**: Python 3.10+

---

## 📊 Usage Examples

### Add Items from Bill
1. Go to home page (redirects to dashboard)
2. Click "Upload Bill" or go to `/upload_bill`
3. Select receipt image
4. System extracts items using Donut OCR (with EasyOCR fallback)
5. Review extracted items on confirmation page
6. Confirm to add to inventory

### Get Recipe Suggestions
1. Go to Dashboard (`/dashboard`)
2. View "Suggested Recipes" section (auto-generated)
3. Recipes ranked by:
   - Ingredient availability and coverage
   - Expiring items priority (bonus scoring)
   - Confidence matching and category awareness
4. Click "Cook Recipe" to deduct ingredients automatically

### Track Consumption
1. Go to "Daily Usage" (`/daily-usage`)
2. Log items consumed with quantities
3. System tracks usage patterns via event logging
4. Rolling CPD (Consumption Per Day) calculation
5. Improves finish date predictions over time

### View Analytics
1. Dashboard shows real-time analytics
2. Waste trends analysis (30-day window)
3. Freshness scoring and inventory health
4. Personalized insights and recommendations
5. Consumption pattern recognition

---

## 🔧 Configuration

### Default Expiry Times
Edit `expiry_data.json` - contains 11 basic items with shelf life in days.

### Recipes
Edit `recipes.json` - contains 30+ Indian recipes with ingredients, quantities, time, difficulty, and tags.

### Consumption Patterns
Edit `consumption_priors.json` - contains per-person-per-day consumption estimates for 18 common items.

### Advanced Categorization
The system uses `utils/item_categorizer.py` with 12 categories and 200+ keywords for smart classification.

---

## 🌐 Available Routes

- `/` - Home (redirects to dashboard)
- `/upload_bill` - Upload and scan grocery bills
- `/confirm_bill` - Review and confirm extracted items
- `/dashboard` - Main inventory dashboard with analytics
- `/survey` - AI-powered consumption survey
- `/daily-usage` - Daily usage tracking interface
- `/log-usage` - Log item consumption
- `/shopping-list` - Smart shopping recommendations
- `/consume_pack` - Mark items as consumed

---

## 📝 Notes

- OCR works completely offline using Donut and EasyOCR
- You can manually add/update items on the dashboard
- Default shelf life values are in `expiry_data.json`
- Consumption data is stored locally in SQLite
- All calculations are done server-side for privacy
- No external API dependencies required

---

## 📄 License

MIT License - Feel free to use this project for personal or commercial purposes.

---

**Made with ❤️ for reducing food waste**
