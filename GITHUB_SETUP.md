# GitHub Setup Guide for ShelfLife Project

## ✅ Step 1: Git Configuration (DONE)
Your Git is already configured:
```
user.name=navalcn
user.email=navalcn4002@gmail.com
```

---

## 📋 Step 2: Create .gitignore File

Create a `.gitignore` file in the project root to exclude unnecessary files:

```bash
cd C:\Users\Naval\Documents\ShelfLife
```

Then create `.gitignore`:

```
# Virtual Environment
.venv/
.venv312/
venv/
env/

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Flask
instance/
.webassets-cache

# Database
*.db
*.sqlite
*.sqlite3

# IDE
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store

# Uploads & Logs
uploads/
logs/
*.log

# Environment variables
.env
.env.local

# Google credentials
service_account.json

# OS
Thumbs.db
.DS_Store

# Temporary files
*.tmp
*.temp
```

---

## 🔑 Step 3: Create GitHub Repository

1. Go to https://github.com/new
2. Create a new repository named: `ShelfLife` (or `shelflife`)
3. **DO NOT** initialize with README, .gitignore, or license (we'll add them)
4. Click "Create repository"
5. Copy the repository URL (e.g., `https://github.com/navalcn/ShelfLife.git`)

---

## 🚀 Step 4: Initialize Git & Push to GitHub

Run these commands in Git Bash in your project directory:

```bash
# Navigate to project
cd C:\Users\Naval\Documents\ShelfLife

# Initialize git repository
git init

# Add all files (respecting .gitignore)
git add .

# Create initial commit
git commit -m "Initial commit: ShelfLife - Food Inventory Management System"

# Add remote repository (replace with your GitHub URL)
git remote add origin https://github.com/navalcn/ShelfLife.git

# Rename branch to main (if needed)
git branch -M main

# Push to GitHub
git push -u origin main
```

---

## 📝 Step 5: Create README.md (if not exists)

Your project already has a README, but verify it has:

```markdown
# ShelfLife+ 🥬

A comprehensive food inventory management system with smart expiry tracking, recipe suggestions, and waste analytics.

## Features

- 📸 **Bill Scanning**: Extract items from receipts using OCR
- 🥗 **Smart Recipes**: AI-powered recipe suggestions based on available ingredients
- 📊 **Analytics**: Track waste, consumption patterns, and savings
- 🛒 **Shopping List**: Smart shopping recommendations
- 📅 **Expiry Tracking**: Automatic expiry date prediction
- 🍽️ **Meal Planning**: Generate optimized meal plans

## Installation

1. Clone the repository:
```bash
git clone https://github.com/navalcn/ShelfLife.git
cd ShelfLife
```

2. Create virtual environment:
```bash
python -m venv .venv312
.venv312\Scripts\activate  # On Windows
source .venv312/bin/activate  # On macOS/Linux
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
python app.py
```

5. Open browser and go to: http://localhost:5000

## Configuration

Set Google Vision API credentials (optional):
```bash
set GOOGLE_APPLICATION_CREDENTIALS=path\to\service_account.json
```

## Project Structure

```
ShelfLife/
├── app.py                 # Main Flask application
├── models.py              # Database models
├── database.py            # Database initialization
├── requirements.txt       # Python dependencies
├── recipes.json           # Recipe database
├── expiry_data.json       # Default expiry times
├── utils/                 # Utility modules
│   ├── recipe_engine.py
│   ├── item_categorizer.py
│   ├── analytics.py
│   └── [more utilities]
├── templates/             # HTML templates
├── static/                # CSS & JavaScript
└── uploads/               # Temporary files
```

## Recent Fixes

- ✅ Fixed recipe cooking quantity deduction bug
- ✅ Fixed timezone compatibility (Python 3.10+)
- ✅ Fixed meal planning crashes
- ✅ Fixed item categorization scoring
- ✅ Fixed analytics undefined variables
- ✅ Fixed drumstick categorization (now vegetables)

## Future Improvements

- Add comprehensive logging
- Add unit tests
- Add waste prediction
- Add cost analytics
- Add mobile app support

## License

MIT License - feel free to use this project for personal or commercial purposes.

## Author

Naval Choudhary - [@navalcn](https://github.com/navalcn)
```

---

## ✅ Step 6: Verify Push

After pushing, verify on GitHub:

1. Go to https://github.com/navalcn/ShelfLife
2. Check that all files are there
3. Verify the commit message appears

---

## 🔄 Step 7: Future Commits

For future changes:

```bash
# Make changes to files

# Stage changes
git add .

# Commit with message
git commit -m "Description of changes"

# Push to GitHub
git push origin main
```

---

## 📌 Common Commands

```bash
# Check status
git status

# View commit history
git log --oneline

# View changes
git diff

# Undo last commit (keep changes)
git reset --soft HEAD~1

# Undo last commit (discard changes)
git reset --hard HEAD~1

# Create a new branch
git checkout -b feature-name

# Switch branches
git checkout main

# Merge branch
git merge feature-name
```

---

## 🐛 Troubleshooting

### Authentication Error
If you get authentication errors, use SSH instead:
```bash
git remote set-url origin git@github.com:navalcn/ShelfLife.git
```

### Large Files
If you get "file too large" error, add to .gitignore:
```bash
git rm --cached large_file.db
git add .gitignore
git commit -m "Remove large file from tracking"
```

### Merge Conflicts
If you get merge conflicts:
```bash
# View conflicts
git status

# After resolving conflicts manually
git add .
git commit -m "Resolve merge conflicts"
```

---

## 📊 Repository Settings (Recommended)

After pushing, go to GitHub repository settings:

1. **General**
   - Add description: "Food inventory management system with smart expiry tracking"
   - Add topics: `python`, `flask`, `inventory`, `recipe`, `food-waste`

2. **Branches**
   - Set main as default branch
   - Enable branch protection rules

3. **Security**
   - Enable vulnerability alerts
   - Enable dependabot

4. **Pages**
   - (Optional) Enable GitHub Pages for documentation

---

## 🎉 You're Done!

Your ShelfLife project is now on GitHub! 

**Next Steps:**
1. Share the repository link
2. Add collaborators if needed
3. Set up CI/CD (GitHub Actions) for automated testing
4. Create issues for future improvements
5. Use GitHub Discussions for community feedback

