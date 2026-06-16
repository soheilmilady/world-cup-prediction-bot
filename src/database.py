import os
import psycopg2
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_url=None):
        # خواندن آدرس دیتابیس ابری از متغیرهای محیطی
        self.db_url = db_url or os.getenv("DATABASE_URL")
        if not self.db_url:
            raise ValueError("خطا: DATABASE_URL در متغیرهای محیطی یافت نشد!")
        self.init_db()

    def get_connection(self):
        """ایجاد اتصال به دیتابیس ابری PostgreSQL"""
        conn = psycopg2.connect(self.db_url)
        return conn

    def init_db(self):
        """ساخت جداول دیتابیس در صورت عدم وجود در سرور ابری"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # ۱. جدول کاربران
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                total_score INTEGER DEFAULT 0
            )
        """)

        # ۲. جدول مسابقات
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS matches (
                match_id INTEGER PRIMARY KEY,
                home_team TEXT,
                away_team TEXT,
                match_time TEXT NOT NULL,
                status TEXT NOT NULL,
                home_score INTEGER DEFAULT NULL,
                away_score INTEGER DEFAULT NULL
            )
        """)

        # ۳. جدول پیش‌بینی‌ها
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                user_id BIGINT,
                match_id INTEGER,
                predicted_home INTEGER NOT NULL,
                predicted_away INTEGER NOT NULL,
                points_earned INTEGER DEFAULT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (user_id, match_id),
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
                FOREIGN KEY (match_id) REFERENCES matches (match_id) ON DELETE CASCADE
            )
        """)

        # ۴. جدول رده‌بندی گروه‌ها
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS standings (
                group_name TEXT,
                team_name TEXT,
                played_games INTEGER,
                won INTEGER,
                draw INTEGER,
                lost INTEGER,
                points INTEGER,
                goals_for INTEGER,
                goals_against INTEGER,
                goal_differential INTEGER,
                PRIMARY KEY (group_name, team_name)
            )
        """)

        conn.commit()
        cursor.close()
        conn.close()

    def create_standings_table(self):
        """ساخت مجزا و مستقل جدول گروه‌ها جهت تضمین پایداری در حین فرآیند همگام‌سازی"""
        self.init_db()

    def update_standings(self, standings_data):
        """بروزرسانی اطلاعات جدول گروه‌ها در دیتابیس ابری"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM standings")
        
        for row in standings_data:
            cursor.execute("""
                INSERT INTO standings 
                (group_name, team_name, played_games, won, draw, lost, points, goals_for, goals_against, goal_differential)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, row)
        conn.commit()
        cursor.close()
        conn.close()

    def get_standings(self):
        """واکشی جدول گروه‌ها به تفکیک نام گروه"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT group_name, team_name, played_games, won, draw, lost, points, goal_differential 
            FROM standings 
            ORDER BY group_name ASC, points DESC, goal_differential DESC
        """)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return rows

    def register_user(self, user_id, username, full_name):
        """ثبت نام یا بروزرسانی کاربر با سینتکس PostgreSQL (ON CONFLICT)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (user_id, username, full_name)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
                username = EXCLUDED.username,
                full_name = EXCLUDED.full_name
        """, (user_id, username, full_name))
        conn.commit()
        cursor.close()
        conn.close()

    def get_leaderboard(self):
        """دریافت لیست رده‌بندی کاربران با منطق اولویت‌بندی فوتبالی"""
        conn = self.get_connection()
        cursor = conn.cursor()
        query = """
            SELECT 
                u.username, 
                u.full_name, 
                u.total_score,
                SUM(CASE WHEN p.points_earned = 10 THEN 1 ELSE 0 END) as count_10,
                SUM(CASE WHEN p.points_earned = 7 THEN 1 ELSE 0 END) as count_7,
                SUM(CASE WHEN p.points_earned = 5 THEN 1 ELSE 0 END) as count_5
            FROM users u
            LEFT JOIN predictions p ON u.user_id = p.user_id
            GROUP BY u.user_id, u.username, u.full_name, u.total_score
            ORDER BY 
                u.total_score DESC, 
                count_10 DESC, 
                count_7 DESC, 
                count_5 DESC, 
                u.full_name ASC
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return rows

    def recalculate_user_total_score(self, user_id):
        """محاسبه مجدد مجموع امتیازات یک کاربر"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT SUM(points_earned) 
            FROM predictions 
            WHERE user_id = %s AND points_earned IS NOT NULL
        """, (user_id,))
        result = cursor.fetchone()
        total_score = result[0] if result[0] is not None else 0
        
        cursor.execute("""
            UPDATE users 
            SET total_score = %s 
            WHERE user_id = %s
        """, (total_score, user_id))
        
        conn.commit()
        cursor.close()
        conn.close()

    def save_or_update_match(self, match_id, home_team, away_team, match_time, status, home_score=None, away_score=None):
        """ذخیره مسابقه جدید یا بروزرسانی وضعیت و نتیجه آن"""
        conn = self.get_connection()
        cursor = conn.cursor()
        if isinstance(match_time, datetime):
            match_time_str = match_time.isoformat()
        else:
            match_time_str = str(match_time)

        cursor.execute("""
            INSERT INTO matches (match_id, home_team, away_team, match_time, status, home_score, away_score)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (match_id) DO UPDATE SET
                home_team = EXCLUDED.home_team,
                away_team = EXCLUDED.away_team,
                status = EXCLUDED.status,
                home_score = EXCLUDED.home_score,
                away_score = EXCLUDED.away_score
        """, (match_id, home_team, away_team, match_time_str, status, home_score, away_score))
        conn.commit()
        cursor.close()
        conn.close()

        if status == "FINISHED" and home_score is not None and away_score is not None:
            self.process_match_results(match_id, home_score, away_score)

    def get_match_by_id(self, match_id):
        """دریافت اطلاعات یک مسابقه خاص"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM matches WHERE match_id = %s", (match_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return row

    def calculate_points(self, p_home, p_away, r_home, r_away):
        if p_home == r_home and p_away == r_away:
            return 10
        p_diff = p_home - p_away
        r_diff = r_home - r_away
        p_outcome = 1 if p_diff > 0 else (-1 if p_diff < 0 else 0)
        r_outcome = 1 if r_diff > 0 else (-1 if r_diff < 0 else 0)
        if p_outcome == r_outcome and p_diff == r_diff:
            return 7
        if p_outcome == r_outcome:
            return 5
        return 2

    def process_match_results(self, match_id, real_home, real_away):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id, predicted_home, predicted_away 
            FROM predictions 
            WHERE match_id = %s AND points_earned IS NULL
        """, (match_id,))
        predictions = cursor.fetchall()
        cursor.close()
        conn.close()
        
        for user_id, p_home, p_away in predictions:
            points = self.calculate_points(p_home, p_away, real_home, real_away)
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE predictions 
                SET points_earned = %s 
                WHERE user_id = %s AND match_id = %s
            """, (points, user_id, match_id))
            conn.commit()
            cursor.close()
            conn.close()
            self.recalculate_user_total_score(user_id)

    def submit_prediction(self, user_id, match_id, predicted_home, predicted_away):
        conn = self.get_connection()
        cursor = conn.cursor()
        current_time_str = datetime.utcnow().isoformat()
        cursor.execute("""
            INSERT INTO predictions (user_id, match_id, predicted_home, predicted_away, created_at)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (user_id, match_id) DO UPDATE SET
                predicted_home = EXCLUDED.predicted_home,
                predicted_away = EXCLUDED.predicted_away,
                created_at = EXCLUDED.created_at,
                points_earned = NULL
        """, (user_id, match_id, predicted_home, predicted_away, current_time_str))
        conn.commit()
        cursor.close()
        conn.close()

    def get_user_prediction(self, user_id, match_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT predicted_home, predicted_away, points_earned FROM predictions WHERE user_id = %s AND match_id = %s", (user_id, match_id))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return row