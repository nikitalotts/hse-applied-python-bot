import aiohttp
import requests
from typing import Dict, Any, Optional
from googletrans import Translator
from requests import RequestException


class WeatherApiClient:
    def __init__(self, api_key: str) -> None:
        self.api_key: str = api_key
        self.base_url: str = "http://api.openweathermap.org/data/2.5/weather"
        self.check_key()

    def check_key(self) -> bool:
        try:
            response = requests.get(f"{self.base_url}?q=London&appid={self.api_key}")
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise RequestException("Not valid API key")

    async def get_weather_async(self, city: str) -> Dict[str, Any]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}?q={city}&appid={self.api_key}&units=metric&lang=ru") as response:
                    response.raise_for_status()
                    return await response.json()
        except aiohttp.ClientError as e:
            return {"error": str(e)}

    async def is_city_exists(self, city: str) -> bool:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                        f"{self.base_url}?q={city}&appid={self.api_key}&units=metric&lang=ru") as response:
                    await response.text()
                    return response.status == 404
        except aiohttp.ClientError:
            return False


class ProductsApiClient:
    async def get_product_info(self, product: str) -> Optional[Dict[str, Any]]:
        product_name = await translate(product)
        url = f"https://world.openfoodfacts.org/cgi/search.pl?action=process&search_terms={product_name}&json=true"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                try:
                    data = await response.json()
                    products = data.get('products', [])
                    if products:  # Проверяем, есть ли найденные продукты
                        first_product = products[0]
                        return {
                            'name': first_product.get('product_name', 'Неизвестно'),
                            'calories': first_product.get('nutriments', {}).get('energy-kcal_100g', 0)
                        }
                    return None
                except aiohttp.ClientError as e:
                    return {"error": str(e)}


class WorkoutApiClient:
    def __init__(self, api_key: str) -> None:
        self.api_key: str = api_key
        self.check_key()

    def check_key(self) -> bool:
        try:
            response = requests.get(
                f"https://api.api-ninjas.com/v1/caloriesburned?activity=running",
                headers={'X-Api-Key': self.api_key}
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise RequestException("Not valid API key")

    async def get_exercise_info(self, exercise_name: str) -> Optional[Dict[str, Any]]:
        exercise = await translate(exercise_name)
        url = f"https://api.api-ninjas.com/v1/caloriesburned?activity={exercise}"
        async with aiohttp.ClientSession(headers={'X-Api-Key': self.api_key}) as session:
            async with session.get(url) as response:
                try:
                    data = await response.json()
                    response.raise_for_status()
                    if data:
                        first_exercise = data[0]
                        return {
                            'name': first_exercise.get('name', 'Неизвестно'),
                            'calories': first_exercise.get('calories_per_hour', 0)
                        }
                    return None
                except aiohttp.ClientError as e:
                    return {"error": str(e)}


async def translate(text: str, destination='en') -> str:
    async with Translator() as translator:
        translation = await translator.translate(text, dest=destination)
        return translation.text


def test_weather_api_client(api_key: str, city: str) -> None:
    weather_client = WeatherApiClient(api_key=api_key)

    try:
        weather_client.check_key()
        print("API key is valid.")
    except Exception as e:
        print(f"API key validation failed: {e}")

    async def test_get_weather():
        result = await weather_client.get_weather_async(city)
        if "error" in result:
            print(f"Error while fetching weather data: {result['error']}")
        else:
            print(f"Weather data for Moscow: {result}")

    asyncio.run(test_get_weather())


def test_products_api_client(product: str):
    async def test_get_food_info():
        product_client = ProductsApiClient()
        search_query = await translate(product)
        result = await product_client.get_food_info(search_query)
        if result is None:
            print("No product information found.")
        elif "error" in result:
            print(f"Error while fetching product data: {result['error']}")
        else:
            print(f"Product information: {result}")

    asyncio.run(test_get_food_info())


def test_exercise_api_client(exercise: str):
    async def test_get_exercise_info():
        product_client = WorkoutApiClient(WORKOUT_API_TOKEN)
        result = await product_client.get_exercise_info(exercise)
        if result is None:
            print("No product information found.")
        elif "error" in result:
            print(f"Error while fetching product data: {result['error']}")
        else:
            print(f"Product information: {result}")

    asyncio.run(test_get_exercise_info())


if __name__ == "__main__":
    import asyncio
    from config import OPEN_WEATHER_MAP_TOKEN, WORKOUT_API_TOKEN

    print("Testing WeatherApiClient...")
    test_weather_api_client(OPEN_WEATHER_MAP_TOKEN, "Москва")

    print("\nTesting ProductsApiClient...")
    test_products_api_client("банан")

    print("\nTesting WorkoutApiClient...")
    test_exercise_api_client("бег")
