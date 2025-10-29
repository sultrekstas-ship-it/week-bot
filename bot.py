import os
import re
from datetime import datetime, date, time
from io import BytesIO
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram.error import TelegramError
from telegram.constants import ChatMemberStatus
from PIL import Image, ImageDraw, ImageFont
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from database import Database

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен бота (получите у @BotFather)
try:
    from dotenv import load_dotenv
    load_dotenv()
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    if not BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN не найден в .env файле")
except ImportError:
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    if not BOT_TOKEN:
        raise ValueError("Установите python-dotenv или задайте переменную окружения TELEGRAM_BOT_TOKEN")

# Глобальные переменные
db = Database()
bot_application = None

# Канал для обязательной подписки
REQUIRED_CHANNEL = "@savinih_vitaliy"  # или ID канала в формате -100xxxxxxxxxx


async def check_subscription(user_id: int) -> bool:
    """
    Проверяет, подписан ли пользователь на обязательный канал.
    Возвращает True, если подписан, False в противном случае.
    """
    try:
        member = await bot_application.bot.get_chat_member(
            chat_id=REQUIRED_CHANNEL,
            user_id=user_id
        )
        
        # Проверяем статус пользователя в канале
        # Допустимые статусы: creator/owner, administrator, member
        if member.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.MEMBER]:
            return True
        else:
            return False
            
    except TelegramError as e:
        logger.error(f"Ошибка при проверке подписки для пользователя {user_id}: {e}")
        # В случае ошибки возвращаем False (безопасное поведение)
        return False


def calculate_weeks_and_days(birth_date: date) -> tuple:
    """
    Вычисляет количество прожитых полных недель и дней для таблицы 52x90.
    Для корректного отображения в таблице считаем: полных_лет * 52 + недель_в_текущем_году
    """
    today = date.today()
    
    # Общее количество дней с рождения
    total_days = (today - birth_date).days
    
    # Вычисляем полный возраст в годах
    age_years = today.year - birth_date.year
    
    # Проверяем, был ли уже день рождения в этом году
    had_birthday_this_year = (today.month, today.day) >= (birth_date.month, birth_date.day)
    
    if not had_birthday_this_year:
        age_years -= 1
    
    # Вычисляем дату последнего дня рождения
    if had_birthday_this_year:
        last_birthday = date(today.year, birth_date.month, birth_date.day)
    else:
        last_birthday = date(today.year - 1, birth_date.month, birth_date.day)
    
    # Количество дней с последнего дня рождения
    days_since_birthday = (today - last_birthday).days
    
    # Количество недель в текущем году жизни
    weeks_in_current_year = days_since_birthday // 7
    
    # Итоговое количество недель для таблицы 52x90
    weeks_for_table = age_years * 52 + weeks_in_current_year
    
    return weeks_for_table, total_days


def generate_life_calendar(weeks_lived: int, birth_date: date) -> BytesIO:
    """
    Генерирует красивое изображение календаря жизни в неделях.
    90 лет = 4680 недель (52 недели в год * 90 лет)
    """
    # Параметры изображения
    weeks_per_year = 52
    years_total = 90
    
    # Размеры (увеличены для лучшего качества)
    square_size = 14
    gap = 2
    margin_left = 100
    margin_top = 140
    margin_right = 60
    margin_bottom = 40
    
    # Размеры холста
    width = margin_left + (square_size + gap) * weeks_per_year + margin_right
    height = margin_top + (square_size + gap) * years_total + margin_bottom
    
    # Создаем изображение с белым фоном
    img = Image.new('RGB', (width, height), '#FFFFFF')
    draw = ImageDraw.Draw(img)
    
    # Загрузка шрифтов с приоритетом для кроссплатформенности
    try:
        # Windows
        font_title = ImageFont.truetype("arial.ttf", 38)
        font_medium = ImageFont.truetype("arial.ttf", 16)
        font_small = ImageFont.truetype("arial.ttf", 13)
    except:
        try:
            # Linux - DejaVu
            font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 38)
            font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 13)
        except:
            try:
                # Linux альтернатива - Liberation
                font_title = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 38)
                font_medium = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 16)
                font_small = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 13)
            except:
                # Fallback
                font_title = ImageFont.load_default()
                font_medium = ImageFont.load_default()
                font_small = ImageFont.load_default()
    
    # === ЗАГОЛОВОК ===
    title_black = "90 лет твоей жизни в "
    title_red = "неделях"
    
    # Вычисляем ширину текста для точного позиционирования
    try:
        bbox_black = draw.textbbox((0, 0), title_black, font=font_title)
        text_width_black = bbox_black[2] - bbox_black[0]
        bbox_red = draw.textbbox((0, 0), title_red, font=font_title)
        text_width_red = bbox_red[2] - bbox_red[0]
        total_width = text_width_black + text_width_red
    except:
        # Fallback для старых версий Pillow
        text_width_black = len(title_black) * 20
        text_width_red = len(title_red) * 20
        total_width = text_width_black + text_width_red
    
    # Центрируем заголовок
    title_y = 25
    title_x_black = (width - total_width) // 2
    title_x_red = title_x_black + text_width_black
    
    draw.text((title_x_black, title_y), title_black, fill='#1a1a1a', font=font_title)
    draw.text((title_x_red, title_y), title_red, fill='#DC143C', font=font_title)
    
    # === ПОДЗАГОЛОВОК "Номер недели" со стрелкой ===
    subtitle_y = 80
    draw.text((margin_left, subtitle_y), "Номер недели", fill='#333333', font=font_small)
    arrow_start_x = margin_left + 115
    arrow_end_x = arrow_start_x + 100
    arrow_y = subtitle_y + 7
    
    # Стрелка
    draw.line([(arrow_start_x, arrow_y), (arrow_end_x, arrow_y)], fill='#333333', width=2)
    draw.polygon([(arrow_end_x, arrow_y), (arrow_end_x - 7, arrow_y - 4), (arrow_end_x - 7, arrow_y + 4)], 
                 fill='#333333')
    
    # === НОМЕРА НЕДЕЛЬ ПО ГОРИЗОНТАЛИ ===
    numbers_y = 105
    for i in [1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50]:
        x = margin_left + i * (square_size + gap) - 8
        draw.text((x, numbers_y), str(i), fill='#666666', font=font_small)
    
    # === ПОДПИСЬ "Возраст" ПО ВЕРТИКАЛИ ===
    age_label_x = 20
    age_label_start_y = margin_top + 80
    age_text = "Возраст"
    
    for idx, char in enumerate(age_text):
        draw.text((age_label_x, age_label_start_y + idx * 22), char, fill='#333333', font=font_small)
    
    # Стрелка вниз
    arrow_x = age_label_x + 7
    arrow_start_y = age_label_start_y + len(age_text) * 22 + 10
    arrow_end_y = arrow_start_y + 40
    draw.line([(arrow_x, arrow_start_y), (arrow_x, arrow_end_y)], fill='#333333', width=2)
    draw.polygon([(arrow_x, arrow_end_y), (arrow_x - 4, arrow_end_y - 7), (arrow_x + 4, arrow_end_y - 7)], 
                 fill='#333333')
    
    # === НОМЕРА ЛЕТ ПО ВЕРТИКАЛИ ===
    for i in [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85]:
        y = margin_top + i * (square_size + gap) - 5
        draw.text((60, y), str(i), fill='#666666', font=font_small)
    
    # === РИСУЕМ КВАДРАТИКИ НЕДЕЛЬ ===
    week_counter = 0
    for year in range(years_total):
        for week in range(weeks_per_year):
            x = margin_left + week * (square_size + gap)
            y = margin_top + year * (square_size + gap)
            
            if week_counter < weeks_lived:
                # Прожитые недели - яркий красный
                fill_color = '#DC143C'
                outline_color = '#DC143C'
                draw.rectangle([x, y, x + square_size - 1, y + square_size - 1], 
                             fill=fill_color, outline=outline_color, width=1)
            else:
                # Будущие недели - светлые с серой обводкой
                fill_color = '#F5F5F5'
                outline_color = '#D0D0D0'
                draw.rectangle([x, y, x + square_size - 1, y + square_size - 1], 
                             fill=fill_color, outline=outline_color, width=1)
            
            week_counter += 1
    
    # === НОМЕР 90 СПРАВА ВНИЗУ ===
    draw.text((width - 45, height - 45), "90", fill='#666666', font=font_medium)
    
    # Сохраняем в BytesIO с высоким качеством
    bio = BytesIO()
    bio.name = 'life_calendar.png'
    img.save(bio, 'PNG', quality=95, optimize=True)
    bio.seek(0)
    
    return bio


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    # Проверяем подписку на канал
    is_subscribed = await check_subscription(update.effective_user.id)
    
    if not is_subscribed:
        # Создаем кнопки для подписки
        keyboard = [
            [InlineKeyboardButton("📢 Подписаться на канал", url="https://t.me/savinih_vitaliy")],
            [InlineKeyboardButton("✅ Проверить подписку", callback_data="check_sub")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "👋 Привет!\n\n"
            "❌ Для использования бота необходимо подписаться на наш канал!\n\n"
            "📢 Подпишитесь на канал и нажмите «Проверить подписку»:",
            reply_markup=reply_markup
        )
        return
    
    welcome_text = (
        "👋 Привет!\n\n"
        "🗓 Я покажу твою жизнь в неделях — каждая прожитая неделя это маленький квадратик на большой таблице.\n\n"
        "📅 Отправь мне дату своего рождения в формате:\n"
        "дд.мм.гггг или дд/мм/гггг\n\n"
        "📌 Например: 23.10.2004"
    )
    await update.message.reply_text(welcome_text)


async def check_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для ручной проверки обновлений (для тестирования)"""
    await update.message.reply_text("Запускаю проверку еженедельных обновлений...")
    await check_weekly_updates()
    await update.message.reply_text("Проверка завершена!")


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на inline кнопки"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "check_sub":
        # Проверяем подписку
        is_subscribed = await check_subscription(query.from_user.id)
        
        if is_subscribed:
            await query.edit_message_text(
                "✅ Отлично! Вы подписаны на канал.\n\n"
                "Теперь отправьте мне дату своего рождения в формате дд.мм.гггг или дд/мм/гггг\n"
                "Например: 23.10.2004"
            )
        else:
            keyboard = [
                [InlineKeyboardButton("📢 Подписаться на канал", url="https://t.me/savinih_vitaliy")],
                [InlineKeyboardButton("✅ Проверить подписку", callback_data="check_sub")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "❌ Вы еще не подписаны на канал!\n\n"
                "Пожалуйста, подпишитесь и нажмите «Проверить подписку» снова:",
                reply_markup=reply_markup
            )


async def handle_birthdate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик сообщения с датой рождения"""
    user_input = update.message.text.strip()
    
    # Проверяем подписку на канал
    is_subscribed = await check_subscription(update.effective_user.id)
    
    if not is_subscribed:
        # Создаем кнопки для подписки
        keyboard = [
            [InlineKeyboardButton("📢 Подписаться на канал", url="https://t.me/savinih_vitaliy")],
            [InlineKeyboardButton("✅ Проверить подписку", callback_data="check_sub")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "❌ Для использования бота необходимо подписаться на наш канал!\n\n"
            "📢 Подпишитесь на канал и нажмите «Проверить подписку»:",
            reply_markup=reply_markup
        )
        return
    
    # Проверяем формат даты
    date_pattern = r'(\d{2})[\./](\d{2})[\./](\d{4})'
    match = re.match(date_pattern, user_input)
    
    if not match:
        await update.message.reply_text(
            "Неверный формат даты. Пожалуйста, используйте формат дд.мм.гггг или дд/мм/гггг\n"
            "Например: 23.10.2004"
        )
        return
    
    try:
        day, month, year = match.groups()
        birth_date = date(int(year), int(month), int(day))
        
        # Проверяем, что дата не в будущем
        if birth_date > date.today():
            await update.message.reply_text("Дата рождения не может быть в будущем!")
            return
        
        # Проверяем разумность даты (не более 120 лет)
        age_in_years = (date.today() - birth_date).days / 365.25
        if age_in_years > 120:
            await update.message.reply_text("Пожалуйста, проверьте правильность даты рождения.")
            return
        
    except ValueError:
        await update.message.reply_text(
            "Некорректная дата. Проверьте правильность введенных данных."
        )
        return
    
    # Вычисляем недели и дни
    weeks, days = calculate_weeks_and_days(birth_date)
    
    # Сохраняем пользователя в базу данных
    try:
        user = update.effective_user
        db.save_user(
            user_id=user.id,
            birth_date=birth_date,
            username=user.username,
            first_name=user.first_name
        )
        logger.info(f"Пользователь {user.id} сохранен в базе данных")
    except Exception as e:
        logger.error(f"Ошибка при сохранении пользователя: {e}")
    
    # Отправляем текстовую информацию
    response_text = (
        f"📊 Вы прожили уже {weeks} недель или {days} дней!\n\n"
        f"✨ Готово! Вот таблица вашей жизни.\n\n"
        f"🔔 Теперь я буду присылать вам обновленную таблицу каждую неделю!"
    )
    
    await update.message.reply_text(response_text)
    
    # Генерируем и отправляем изображение
    try:
        await update.message.reply_text("Генерирую изображение...")
        image_bio = generate_life_calendar(weeks, birth_date)
        await update.message.reply_photo(photo=image_bio)
        
        # Обновляем номер последней отправленной недели
        db.update_last_week_sent(update.effective_user.id, weeks)
        
        logger.info(f"Успешно отправлено изображение для пользователя {update.effective_user.id}")
    except Exception as e:
        logger.error(f"Ошибка при генерации изображения: {e}")
        await update.message.reply_text("Извините, произошла ошибка при генерации изображения.")


async def send_weekly_update(user_id: int, birth_date: date, current_week: int):
    """Отправляет еженедельное обновление пользователю"""
    try:
        weeks, days = calculate_weeks_and_days(birth_date)
        
        # Генерируем сообщение
        message_text = (
            f"🎉 Поздравляем! Вы прожили еще одну неделю!\n\n"
            f"📊 Неделя #{current_week}\n"
            f"📅 Всего прожито: {weeks} недель или {days} дней\n\n"
            f"Вот обновленная таблица вашей жизни:"
        )
        
        # Отправляем сообщение
        await bot_application.bot.send_message(
            chat_id=user_id,
            text=message_text
        )
        
        # Генерируем и отправляем изображение
        image_bio = generate_life_calendar(weeks, birth_date)
        await bot_application.bot.send_photo(
            chat_id=user_id,
            photo=image_bio
        )
        
        # Обновляем номер последней отправленной недели
        db.update_last_week_sent(user_id, current_week)
        
        logger.info(f"Отправлено еженедельное обновление пользователю {user_id}, неделя {current_week}")
        
    except TelegramError as e:
        logger.error(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")
    except Exception as e:
        logger.error(f"Неожиданная ошибка при отправке обновления пользователю {user_id}: {e}")


async def check_weekly_updates():
    """Проверяет и отправляет еженедельные обновления всем пользователям"""
    logger.info("Запуск проверки еженедельных обновлений...")
    
    try:
        users_to_update = db.get_users_for_weekly_update()
        
        if users_to_update:
            logger.info(f"Найдено {len(users_to_update)} пользователей для обновления")
            
            for user in users_to_update:
                await send_weekly_update(
                    user_id=user['user_id'],
                    birth_date=user['birth_date_obj'],
                    current_week=user['current_week']
                )
        else:
            logger.info("Нет пользователей для обновления")
            
    except Exception as e:
        logger.error(f"Ошибка при проверке обновлений: {e}")


def main():
    """Запуск бота"""
    global bot_application
    
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    bot_application = application
    
    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("check_now", check_now))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_birthdate))
    
    # Настраиваем scheduler для ежедневной проверки в 10:00
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        check_weekly_updates,
        trigger=CronTrigger(hour=10, minute=0),  # Каждый день в 10:00
        id='weekly_check',
        name='Проверка еженедельных обновлений',
        replace_existing=True
    )
    scheduler.start()
    logger.info("Scheduler запущен. Проверка будет выполняться каждый день в 10:00")
    
    # Запускаем бота
    logger.info("Бот запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()

