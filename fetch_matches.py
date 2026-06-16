import os
import requests
from datetime import datetime
from dotenv import load_dotenv
from database import DatabaseManager

# بارگذاری متغیرهای محیطی از فایل .env
load_dotenv(".env")

class FootballAPIManager:
    def __init__(self, db_manager):
        self.db = db_manager
        self.api_key = os.getenv("FOOTBALL_API_KEY")
        if not self.api_key:
            raise ValueError("خطا: FOOTBALL_API_KEY در فایل .env تعریف نشده است!")
        
        self.headers = {
            "X-Auth-Token": self.api_key
        }
        # آدرس‌های API مسابقات و جدول رده‌بندی جام جهانی (WC)
        self.matches_url = "https://api.football-data.org/v4/competitions/WC/matches"
        self.standings_url = "https://api.football-data.org/v4/competitions/WC/standings"

    def sync_matches_to_db(self):
        """دریافت مسابقات از API و ذخیره/بروزرسانی مستقیم آن‌ها در دیتابیس ابری"""
        try:
            response = requests.get(self.matches_url, headers=self.headers)
            
            if response.status_code == 200:
                data = response.json()
                matches_list = data.get("matches", [])
                
                if not matches_list:
                    print("هیچ مسابقه‌ای برای این تورنمنت یافت نشد.")
                    return []
                
                parsed_matches = []
                for match in matches_list:
                    match_id = match.get("id")
                    
                    home_team_obj = match.get("homeTeam")
                    home_team = home_team_obj.get("name") if home_team_obj else "نامشخص"
                    if not home_team:
                        home_team = "نامشخص"
                        
                    away_team_obj = match.get("awayTeam")
                    away_team = away_team_obj.get("name") if away_team_obj else "نامشخص"
                    if not away_team:
                        away_team = "نامشخص"
                        
                    status = match.get("status", "TIMED")
                    
                    utc_date_str = match.get("utcDate")
                    if not utc_date_str:
                        continue
                    
                    utc_date_str = utc_date_str.replace("Z", "")
                    utc_time = datetime.fromisoformat(utc_date_str)
                    
                    home_score = match.get("score", {}).get("fullTime", {}).get("home")
                    away_score = match.get("score", {}).get("fullTime", {}).get("away")
                    
                    # ذخیره یا بروزرسانی در دیتابیس اصلی
                    self.db.save_or_update_match(
                        match_id=match_id,
                        home_team=home_team,
                        away_team=away_team,
                        match_time=utc_time,
                        status=status,
                        home_score=home_score,
                        away_score=away_score
                    )
                    
                    match_info = {
                        "match_id": match_id,
                        "home_team": home_team,
                        "away_team": away_team,
                        "status": status,
                        "utc_time": utc_time,
                        "home_score": home_score,
                        "away_score": away_score
                    }
                    parsed_matches.append(match_info)
                
                print(f"همگام‌سازی مسابقات موفقیت‌آمیز بود! {len(parsed_matches)} مسابقه بروزرسانی شد.")
                return parsed_matches
            else:
                print(f"خطا در دریافت مسابقات. کد وضعیت: {response.status_code}")
                return []
        except Exception as e:
            print(f"یک خطای غیرمنتظره در همگام‌سازی مسابقات رخ داد: {e}")
            return []

    def sync_standings_to_db(self):
        """دریافت جدول رده‌بندی گروه‌های واقعی جام جهانی از API و ذخیره در دیتابیس ابری"""
        try:
            response = requests.get(self.standings_url, headers=self.headers)
            if response.status_code == 200:
                data = response.json()
                standings_list = data.get("standings", [])
                
                extracted_rows = []
                for group_data in standings_list:
                    group_name = group_data.get("group")
                    table_rows = group_data.get("table", [])
                    
                    for row in table_rows:
                        team_name = row.get("team", {}).get("name")
                        played = row.get("playedGames", 0)
                        won = row.get("won", 0)
                        draw = row.get("draw", 0)
                        lost = row.get("lost", 0)
                        points = row.get("points", 0)
                        goals_for = row.get("goalsFor", 0)
                        goals_against = row.get("goalsAgainst", 0)
                        goal_diff = row.get("goalDifference", 0)
                        
                        extracted_rows.append((
                            group_name, team_name, played, won, draw, lost, 
                            points, goals_for, goals_against, goal_diff
                        ))
                
                # ایجاد جدول و ثبت اطلاعات در دیتابیس
                self.db.create_standings_table()
                self.db.update_standings(extracted_rows)
                print(f"همگام‌سازی جدول گروه‌ها موفقیت‌آمیز بود! {len(extracted_rows)} تیم بروزرسانی شدند.")
                return True
            else:
                print(f"خطا در دریافت جدول گروه‌ها. کد وضعیت: {response.status_code}")
                return False
        except Exception as e:
            print(f"یک خطای غیرمنتظره در همگام‌سازی جدول گروه‌ها رخ داد: {e}")
            return False

# اصلاح بخش تست دستی برای خواندن خودکار DATABASE_URL از متغیرهای محیطی ابری
if __name__ == "__main__":
    db_url_from_env = os.getenv("DATABASE_URL")
    if not db_url_from_env:
        print("خطا: DATABASE_URL در فایل .env یافت نشد! لطفاً لینک اتصال رندر را قرار دهید.")
    else:
        try:
            db_manager = DatabaseManager(db_url=db_url_from_env)
            api_manager = FootballAPIManager(db_manager)
            api_manager.sync_matches_to_db()
            api_manager.sync_standings_to_db()
        except Exception as e:
            print(f"خطا در راه‌اندازی دیتابیس ابری: {e}")