from aiogram import Router, Dispatcher
from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile
from aiogram.filters import Command, CommandObject
from src.states import ProfileSetup, FoodLogging
from src.commands import *
from src.utils import *
from src.users import *
from src.config import ADMIN_USER_ID

router = Router()


@router.message(Command(START))
async def start(message: types.Message):
    log_command(START, message.from_user.id, message.from_user.username)
    await message.answer("Привет! Я помогу тебе рассчитать нормы воды и калорий. "
                         "Используй /help для списка команд.")


@router.message(Command(HELP))
async def help(message: types.Message):
    log_command(HELP, message.from_user.id, message.from_user.username)
    await message.answer(
        "Список доступных команд:\n\n"
        "/start — Начать работу с ботом\n"
        "/help — Список доступных команд\n"
        "/set_profile — Настроить профиль (без выполнения это команды остальные работать не будут)\n"
        "/log_water <объем> — Записать количество выпитой воды (в мл)\n"
        "/log_food <название продукта> — Записать продукт и его количество\n"
        "/log_workout <активность> <время> — Записать тренировку\n"
        "/check_progress — Проверить прогресс за сегодня\n"
        "/show_water_chart — Показать график потребления воды\n"
        "/show_calories_chart — Показать график потребления калорий\n"
        f"{'/fake — (Служ.) Сгенерировать тестовые данные для графика' if message.from_user.id == ADMIN_USER_ID else ''}"
    )


@router.message(Command(SET_PROFILE))
async def set_profile(message: types.Message, state: FSMContext):
    log_command(SET_PROFILE, message.from_user.id, message.from_user.username)
    await message.answer("Введите ваш вес (в кг):")
    await state.set_state(ProfileSetup.weight)


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
    user_data["city"] = city
    user_id = message.from_user.id

    add_user(user_id, user_data)
    await set_norms_for_day(user_id, city)
    await message.answer("Профиль успешно настроен! Используйте /check_progress для проверки прогресса.")
    await state.clear()


@router.message(Command(SHOW_WATER_CHART))
async def show_water_chart(message: types.Message):
    log_command(SHOW_WATER_CHART, message.from_user.id, message.from_user.username)

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
async def show_calories_chart(message: types.Message):
    log_command(SHOW_CALORIES_CHART, message.from_user.id, message.from_user.username)

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


@router.message(Command(CHECK_PROGRESS))
async def check_progress(message: types.Message):
    log_command(CHECK_PROGRESS, message.from_user.id, message.from_user.username)
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
    log_command(LOG_WATER, message.from_user.id, message.from_user.username)
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
    log_command(LOG_WORKOUT, message.from_user.id, message.from_user.username)
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
    log_command(LOG_FOOD, message.from_user.id, message.from_user.username)
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


@router.message(Command(FAKE))
async def fake(message: types.Message):
    log_command(FAKE, message.from_user.id, message.from_user.username)
    user_id = message.from_user.id
    if user_id != ADMIN_USER_ID:
        return
    await generate_fake_date(user_id, 7)
    await message.reply("Тестовые данные сгенерированы")


def setup_handlers(dp: Dispatcher):
    dp.include_router(router)
