from dotenv import load_dotenv
from os import getenv


load_dotenv()

API_URL = getenv('API_URL')
BOT_TOKEN = getenv('BOT_TOKEN')
JWT_TOKEN = getenv('JWT_TOKEN')
URL_WEB_SITE = getenv('URL_WEB_SITE')
HEADER = {
    "Authorization": f"Bearer {JWT_TOKEN}"
}
