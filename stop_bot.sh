#!/bin/bash

# Скрипт для остановки бота

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PID_FILE="$DIR/bot.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "PID файл не найден. Ищем процесс вручную..."
    PID=$(ps aux | grep "[p]ython3 bot.py" | awk '{print $2}')
    if [ -z "$PID" ]; then
        echo "Бот не запущен"
        exit 0
    fi
else
    PID=$(cat "$PID_FILE")
fi

if ps -p $PID > /dev/null 2>&1; then
    echo "Остановка бота (PID: $PID)..."
    kill $PID
    sleep 1
    
    # Проверяем, завершился ли процесс
    if ps -p $PID > /dev/null 2>&1; then
        echo "Принудительная остановка..."
        kill -9 $PID
    fi
    
    rm -f "$PID_FILE"
    echo "Бот остановлен"
else
    echo "Процесс не найден"
    rm -f "$PID_FILE"
fi


