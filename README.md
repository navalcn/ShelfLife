# ShelfLife+

AI-powered grocery tracker built with Flask, SQLite, and Google Vision API.

## Features
- Upload grocery bill images → OCR via Google Vision → extract items
- Track items with expiry dates and consumption
- Color-coded dashboard and charts via Chart.js
- Quick surveys to refine consumption predictions

## Setup
1. Create and activate a virtual environment.
2. Install dependencies:
```
pip install -r requirements.txt
```
3. Set Google credentials (if using Vision):
```
set GOOGLE_APPLICATION_CREDENTIALS=path\to\service_account.json
```
4. Run the server:
```
python app.py
```

## Notes
- If Vision is not configured, OCR will gracefully skip and you can add/update items on the dashboard.
- Default shelf life values are in `expiry_data.json`.
