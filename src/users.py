import random
from datetime import datetime, date, timedelta
from src.api import WeatherApiClient
from src.config import OPEN_WEATHER_MAP_TOKEN

users = {}

weather_client = WeatherApiClient(OPEN_WEATHER_MAP_TOKEN)


def add_user(user_id: int, user_data: dict):
    users[user_id] = {
        "weight": user_data.get("weight"),
        "height": user_data.get("height"),
        "age": user_data.get("age"),
        "activity": user_data.get("activity"),
        "city": user_data.get("city").capitalize(),
        "daily_norm": {
            "water_goal": user_data.get("weight") * 30 + user_data.get("activity") * 10,
            "calorie_goal": (
                    10 * user_data.get("weight")
                    + 6.25 * user_data.get("height")
                    - 5 * user_data.get("age")
            ),
        },
        "stats": {}
    }


def is_user_exists(user_id: int):
    return user_id in users


def ensure_statistics_exists(user_id: int, date: date):
    if date not in users[user_id]["stats"]:
        users[user_id]["stats"][date] = {
            "logged_water": 0,
            "additional_water": 0,
            "logged_calories": 0,
            "burned_calories": 0,
        }


def add_water(user_id: int, date: date, volume: float):
    users[user_id]["stats"][date]["logged_water"] += volume


def inc_water_norm(user_id: int, date: date, volume: float):
    users[user_id]["stats"][date]["additional_water"] += volume


def burn_calories(user_id: int, date: date, amount: float):
    users[user_id]["stats"][date]["burned_calories"] += amount


def add_calories(user_id: int, date: date, amount: float):
    users[user_id]["stats"][date]["logged_calories"] += amount


def get_user_statistic_and_profile(user_id: int, date: date):
    stats = users[user_id]["stats"][date]
    profile = users[user_id]
    return stats, profile


def get_user_basenorm(user_id: int):
    return users[user_id]["daily_norm"]


async def set_norms_for_day(user_id: int, city: str):
    today = datetime.now().date()

    ensure_statistics_exists(user_id, today)
    await add_water_goal_for_day(user_id, today, city)
    add_calorie_goal_for_day(user_id, today)


async def add_water_goal_for_day(user_id: int, date: date, city):
    weather_data = await weather_client.get_weather_async(city)
    temperature = weather_data["main"]["temp"]

    users[user_id]["stats"][date]["water_goal"] = (users[user_id]["daily_norm"]["water_goal"] +
                                                   (500 if temperature and temperature > 25 else 0))


def add_calorie_goal_for_day(user_id: int, date: date):
    activity_level = users[user_id]['activity']
    users[user_id]["stats"][date]["calorie_goal"] = (users[user_id]["daily_norm"]["calorie_goal"] +
                                                     (300 if activity_level > 60 else 0))


def get_stats(user_id, key):
    stats = users[user_id]['stats']
    dates = list(stats.keys())
    logged_water = [stats[day][key] for day in dates]
    return dates, logged_water


def get_active_days(user_id):
    stats = users[user_id]['stats']
    return len(list(stats.keys()))


def get_user_daily_calorie_goal(user_id: int):
    return users[user_id]['daily_norm']['calorie_goal']


def get_user_daily_water_goal(user_id: int):
    return users[user_id]['daily_norm']['water_goal']

async def generate_fake_date(user_id: int, days_before: int):
    for day_before in range(days_before):
        day = datetime.now().date() - timedelta(days=day_before)
        ensure_statistics_exists(user_id, day)

        # add random amount of calories
        add_calories(user_id, day, random.randint(1000, 5000))

        # add random amount of water
        add_water(user_id, day, random.randint(1000, 5000))
