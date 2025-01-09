import io
import random
import matplotlib.pyplot as plt
from datetime import datetime, date, timedelta
from aiogram import Router, Dispatcher
from aiogram import Bot, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile
from aiogram.filters import Command, CommandObject
from states import ProfileSetup, FoodLogging
from commands import *
from api import WeatherApiClient, WorkoutApiClient, ProductsApiClient
from config import OPEN_WEATHER_MAP_TOKEN, WORKOUT_API_TOKEN

router = Router()
weather_client = WeatherApiClient(OPEN_WEATHER_MAP_TOKEN)
workout_client = WorkoutApiClient(WORKOUT_API_TOKEN)
product_client = ProductsApiClient()

users = {}


@router.message(Command(START))
async def start(message: types.Message, state: FSMContext):
    await message.answer("Привет! Я помогу тебе рассчитать нормы воды и калорий. "
                         "Используй /help для списка команд.")
    #await state.clear()


def parse_numeric_value(value: str):
    try:
        return float(value)
    except Exception as e:
        print(e)
        return None


def parse_and_validate(value: str, lower_bound: int, upper_bound: int):
    numeric_value = parse_numeric_value(value)

    if numeric_value and lower_bound < numeric_value < upper_bound:
        return numeric_value

    return None


@router.message(Command(SET_PROFILE))
async def set_profile(message: types.Message, state: FSMContext):
    await message.answer("Введите ваш вес (в кг):")
    await state.set_state(ProfileSetup.weight)


@router.message(Command("temp"))
async def temp(message: types.Message, state: FSMContext):
    x = users
    await message.reply(str(x))


@router.message(Command("fake"))
async def fake(message: types.Message):
    await generate_fake_date(message.from_user.id, 7)
    await message.reply("ok")


@router.message(Command(SHOW_WATER_CHART))
async def fake(message: types.Message):
    user_id = message.from_user.id

    if get_active_days(user_id) < 2:
        await message.answer("Данная функция пока недоступна, Вы должны иметь не менее 2 активных дней.")
        return

    dates, logged_water = get_stats(user_id, 'logged_water')
    graph_image = create_water_chart(user_id, dates, logged_water)
    await message.reply_photo(
        photo=BufferedInputFile(graph_image, filename="water_chart.png"),
        caption="График потребления воды"
    )


@router.message(Command(SHOW_CALORIES_CHART))
async def fake(message: types.Message):
    user_id = message.from_user.id

    if get_active_days(user_id) < 2:
        await message.answer("Данная функция пока недоступна, Вы должны иметь не менее 2 активных дней.")
        return

    dates, logged_calories = get_stats(user_id, 'logged_calories')
    graph_image = create_calories_chart(user_id, dates, logged_calories)
    await message.reply_photo(
        photo=BufferedInputFile(graph_image, filename="calories_chart.png"),
        caption="График потребления калорий"
    )


@router.message(ProfileSetup.weight, F.text)
async def process_weight(message: types.Message, state: FSMContext):
    weight = parse_and_validate(message.text, 20, 300)
    if not weight:
        await message.answer("Пожалуйста, введите корректное значение.")
        return
    await state.update_data(weight=weight)
    await message.answer("Введите ваш рост (в см):")
    await state.set_state(ProfileSetup.height)


@router.message(ProfileSetup.height, F.text)
async def process_height(message: types.Message, state: FSMContext):
    height = parse_and_validate(message.text, 50, 250)
    if not height:
        await message.answer("Пожалуйста, введите корректное значение.")
        return
    await state.update_data(height=height)
    await message.answer("Введите ваш возраст:")
    await state.set_state(ProfileSetup.age)


@router.message(ProfileSetup.age, F.text)
async def process_age(message: types.Message, state: FSMContext):
    age = parse_and_validate(message.text, 0, 150)
    if not age:
        await message.answer("Пожалуйста, введите корректное значение.")
        return
    await state.update_data(age=age)
    await message.answer("Сколько минут активности у вас в день? (в минутах)")
    await state.set_state(ProfileSetup.activity)


@router.message(ProfileSetup.activity, F.text)
async def process_activity(message: types.Message, state: FSMContext):
    activity = parse_and_validate(message.text, 0, 24 * 60 * 60)
    if not activity:
        await message.answer("Пожалуйста, введите корректное значение.")
        return
    await state.update_data(activity=activity)
    await message.answer("В каком городе вы находитесь?")
    await state.set_state(ProfileSetup.city)


@router.message(ProfileSetup.city, F.text)
async def process_city(message: types.Message, state: FSMContext):
    city = await check_city(message.text)
    if not city:
        await message.answer("Пожалуйста, введите корректное название города.")
        return

    user_data = await state.get_data()
    user_id = message.from_user.id

    users[user_id] = {
        "weight": user_data.get("weight"),
        "height": user_data.get("height"),
        "age": user_data.get("age"),
        "activity": user_data.get("activity"),
        "city": message.text.capitalize(),
        "daily_norm": {
            "water_goal": user_data.get("weight") * 30 + user_data.get("activity") * 10,
            "calorie_goal": (
                    10 * user_data.get("weight")
                    + 6.25 * user_data.get("height")
                    - 5 * user_data.get("age")
            ),
        },
        "stats": {},
    }

    await set_norms_for_day(user_id, city)
    await message.answer("Профиль успешно настроен! Используйте /check_progress для проверки прогресса.")
    await state.clear()


async def generate_fake_date(user_id: int, days_before: int):
    for day_before in range(days_before):
        day = datetime.now().date() - timedelta(days=day_before)
        ensure_statistics_exists(user_id, day)

        # add random amount of calories
        add_calories(user_id, day, random.randint(1000, 5000))

        # add random amount of water
        add_water(user_id, day, random.randint(1000, 5000))


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


def create_water_chart(user_id, dates, logged_water):
    plt.figure(figsize=(10, 5))
    plt.plot(dates, logged_water, marker='o', linestyle='-', color='b', label='Суточное потребление (мл)')
    plt.axhline(y=users[user_id]['daily_norm']['water_goal'], color='r', linestyle='--', label='Суточная норма (мл)')
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
    plt.axhline(y=users[user_id]['daily_norm']['calorie_goal'], color='r', linestyle='--', label='Суточная норма (ккал)')
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


@router.message(Command(CHECK_PROGRESS))
async def check_progress(message: types.Message):
    user_id = message.from_user.id
    today = datetime.now().date()

    ensure_statistics_exists(user_id, today)

    stats, profile = get_user_statistic_and_profile(user_id, today)

    await message.answer(
        f"📊 Прогресс:\n\n"
        f"Вода:\n"
        f"- Выпито: {stats['logged_water']} мл из {stats['water_goal'] + stats['additional_water']} мл.\n"
        f"- Осталось: {stats['water_goal'] + stats['additional_water'] - stats['logged_water']} мл.\n\n"
        f"Калории:\n"
        f"- Потреблено: {stats['logged_calories']} ккал из {stats['calorie_goal']} ккал.\n"
        f"- Сожжено: {stats['burned_calories']} ккал.\n"
        f"- Баланс: {stats['logged_calories'] - stats['burned_calories']} ккал."
    )


@router.message(Command(LOG_WATER))
async def log_water(message: types.Message, command: CommandObject):
    if not command.args:
        await message.answer('Пожалуйста, введите аргументы команды (например, "/log_water 100").')
        return

    if len(command.args.split()) != 1:
        await message.answer('Пожалуйста, введите один агрумент')
        return

    volume = parse_numeric_value(command.args.split(" ")[0])
    if not volume:
        await message.answer("Пожалуйста, введите корректное численное значение.")
        return

    user_id = message.from_user.id
    today = datetime.now().date()

    ensure_statistics_exists(user_id, today)
    add_water(user_id, today, volume)

    stats, _ = get_user_statistic_and_profile(user_id, today)

    await message.answer(f"Выпито: {stats['logged_water']} мл из {stats['water_goal']} мл.\n")


@router.message(Command(LOG_WORKOUT))
async def log_workout(message: types.Message, command: CommandObject):
    if not command.args:
        await message.answer('Пожалуйста, введите аргументы команды (например, "/log_workout бег 30").')
        return

    if len(command.args.split()) != 2:
        await message.answer('Пожалуйста, введите два агрумента (/log_workout <тип тренировки> <время (мин)>)')
        return

    activity, duration = command.args.split()
    activity = activity.capitalize().strip()

    if not activity.isalpha():
        await message.answer("Пожалуйста, введите корректное название активности.")
        return

    duration = parse_and_validate(duration, 1, 24 * 60 * 60)
    if not duration:
        await message.answer("Пожалуйста, введите корректное численное значение времени выполнения упражнения.")
        return

    activity_info = await workout_client.get_exercise_info(activity)
    if not activity_info:
        await message.answer("Данная активность не найдена, попробуйте другое название.")
        return

    user_id = message.from_user.id
    today = datetime.now().date()
    calories = activity_info['calories'] * duration / 60

    ensure_statistics_exists(user_id, today)

    burn_calories(user_id, today, calories)

    text = f"{activity} {duration} минут — {calories} ккал."

    additonal_water = (duration // 30) * 200
    if additonal_water > 0:
        text += f" Дополнительно: выпейте {additonal_water} мл воды."
        inc_water_norm(user_id, today, additonal_water)

    await message.answer(text)


@router.message(Command(LOG_FOOD))
async def log_food_name(message: types.Message, command: CommandObject, state: FSMContext):
    if not command.args:
        await message.answer('Пожалуйста, введите название продукта (например, "/log_food банан").')
        return

    if len(command.args.split()) != 1:
        await message.answer('Пожалуйста, введите один агрумент (/log_food <тип продукта>)')
        return

    product = command.args.split()[0]
    product = product.capitalize().strip()
    if not product.isalpha():
        await message.answer("Пожалуйста, введите корректное название продукта.")
        return

    await message.answer('Пожалуйста, подождите...')
    product_info = await product_client.get_product_info(product)
    if not product_info:
        await message.answer("Данная продукт не найден, попробуйте другое название.")
        return

    await state.update_data(product_info=product_info)
    await message.answer(f"{product} — {product_info['calories']} ккал на 100 г. Сколько грамм вы съели?")
    await state.set_state(FoodLogging.amount)


@router.message(FoodLogging.amount, F.text)
async def log_food_amount(message: types.Message, state: FSMContext):
    amount = parse_and_validate(message.text, 1, 5000)
    if not amount:
        await message.answer("Пожалуйста, введите корректное значение.")
        return

    user_data = await state.get_data()
    product_info = user_data.get("product_info")

    today = datetime.now().date()
    user_id = message.from_user.id
    calories = product_info["calories"] * amount / 100

    ensure_statistics_exists(user_id, today)

    add_calories(user_id, today, calories)

    await message.answer(f"Записано: {calories} ккал.")
    await state.clear()


def is_user_exists(user_id: int):
    return user_id in users


async def check_city(city: str):
    city = city.lower().capitalize().strip()

    if not city.isalpha() or await weather_client.is_city_exists(city):
        return None

    return city


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


def setup_handlers(dp: Dispatcher):
    dp.include_router(router)
