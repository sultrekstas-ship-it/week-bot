#!/bin/bash

# Скрипт для проверки статуса бота

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PID_FILE="$DIR/bot.pid"

echo "=== Статус бота Life Weeks ==="
echo ""

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null 2>&1; then
        echo "✅ Бот работает (PID: $PID)"
        echo ""
        echo "Информация о процессе:"
        ps -f -p $PID
        echo ""
        echo "Использование ресурсов:"
        ps -o pid,user,%cpu,%mem,vsz,rss,comm -p $PID
    else
        echo "❌ Бот не работает (но PID файл существует)"
        rm -f "$PID_FILE"
    fi
else
    # Ищем процесс вручную
    PID=$(ps aux | grep "[p]ython3 bot.py" | awk '{print $2}')
    if [ ! -z "$PID" ]; then
        echo "⚠️ Бот работает (PID: $PID), но PID файл отсутствует"
        echo $PID > "$PID_FILE"
    else
        echo "❌ Бот не запущен"
    fi
fi

echo ""
echo "Логи (последние 10 строк):"
echo "================================"
if [ -f "$DIR/bot.log" ]; then
    tail -10 "$DIR/bot.log"
else
    echo "Файл логов не найден"
fi


