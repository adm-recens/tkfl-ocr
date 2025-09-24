import sqlite3

db_path = "data/ocr.sqlite3"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Try to add crop_data column
try:
    cur.execute("ALTER TABLE vouchers_master ADD COLUMN crop_data TEXT;")
    print("Column 'crop_data' added successfully.")
except sqlite3.OperationalError as e:
    print(f"Error: {e} (column may already exist)")

# Print schema
cur.execute("PRAGMA table_info(vouchers_master)")
print("Schema for vouchers_master:")
for col in cur.fetchall():
    print(col)

conn.commit()
conn.close()