FROM python:3.12-slim

# Установка FFmpeg и необходимых системных утилит
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем зависимости и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код проекта
COPY . .

# Создаем рабочие папки для данных и временных медиа
RUN mkdir -p data/temp

# Команда запуска бота
CMD ["python", "main.py"]
