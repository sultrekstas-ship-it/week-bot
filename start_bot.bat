@echo off
chcp 65001 > nul
echo Запуск Telegram бота "Недели жизни"...
echo.

if not exist .env (
    echo ОШИБКА: Файл .env не найден!
    echo Создайте файл .env на основе .env.example
    echo и добавьте токен вашего бота.
    pause
    exit /b 1
)

if not exist venv (
    echo Создание виртуального окружения...
    python -m venv venv
    echo.
)

echo Активация виртуального окружения...
call venv\Scripts\activate.bat

echo Установка зависимостей...
pip install -r requirements.txt --quiet

echo.
echo Запуск бота...
echo Для остановки нажмите Ctrl+C
echo.

python bot.py

pause


