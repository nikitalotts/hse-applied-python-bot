import os
from dotenv import load_dotenv

# Загрузка переменных из .env файла
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPEN_WEATHER_MAP_TOKEN = os.getenv("OPEN_WEATHER_MAP_TOKEN")
WORKOUT_API_TOKEN = os.getenv("WORKOUT_API_TOKEN")

if not BOT_TOKEN:
    raise ValueError("Environment variable BOT_TOKEN is not set!")

if not OPEN_WEATHER_MAP_TOKEN:
    raise ValueError("Environment variable OPEN_WEATHER_MAP_TOKEN is not set!")

if not WORKOUT_API_TOKEN:
    raise ValueError("Environment variable WORKOUT_API_TOKEN is not set!")
