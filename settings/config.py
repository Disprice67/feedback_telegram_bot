from dotenv import load_dotenv
from os import getenv


load_dotenv()

BOT_TOKEN = getenv('BOT_TOKEN')
JWT_TOKEN = getenv('JWT_TOKEN')
URL_WEB_SITE = getenv('URL_WEB_SITE')
HEADERS = {
    "Authorization": f"Bearer {JWT_TOKEN}"
}
