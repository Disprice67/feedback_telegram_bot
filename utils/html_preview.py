import pandas as pd


def generate_engineers_preview(df: pd.DataFrame, page: int = 0, max_rows: int = 10) -> tuple[str, int, int]:
    """
    Генерирует HTML-превью для списка инженеров из DataFrame с пагинацией.
    Возвращает HTML-код, текущую страницу и общее количество страниц.
    """
    start = page * max_rows
    end = start + max_rows
    total_pages = (len(df) + max_rows - 1) // max_rows

    html = '<b>📋 Превью инженеров</b>\n'
    html += '<i>Листайте, чтобы просмотреть записи</i>\n'
    html += '<pre>┌' + '─' * 48 + '┐\n'

    html += f"│ {'📧 Почта':<23} │ {'👤 ФИ':<20} │\n"
    html += '├' + '─' * 48 + '┤\n'

    for index, row in df[start:end].iterrows():
        username = row.get('Почта', '—')[:25]
        first_name = row.get('ФИ', '—')[:25]
        html += f"│ {username:<23} │ {first_name:<20} │\n"

    html += '└' + '─' * 48 + '┘\n'
    html += f'<i>Страница {page + 1} из {total_pages}</i></pre>'

    return html, page, total_pages


def generate_cases_preview(df: pd.DataFrame, page: int = 0, max_rows: int = 10) -> tuple[str, int, int]:
    """
    Генерирует HTML-превью для списка кейсов из DataFrame с пагинацией, показывая уникальных исполнителей и их количество кейсов.
    Возвращает HTML-код, текущую страницу и общее количество страниц.
    """
    case_counts = df['Исполнитель'].value_counts().reset_index()
    case_counts.columns = ['Исполнитель', 'Кол-во кейсов']

    start = page * max_rows
    end = start + max_rows
    total_pages = (len(case_counts) + max_rows - 1) // max_rows

    html = '<b>📋 Превью кейсов</b>\n'
    html += '<i>Листайте, чтобы просмотреть записи</i>\n'
    html += '<pre>┌' + '─' * 48 + '┐\n'

    html += f"│ {'👤 Исполнитель':<23} │ {'📊 Кол-во кейсов':<20} │\n"
    html += '├' + '─' * 48 + '┤\n'

    for index, row in case_counts[start:end].iterrows():
        executor = str(row['Исполнитель'])[:25]
        count = row['Кол-во кейсов']
        html += f"│ {executor:<23} │ {count:<20} │\n"

    html += '└' + '─' * 48 + '┘\n'
    html += f'<i>Страница {page + 1} из {total_pages}</i></pre>'

    return html, page, total_pages


def generate_managers_preview(df: pd.DataFrame, page: int = 0, max_rows: int = 10) -> tuple[str, int, int]:
    """
    Генерирует HTML-превью для списка активностей из DataFrame с пагинацией.
    Возвращает HTML-код, текущую страницу и общее количество страниц.
    """
    start = page * max_rows
    end = start + max_rows
    total_pages = (len(df) + max_rows - 1) // max_rows

    html = '<b>📋 Превью активностей</b>\n'
    html += '<i>Листайте, чтобы просмотреть записи</i>\n'
    html += '<pre>┌' + '─' * 48 + '┐\n'

    html += f"│ {'📋 Название активности':<23} │ {'👤 Сервис-менеджер':<20} │\n"
    html += '├' + '─' * 48 + '┤\n'

    for index, row in df[start:end].iterrows():
        activity_name = str(row.get('Название активности', '—'))[:20]  # Сокращаем до 20 символов
        if len(str(row.get('Название активности', ''))) > 20:
            activity_name += '...'  # Добавляем многоточие, если обрезано
        manager = str(row.get('Сервис-менеджер', '—'))[:20]
        html += f"│ {activity_name:<23} │ {manager:<20} │\n"

    html += '└' + '─' * 48 + '┘\n'
    html += f'<i>Страница {page + 1} из {total_pages}</i></pre>'

    return html, page, total_pages