import sqlite3
from datetime import date, datetime
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path: str = "lifeweeks.db"):
        self.db_path = db_path
        self.init_db()
    
    def get_connection(self):
        """Создает подключение к базе данных"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self):
        """Инициализирует базу данных"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Таблица пользователей
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    birth_date TEXT NOT NULL,
                    last_week_sent INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            conn.commit()
            logger.info("База данных инициализирована")
    
    def save_user(self, user_id: int, birth_date: date, username: str = None, first_name: str = None):
        """Сохраняет или обновляет данные пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            now = datetime.now().isoformat()
            birth_date_str = birth_date.isoformat()
            
            # Проверяем, существует ли пользователь
            cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            exists = cursor.fetchone()
            
            if exists:
                # Обновляем существующего пользователя
                cursor.execute("""
                    UPDATE users 
                    SET birth_date = ?, username = ?, first_name = ?, updated_at = ?, last_week_sent = 0
                    WHERE user_id = ?
                """, (birth_date_str, username, first_name, now, user_id))
                logger.info(f"Обновлены данные пользователя {user_id}")
            else:
                # Добавляем нового пользователя
                cursor.execute("""
                    INSERT INTO users (user_id, username, first_name, birth_date, created_at, updated_at, last_week_sent)
                    VALUES (?, ?, ?, ?, ?, ?, 0)
                """, (user_id, username, first_name, birth_date_str, now, now))
                logger.info(f"Добавлен новый пользователь {user_id}")
            
            conn.commit()
    
    def get_user(self, user_id: int) -> Optional[dict]:
        """Получает данные пользователя по ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            return None
    
    def get_all_users(self) -> List[dict]:
        """Получает всех пользователей"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def update_last_week_sent(self, user_id: int, week_number: int):
        """Обновляет номер последней отправленной недели"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users 
                SET last_week_sent = ?, updated_at = ?
                WHERE user_id = ?
            """, (week_number, datetime.now().isoformat(), user_id))
            conn.commit()
    
    def get_users_for_weekly_update(self) -> List[dict]:
        """
        Получает пользователей, которым нужно отправить обновление.
        Возвращает пользователей, у которых текущая неделя больше last_week_sent.
        """
        from datetime import date as date_module
        
        users_to_update = []
        all_users = self.get_all_users()
        
        for user in all_users:
            try:
                birth_date = date_module.fromisoformat(user['birth_date'])
                
                # Импортируем функцию расчета недель из bot.py
                from bot import calculate_weeks_and_days
                current_week, _ = calculate_weeks_and_days(birth_date)
                
                # Если текущая неделя больше последней отправленной
                if current_week > user['last_week_sent']:
                    user['current_week'] = current_week
                    user['birth_date_obj'] = birth_date
                    users_to_update.append(user)
                    
            except Exception as e:
                logger.error(f"Ошибка при обработке пользователя {user['user_id']}: {e}")
        
        return users_to_update


