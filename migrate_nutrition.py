"""
Migration script to add nutrition columns to cooked_recipes table
Run this once to update your database
"""
import sqlite3
import os

def migrate_database():
    """Add nutrition columns to cooked_recipes table."""
    db_path = os.path.join('instance', 'shelflife.db')
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        print("The database will be created automatically when you run the app.")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if columns already exist
    cursor.execute("PRAGMA table_info(cooked_recipes)")
    columns = [row[1] for row in cursor.fetchall()]
    
    columns_to_add = [
        ('calories', 'INTEGER'),
        ('protein_g', 'REAL'),
        ('carbs_g', 'REAL'),
        ('fat_g', 'REAL'),
        ('fiber_g', 'REAL')
    ]
    
    for col_name, col_type in columns_to_add:
        if col_name not in columns:
            try:
                cursor.execute(f"ALTER TABLE cooked_recipes ADD COLUMN {col_name} {col_type}")
                print(f"[OK] Added column: {col_name}")
            except sqlite3.OperationalError as e:
                print(f"[ERROR] Error adding {col_name}: {e}")
        else:
            print(f"[SKIP] Column {col_name} already exists")
    
    conn.commit()
    conn.close()
    print("\n[SUCCESS] Database migration complete!")

if __name__ == '__main__':
    migrate_database()
