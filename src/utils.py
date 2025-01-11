import io
import matplotlib.pyplot as plt
from src.logger import get_logger
from src.config import OPEN_WEATHER_MAP_TOKEN, WORKOUT_API_TOKEN
from src.api import WeatherApiClient, WorkoutApiClient, ProductsApiClient
from src.users import get_user_daily_calorie_goal, get_user_daily_water_goal

weather_client = WeatherApiClient(OPEN_WEATHER_MAP_TOKEN)
workout_client = WorkoutApiClient(WORKOUT_API_TOKEN)
product_client = ProductsApiClient()
logger = get_logger()


def parse_numeric_value(value: str):
    try:
        return float(value)
    except Exception as e:
        logger.error(e)
        return None


def parse_and_validate(value: str, lower_bound: int, upper_bound: int):
    numeric_value = parse_numeric_value(value)

    if numeric_value and lower_bound < numeric_value < upper_bound:
        return numeric_value

    return None


def log_command(command: str, user_id: int, username: str):
    logger.info(f"Получена команда /{command} от пользователя {user_id}, {username}")


def create_water_chart(user_id, dates, logged_water):
    plt.figure(figsize=(10, 5))
    plt.plot(dates, logged_water, marker='o', linestyle='-', color='b', label='Суточное потребление (мл)')
    plt.axhline(y=get_user_daily_water_goal(user_id), color='r', linestyle='--', label='Суточная норма (мл)')
    plt.title("Потребление воды")
    plt.xlabel("Дата")
    plt.ylabel("Количество воды (мл)")
    plt.xticks(rotation=45)
    plt.legend()
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    return buf.read()


def create_calories_chart(user_id, dates, logged_water):
    plt.figure(figsize=(10, 5))
    plt.plot(dates, logged_water, marker='o', linestyle='-', color='b', label='Суточное потребление (ккал)')
    plt.axhline(y=get_user_daily_calorie_goal(user_id), color='r', linestyle='--', label='Суточная норма (ккал)')
    plt.title("Потребление калорий")
    plt.xlabel("Дата")
    plt.ylabel("Количество (ккал)")
    plt.xticks(rotation=45)
    plt.legend()
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    return buf.read()


async def check_city(city: str):
    city = city.lower().capitalize().strip()
    if not city.isalpha() or await weather_client.is_city_exists(city):
        return None
    return city
