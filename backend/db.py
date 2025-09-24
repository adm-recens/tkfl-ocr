# backend/db.py
import sqlite3
import os
print(f"[DEBUG] Loaded db.py from: {__file__}, module: {__name__}")
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.path.join(PROJECT_ROOT, "data", "ocr.sqlite3")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
print(f"[DEBUG] Using DB_PATH: {DB_PATH}")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.path.join(PROJECT_ROOT, "data", "ocr.sqlite3")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
print(f"[DEBUG] Loaded db.py from: {__file__}, module: {__name__}")
print(f"[DEBUG] Using DB_PATH: {DB_PATH}")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create master table for receipts / vouchers."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS vouchers_master (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_name TEXT,
        voucher_no TEXT,
        voucher_date TEXT,
        supplier_code TEXT,
        raw_ocr TEXT,
        parsed_json TEXT,
        crop_data TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()
