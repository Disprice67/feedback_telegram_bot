from settings.config import URL_WEB_SITE
from io import BytesIO
import pandas as pd


# Upload_files
def read_excel(file_stream: BytesIO) -> pd.DataFrame | None:
    try:
        return pd.read_excel(file_stream)
    except Exception:
        return None


def get_category_config(category: str) -> dict | None:
    return {
        'upload_managers': {
            'url': f'{URL_WEB_SITE}/api/v1/activities/',
            'columns': ['Код активности', 'Название активности', 'Сервис-менеджер']
        },
        'upload_cases': {
            'url': f'{URL_WEB_SITE}/api/v1/cases/',
            'columns': ['Код', 'Создано', 'Дата решения', 'Приоритет', 'Статус', 'Тема', 'Описание', 'Автор', 'Исполнитель', 'Активность', 'Вендор', 'Рабочая группа', 'Описание решения', 'Код решения', 'Организация']
        },
        'upload_engineers': {
            'url': f'{URL_WEB_SITE}/api/v1/users/',
            'columns': ['Почта', 'ФИ']
        },
        'download_xlsx': {
            'url': f'{URL_WEB_SITE}/api/v1/activities/export/',
            'columns': []
        }
    }.get(category)


async def get_file_stream(message) -> BytesIO:
    file = await message.bot.download(message.document.file_id)
    file.seek(0)
    return BytesIO(file.read())


def validate_columns(df: pd.DataFrame, required: list[str]) -> bool:
    return all(col in df.columns for col in required)
