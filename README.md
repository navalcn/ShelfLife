# ShelfLife+ 🥬

A comprehensive **AI-powered food inventory management system** with smart expiry tracking, recipe suggestions, waste analytics, and intelligent meal planning.

Built with **Flask**, **SQLite**, **Google Vision API**, and **Machine Learning**.

---

## ✨ Features

### 📸 **Bill Scanning & OCR**
- Upload grocery bill images
- Multi-model OCR (Donut + EasyOCR) for accurate item extraction
- Automatic item categorization and unit prediction
- Graceful fallback if Vision API unavailable

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

4. **(Optional) Set Google Vision API credentials:**
```bash
set GOOGLE_APPLICATION_CREDENTIALS=path\to\service_account.json  # Windows
export GOOGLE_APPLICATION_CREDENTIALS=path/to/service_account.json  # macOS/Linux
```

5. **Run the application:**
```bash
python app.py
```

6. **Open in browser:**
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
├── recipes.json                # Recipe database (50+ recipes)
├── expiry_data.json            # Default expiry times
├── consumption_priors.json     # Consumption patterns
│
├── utils/                      # Utility modules
│   ├── recipe_engine.py        # Recipe scoring & meal planning
│   ├── item_categorizer.py     # Smart item categorization
│   ├── analytics.py            # Waste & consumption analytics
│   ├── expiry_utils.py         # Expiry date calculations
│   ├── vision_utils.py         # Google Vision API integration
│   ├── enhanced_ocr.py         # Multi-model OCR (Donut + EasyOCR)
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
│   ├── css/style.css           # Styling
│   └── js/script.js            # Frontend logic
│
└── uploads/                    # Temporary files & data
```

---

## 🐛 Recent Bug Fixes (v1.0)

✅ **10 Critical Bugs Fixed:**
1. Recipe cooking quantity deduction error
2. Timezone import compatibility (Python 3.10+)
3. Meal planning crash on ingredient conflicts
4. Item categorization over-normalization
5. Division by zero in coverage calculation
6. Duplicate datetime imports
7. Analytics lazy import performance issue
8. Models UTC import compatibility
9. Analytics undefined variables crash
10. Drumstick miscategorized as beverage

---

## 🎯 Key Technologies

- **Backend**: Flask, SQLAlchemy, SQLite
- **Frontend**: HTML5, CSS3, JavaScript, Chart.js
- **ML/AI**: Google Vision API, Donut OCR, EasyOCR, RapidFuzz
- **Data**: JSON, Event logging, Analytics engine
- **Deployment**: Python 3.10+

---

## 📊 Usage Examples

### Add Items from Bill
1. Go to Dashboard
2. Click "Upload Bill"
3. Select receipt image
4. System extracts items automatically
5. Review and confirm

### Get Recipe Suggestions
1. Go to Dashboard
2. View "Suggested Recipes" section
3. Recipes ranked by:
   - Ingredient availability
   - Expiring items priority
   - User preferences
4. Click recipe to cook and deduct ingredients

### Track Consumption
1. Go to "Daily Usage"
2. Log items consumed
3. System learns consumption patterns
4. Improves predictions over time

### View Analytics
1. Go to Dashboard
2. Check "Waste Trends" and "Insights"
3. See consumption patterns
4. Get personalized recommendations

---

## 🔧 Configuration

### Default Expiry Times
Edit `expiry_data.json` to customize default shelf life for items.

### Recipes
Edit `recipes.json` to add/modify recipes.

### Consumption Patterns
Edit `consumption_priors.json` to adjust consumption estimates.

---

## 🚀 Future Improvements

- [ ] Add comprehensive logging system
- [ ] Add unit tests and CI/CD
- [ ] Add waste prediction ML model
- [ ] Add cost analytics and budget tracking
- [ ] Add mobile app (React Native)
- [ ] Add seasonal ingredient awareness
- [ ] Add social sharing features
- [ ] Add multi-user support
- [ ] Add cloud backup
- [ ] Add voice commands

---

## 📝 Notes

- If Google Vision API is not configured, OCR will gracefully skip
- You can manually add/update items on the dashboard
- Default shelf life values are in `expiry_data.json`
- Consumption data is stored locally in SQLite
- All calculations are done server-side for privacy

---

## 📄 License

MIT License - Feel free to use this project for personal or commercial purposes.

---

## 👨‍💻 Author

**Naval Choudhary**
- GitHub: [@navalcn](https://github.com/navalcn)
- Email: navalcn4002@gmail.com

---

## 🤝 Contributing

Contributions are welcome! Feel free to:
- Report bugs
- Suggest features
- Submit pull requests
- Improve documentation

---

## 📞 Support

For issues or questions:
1. Check existing GitHub issues
2. Create a new issue with details
3. Include error messages and steps to reproduce

---

**Made with ❤️ for reducing food waste**
