"""
Утилита для просмотра пользователей в базе данных
"""
from database import Database
from datetime import date
from bot import calculate_weeks_and_days

def main():
    db = Database()
    users = db.get_all_users()
    
    if not users:
        print("База данных пуста. Пользователи еще не зарегистрированы.")
        return
    
    print(f"\n{'='*80}")
    print(f"Всего пользователей в базе: {len(users)}")
    print(f"{'='*80}\n")
    
    for idx, user in enumerate(users, 1):
        print(f"Пользователь #{idx}")
        print(f"  ID: {user['user_id']}")
        print(f"  Username: @{user['username']}" if user['username'] else "  Username: (не указан)")
        print(f"  Имя: {user['first_name']}" if user['first_name'] else "  Имя: (не указано)")
        print(f"  Дата рождения: {user['birth_date']}")
        
        # Вычисляем текущие данные
        try:
            birth_date = date.fromisoformat(user['birth_date'])
            current_week, total_days = calculate_weeks_and_days(birth_date)
            age_years = (date.today() - birth_date).days // 365
            
            print(f"  Возраст: ~{age_years} лет")
            print(f"  Текущая неделя: {current_week}")
            print(f"  Всего дней: {total_days}")
            print(f"  Последняя отправленная неделя: {user['last_week_sent']}")
            
            if current_week > user['last_week_sent']:
                print(f"  ⚠️ ТРЕБУЕТСЯ ОТПРАВКА! (неделя {current_week} > {user['last_week_sent']})")
            else:
                print(f"  ✅ Актуально")
                
        except Exception as e:
            print(f"  ⚠️ Ошибка при расчете: {e}")
        
        print(f"  Создан: {user['created_at']}")
        print(f"  Обновлен: {user['updated_at']}")
        print(f"{'-'*80}\n")

if __name__ == "__main__":
    main()


