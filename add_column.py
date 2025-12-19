from common.db import get_connection

conn = get_connection()
cursor = conn.cursor()

cursor.execute("ALTER TABLE tasks ADD COLUMN last_error TEXT;")

conn.commit()
conn.close()