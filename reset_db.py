from common.db import get_connection, init_db

def reset_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM tasks;")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='tasks';")

    conn.commit()
    conn.close()
    print("数据库已清空")

if __name__ == "__main__":
    init_db()
    reset_db()