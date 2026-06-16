import os
import asyncio
import logging
from datetime import datetime, date
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from dotenv import load_dotenv
from database import DatabaseManager
from fetch_matches import FootballAPIManager

# بارگذاری متغیرهای محیطی
load_dotenv(".env")

# فعال‌سازی سیستم لاگین
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("خطا: TELEGRAM_BOT_TOKEN در فایل .env تعریف نشده است!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# اتصال به دیتابیس اصلی و مدیریت API
db = DatabaseManager("world_cup.db")
api_manager = FootballAPIManager(db)

# دیکشنری جامع ترجمه نام تیم‌های جام جهانی به فارسی
TEAM_TRANSLATIONS = {
    "Mexico": "مکزیک", "South Africa": "آفریقای جنوبی", "South Korea": "کره جنوبی",
    "Czechia": "جمهوری چک", "Argentina": "آرژانتین", "Brazil": "برزیل",
    "Germany": "آلمان", "France": "فرانسه", "Spain": "اسپانیا",
    "England": "انگلستان", "Italy": "ایتالیا", "Portugal": "پرتغال",
    "Netherlands": "هلند", "Belgium": "بلژیک", "Croatia": "کرواسی",
    "Uruguay": "اروگوئه", "Colombia": "کلمبیا", "Senegal": "سنگال",
    "Morocco": "مراکش", "Japan": "ژاپن", "Iran": "ایران",
    "USA": "آمریکا", "United States": "آمریکا", "Canada": "کانادا",
    "Australia": "استرالیا", "Saudi Arabia": "عربستان سعودی", "Qatar": "قطر",
    "Ecuador": "اکوادور", "Wales": "ولز", "Poland": "لهستان",
    "Tunisia": "تونس", "Denmark": "دانمارک", "Costa Rica": "کاستاریکا",
    "Switzerland": "سوئیس", "Cameroon": "کامرون", "Ghana": "غنا", "Serbia": "صربستان",
    "Bosnia-Herzegovina": "بوسنی و هرزگوین", "Haiti": "هاییتی", "Scotland": "اسکاتلند",
    "Paraguay": "پاراگوئه", "Turkey": "ترکیه", "Curaçao": "کوراسائو",
    "Ivory Coast": "ساحل عاج", "Sweden": "سوئد", "Egypt": "مصر",
    "New Zealand": "نیوزیلند", "Cape Verde Islands": "کپ ورد", "Iraq": "عراق",
    "Norway": "نروژ", "Algeria": "الجزایر", "Austria": "اتریش",
    "Jordan": "اردن", "Congo DR": "جمهوری دموکراتیک کنگو", "Uzbekistan": "ازبکستان",
    "Panama": "پاناما"
}

def get_fa_team(team_name):
    """تبدیل نام انگلیسی تیم به فارسی روان"""
    if not team_name:
        return "نامشخص"
    cleaned_name = team_name.strip()
    return TEAM_TRANSLATIONS.get(cleaned_name, cleaned_name)

def get_main_menu_keyboard():
    """ساخت کیبورد دکمه‌های دائمی پنج‌گانه پایین صفحه"""
    builder = ReplyKeyboardBuilder()
    builder.button(text="🔮 پیش‌بینی مسابقات امروز")
    builder.button(text="📊 پیش‌بینی‌های من")
    builder.button(text="⚽️ نتایج بازی‌ها")
    builder.button(text="🏆 رده‌بندی شرکت‌کنندگان")
    builder.button(text="📊 جدول گروه‌های جام جهانی")
    builder.adjust(2, 2, 1)
    return builder.as_markup(resize_keyboard=True, persistent=True)

class RegistrationStates(StatesGroup):
    waiting_for_real_name = State()

class PredictionStates(StatesGroup):
    waiting_for_home_score = State()
    waiting_for_away_score = State()

@dp.message(CommandStart())
async def command_start_handler(message: types.Message, state: FSMContext):
    """هندل کردن دستور /start و بررسی وضعیت ثبت‌نام کاربر"""
    user_id = message.from_user.id
    
    if message.chat.type in ["group", "supergroup"]:
        await message.reply(
            f"🏅 **سلام عزیز به چالش بزرگ پیش‌بینی خوش آمدی!**\n"
            f"───────────────────────\n"
            f"برای ثبت‌نام، ثبت پیش‌بینی و مشاهده جدول امتیازات لطفاً به پی‌وی ربات مراجعه کنید:\n"
            f"👉 @{(await bot.get_me()).username}"
        )
        return

    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT full_name FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if not row or row[0] == "نامشخص" or row[0] is None:
        welcome_text = (
            f"👋 **سلام به ربات پیش‌بینی مسابقات جام جهانی خوش آمدی!**\n\n"
            f"⚠️ برای شرکت در مسابقات و قرار گرفتن در جدول رده‌بندی گروه، ابتدا باید نام و نام خانوادگی خود را وارد کنید.\n\n"
            f"👇 **لطفاً نام و نام خانوادگی خود را به «فارسی» ارسال کنید:**"
        )
        await state.clear()
        await message.answer(welcome_text, reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(RegistrationStates.waiting_for_real_name)
    else:
        welcome_text = (
            f"🏁 **سلام {row[0]} عزیز، خوش آمدی!**\n"
            f"───────────────────────\n"
            f"ثبت‌نام شما قبلاً تکمیل شده است. از دکمه‌های زیر صفحه برای مدیریت پیش‌بینی‌ها استفاده کنید."
        )
        await message.answer(welcome_text, reply_markup=get_main_menu_keyboard())

@dp.message(RegistrationStates.waiting_for_real_name)
async def process_real_name_handler(message: types.Message, state: FSMContext):
    """دریافت نام واقعی فارسی و فعال‌سازی منوی اصلی"""
    real_name = message.text.strip()
    user_id = message.from_user.id
    username = message.from_user.username or "بدون_یوزرنیم"

    if len(real_name) < 3:
        await message.answer("❌ نام وارد شده خیلی کوتاه است. لطفاً نام و نام خانوادگی کامل خود را وارد کنید:")
        return

    db.register_user(user_id=user_id, username=username, full_name=real_name)

    success_text = (
        f"✅ **ثبت‌نام شما با موفقیت تکمیل شد!**\n\n"
        f"👤 نام ثبت شده: **{real_name}**\n"
        f"───────────────────────\n"
        f"حالا منوی اصلی ربات برای شما فعال گردید. می‌توانید از دکمه‌های زیر استفاده کنید:"
    )
    await message.answer(success_text, reply_markup=get_main_menu_keyboard())
    await state.clear()

# ------------------ مدیریت دکمه‌های منوی اصلی ------------------

@dp.message(F.text == "🔮 پیش‌بینی مسابقات امروز")
async def predict_menu_handler(message: types.Message):
    await send_today_matches(message)

@dp.message(F.text == "📊 پیش‌بینی‌های من")
async def user_predictions_handler(message: types.Message):
    user_id = message.from_user.id
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.match_id, m.home_team, m.away_team, m.match_time, p.predicted_home, p.predicted_away, p.points_earned
        FROM predictions p
        JOIN matches m ON p.match_id = m.match_id
        WHERE p.user_id = ?
        ORDER BY m.match_time ASC
    """, (user_id,))
    user_preds = cursor.fetchall()
    conn.close()

    if not user_preds:
        await message.answer("💬 **شما هنوز هیچ پیش‌بینی در سیستم ثبت نکرده‌اید!**")
        return

    await message.answer("📊 **لیست پیش‌بینی‌های شما تا این لحظه:**\n───────────────────────")
    for match_id, home_team, away_team, match_time_str, p_home, p_away, points in user_preds:
        match_time = datetime.fromisoformat(match_time_str)
        current_time = datetime.utcnow()
        fa_home = get_fa_team(home_team)
        fa_away = get_fa_team(away_team)
        
        score_status = f"✅ امتیاز کسب شده: **{points} امتیاز**" if points is not None else "⏳ بازی هنوز تمام/محاسبه نشده"
        builder = InlineKeyboardBuilder()
        if current_time < match_time:
            builder.button(text=f"🔄 ویرایش پیش‌بینی", callback_data=f"pred_{match_id}")
            builder.adjust(1)
            reply_markup = builder.as_markup()
        else:
            reply_markup = None

        pred_text = f"🏟 **{fa_home} × {fa_away}**\n🎯 پیش‌بینی شما: **{fa_home} {p_home} - {p_away} {fa_away}**\n{score_status}\n───────────────────────"
        await message.answer(pred_text, reply_markup=reply_markup)

@dp.message(F.text == "⚽️ نتایج بازی‌ها")
async def match_results_handler(message: types.Message):
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT home_team, away_team, home_score, away_score, status 
        FROM matches 
        WHERE status IN ('FINISHED', 'IN_PLAY')
        ORDER BY match_time DESC LIMIT 10
    """)
    results = cursor.fetchall()
    conn.close()

    if not results:
        await message.answer("⚽️ **هنوز مسابقه‌ای شروع نشده یا نتیجه‌ای ثبت نگردیده است.**")
        return

    text = "⚽️ **نتایج آخرین مسابقات برگزار شده:**\n───────────────────────\n"
    for home_team, away_team, h_score, a_score, status in results:
        status_tag = "🔴 در حال برگزاری" if status == "IN_PLAY" else "🏁 پایان یافته"
        text += f"🏟 **{get_fa_team(home_team)}  {h_score} - {a_score}  {get_fa_team(away_team)}**\nوضعیت: {status_tag}\n───────────────────────\n"
    await message.answer(text)

@dp.message(F.text == "🏆 رده‌بندی شرکت‌کنندگان")
async def leaderboard_handler(message: types.Message):
    """نمایش زنده جدول رده‌بندی با اولویت‌بندی بر اساس تعداد پیش‌بینی‌های درشت به جای الفبا"""
    leaderboard_data = db.get_leaderboard()
    if not leaderboard_data:
        await message.answer("🏆 **جدول رده‌بندی شرکت‌کنندگان هنوز خالی است.**")
        return

    text = "🏆 **جدول زنده رده‌بندی شرکت‌کنندگان:**\n───────────────────────\n"
    for index, row in enumerate(leaderboard_data, start=1):
        full_name = row[1]
        total_score = row[2]
        count_10 = row[3] or 0
        
        medal = "🥇" if index == 1 else ("🥈" if index == 2 else ("🥉" if index == 3 else f"{index}#"))
        text += f"{medal} {full_name} ─── 🟡 **{total_score} امتیاز** ({count_10} تا ۱۰امتیازی)\n"
    await message.answer(text)

@dp.message(F.text == "📊 جدول گروه‌های جام جهانی")
async def world_cup_standings_handler(message: types.Message):
    """نمایش لیست گروه‌ها به صورت دکمه‌های شیشه‌ای تفکیک‌شده جهت جلوگیری از خطای طولانی بودن پیام تلگرام"""
    try:
        standings = db.get_standings()
    except Exception:
        db.create_standings_table()
        standings = []

    if not standings:
        await message.answer("📊 **اطلاعات جدول گروه‌ها هنوز بارگذاری نشده است.**")
        return

    # استخراج دزدکی نام گروه‌های یکتا موجود در دیتابیس
    unique_groups = sorted(list(set([row[0] for row in standings])))

    builder = InlineKeyboardBuilder()
    for g_name in unique_groups:
        friendly_name = g_name.replace("GROUP_", "گروه ")
        # ارسال کالبک اختصاصی برای هر گروه
        builder.button(text=f"🏆 {friendly_name}", callback_data=f"viewgroup_{g_name}")
    
    builder.adjust(3) # چینش دکمه‌ها در ردیف‌های ۳ تایی شیک

    intro_text = (
        f"📊 **جدول رده‌بندی گروه‌های جام جهانی واقعی:**\n"
        f"───────────────────────\n"
        f"جام جهانی ۲۰۲۶ شامل ۱۲ گروه ۴ تیمی است.\n"
        f"لطفاً جهت مشاهده وضعیت و جدول زنده هر گروه، روی دکمه مربوط به آن کلیک کنید:"
    )
    await message.answer(intro_text, reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("viewgroup_"))
async def group_details_callback(callback_query: types.CallbackQuery):
    """نمایش زنده دیزاین گرافیکی و مدرن تفکیک‌شده برای یک گروه خاص به محض کلیک"""
    await callback_query.answer()
    group_name = callback_query.data.split("_")[1]
    
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT team_name, played_games, won, draw, lost, points, goal_differential 
        FROM standings 
        WHERE group_name = ?
        ORDER BY points DESC, goal_differential DESC
    """, (group_name,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await callback_query.message.answer("اطلاعات این گروه یافت نشد.")
        return

    friendly_group_name = group_name.replace("GROUP_", "گروه ")
    text = f"🏆 ✨ **جدول زنده {friendly_group_name}** ✨\n"
    text += "───────────────────────\n"

    for index, (team_name, played, won, draw, lost, points, diff) in enumerate(rows, start=1):
        fa_team = get_fa_team(team_name)
        
        if index == 1:
            rank_emoji = "🟢 ۱."
        elif index == 2:
            rank_emoji = "🔵 ۲."
        else:
            rank_emoji = f"⚪️ {index}."

        text += (
            f"{rank_emoji} **{fa_team}**\n"
            f"◽️ بازی: {played}  🔹 برد: {won}  🔸 تفاضل: {diff:+}  🔥 **امتیاز: {points}**\n"
            f"┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈\n"
        )

    # دکمه بازگشت برای راحتی کاربر
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 بازگشت به لیست گروه‌ها", callback_data="back_to_groups")
    
    await callback_query.message.answer(text, reply_markup=builder.as_markup())

@dp.callback_query(F.data == "back_to_groups")
async def back_to_groups_callback(callback_query: types.CallbackQuery):
    """بازگرداندن کاربر به منوی انتخاب گروه‌ها با حذف پیام فعلی"""
    await callback_query.answer()
    await callback_query.message.delete()
    # شبیه‌سازی کلیک مجدد روی دکمه گروه‌ها
    await world_cup_standings_handler(callback_query.message)

# ------------------ کدهای بخش فرآیند پیش‌بینی عددی ------------------

@dp.message(Command("testmatches"))
async def test_matches_command(message: types.Message):
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT match_id, home_team, away_team, match_time, status FROM matches WHERE status = 'TIMED' ORDER BY match_time ASC LIMIT 3")
    test_matches = cursor.fetchall()
    conn.close()

    if not test_matches:
        await message.answer("✨ **هیچ مسابقه برگزار نشده‌ای در دیتابیس نیست.**")
        return

    await message.answer("🛠 **حالت تست سیستم (بدون فیلتر تاریخ امروز):**\n⚽️ **مسابقات شبیه‌سازی شده:**\n───────────────────────")
    for match_id, home_team, away_team, match_time_str, status in test_matches:
        fa_home = get_fa_team(home_team)
        fa_away = get_fa_team(away_team)
        builder = InlineKeyboardBuilder()
        builder.button(text=f"🎲 ثبت پیش‌بینی | {fa_home} × {fa_away}", callback_data=f"pred_{match_id}")
        builder.adjust(1)
        await message.answer(f"🏟 **{fa_home}** [ 🆚 ]  **{fa_away}**\n⏰ شناسه تست: {match_id}\n───────────────────────", reply_markup=builder.as_markup())

async def send_today_matches(message: types.Message):
    conn = db.get_connection()
    cursor = conn.cursor()
    today_str = date.today().isoformat()
    cursor.execute("SELECT match_id, home_team, away_team, match_time, status FROM matches WHERE match_time LIKE ? ORDER BY match_time ASC", (f"{today_str}%",))
    today_matches = cursor.fetchall()
    conn.close()

    if not today_matches:
        await message.answer("✨ **برای امروز مسابقه‌ای در دیتابیس ثبت نشده است.**")
        return

    await message.answer("📅 📅 📅 📅 📅 📅 📅 📅 📅\n⚽️ **مسابقات روز جاری:**\n───────────────────────\nجهت ثبت یا ویرایش پیش‌بینی خود روی بازی مورد نظر کلیک کنید:")
    for match_id, home_team, away_team, match_time_str, status in today_matches:
        match_time = datetime.fromisoformat(match_time_str)
        current_time = datetime.utcnow()
        fa_home = get_fa_team(home_team)
        fa_away = get_fa_team(away_team)
        builder = InlineKeyboardBuilder()
        
        if current_time < match_time:
            builder.button(text=f"🎲 ثبت پیش‌بینی | {fa_home} × {fa_away}", callback_data=f"pred_{match_id}")
        else:
            builder.button(text=f"🔒 قفل شده (بازی شروع شده)", callback_data="match_locked")
            
        builder.adjust(1)
        await message.answer(f"🏟 **{fa_home}** [ 🆚 ]  **{fa_away}**\n⏰ ساعت: {match_time.strftime('%H:%M')} (UTC)\n───────────────────────", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("pred_"))
async def match_click_handler(callback_query: types.CallbackQuery, state: FSMContext):
    match_id = int(callback_query.data.split("_")[1])
    match_data = db.get_match_by_id(match_id)
    if not match_data: return

    fa_home = get_fa_team(match_data[1])
    fa_away = get_fa_team(match_data[2])

    await callback_query.answer()
    await callback_query.message.answer(f"🏁 **پیش‌بینی مسابقه:** {fa_home} × {fa_away}\n\nتعداد گل‌های تیم **{fa_home}** (میزبان) را انتخاب کنید:")
    home_kb = create_numeric_keyboard(match_id, is_home=True)
    await callback_query.message.answer("🔢 انتخاب تعداد گل:", reply_markup=home_kb)
    await state.update_data(current_match_id=match_id, fa_home=fa_home, fa_away=fa_away)
    await state.set_state(PredictionStates.waiting_for_home_score)

def create_numeric_keyboard(match_id, is_home):
    builder = InlineKeyboardBuilder()
    prefix = "score_h" if is_home else "score_a"
    for i in range(10): builder.button(text=str(i), callback_data=f"{prefix}_{match_id}_{i}")
    builder.adjust(5)
    return builder.as_markup()

@dp.callback_query(PredictionStates.waiting_for_home_score, F.data.startswith("score_h_"))
async def home_score_callback(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    parts = callback_query.data.split("_")
    match_id, selected_home_score = int(parts[2]), int(parts[3])
    user_data = await state.get_data()
    
    await state.update_data(predicted_home=selected_home_score)
    await callback_query.message.delete()
    
    await callback_query.message.answer(f"🔹 تعداد گل **{user_data.get('fa_home')}**: {selected_home_score}\n\nحالا تعداد گل‌های تیم **{user_data.get('fa_away')}** (میهمان) را انتخاب کنید:")
    away_kb = create_numeric_keyboard(match_id, is_home=False)
    await callback_query.message.answer("🔢 انتخاب تعداد گل:", reply_markup=away_kb)
    await state.set_state(PredictionStates.waiting_for_away_score)

@dp.callback_query(PredictionStates.waiting_for_away_score, F.data.startswith("score_a_"))
async def away_score_callback(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    parts = callback_query.data.split("_")
    selected_away_score = int(parts[3])
    user_data = await state.get_data()

    await callback_query.message.delete()
    db.submit_prediction(user_id=callback_query.from_user.id, match_id=user_data.get("current_match_id"), predicted_home=user_data.get("predicted_home"), predicted_away=selected_away_score)

    success_text = f"✅ **پیش‌بینی شما با موفقیت ثبت شد!**\n───────────────────────\n🏟 **مسابقه:** {user_data.get('fa_home')} × {user_data.get('fa_away')}\n📊 **نتیجه:** {user_data.get('fa_home')} {user_data.get('predicted_home')} - {selected_away_score} {user_data.get('fa_away')}\n───────────────────────"
    await callback_query.message.answer(success_text)
    await state.clear()

@dp.callback_query(F.data == "match_locked")
async def match_locked_handler(callback_query: types.CallbackQuery):
    await callback_query.answer("این مسابقه شروع شده و امکان ثبت یا ویرایش پیش‌بینی وجود ندارد!", show_alert=True)

# ------------------ موتور همگام‌سازی خودکار در پس‌زمینه ------------------

async def auto_sync_scheduler():
    while True:
        logging.info("⏳ در حال شروع همگام‌سازی خودکار با API فوتبال...")
        try:
            api_manager.sync_matches_to_db()
            api_manager.sync_standings_to_db()
            logging.info("✅ دیتابیس و امتیازات با موفقیت همگام‌سازی شدند.")
        except Exception as e:
            logging.error(f"❌ خطا در چرخه همگام‌سازی خودکار پس‌زمینه: {e}")
        await asyncio.sleep(900)

async def main():
    print("ربات مدرن مسابقات با موفقیت روشن شد...")
    asyncio.create_task(auto_sync_scheduler())
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())