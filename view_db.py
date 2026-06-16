import os
import psycopg2
from dotenv import load_dotenv

load_dotenv(".env")

def view_tables():
    db_url = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    
    # نمایش کاربران ثبت نام شده
    print("--- USERS ---")
    cursor.execute("SELECT * FROM users;")
    for row in cursor.fetchall():
        print(row)
        
    print("\n--- RECENT MATCHES ---")
    cursor.execute("SELECT home_team, away_team, home_score, away_score, status FROM matches LIMIT 5;")
    for row in cursor.fetchall():
        print(row)
        
    cursor.close()
    conn.close()

if __name__ == "__main__":
    view_tables()