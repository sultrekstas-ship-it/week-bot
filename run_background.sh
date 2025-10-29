#!/bin/bash

# Скрипт для запуска бота в фоне на Linux

# Получаем директорию скрипта
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Останавливаем старый процесс если есть
PID_FILE="$DIR/bot.pid"
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p $OLD_PID > /dev/null 2>&1; then
        echo "Остановка старого процесса (PID: $OLD_PID)..."
        kill $OLD_PID
        sleep 2
    fi
fi

# Запускаем бота
echo "Запуск бота в фоне..."
nohup python3 bot.py > bot.log 2>&1 &
NEW_PID=$!

# Сохраняем PID
echo $NEW_PID > "$PID_FILE"

echo "Бот запущен с PID: $NEW_PID"
echo "Логи: tail -f $DIR/bot.log"
echo "Остановка: kill $NEW_PID"


