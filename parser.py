import json
import time
from datetime import date, timedelta

import requests
from bs4 import BeautifulSoup

BASE_URL = 'https://pythondigest.ru/feed'


class Api:
    def __init__(self, url: str):
        self.url = url
        self.session = requests.Session()
        headers = {'User-Agent': 'learn-python-lesson-20 (mansur.gabidullin@gmail.com)'}
        self.session.headers.update(headers)

    def get(self, page: int):
        if page < 1:
            raise ValueError('page must be greater then 0')

        response = self.session.get(self.url, params={'page': page})

        if response.status_code < 200 or response.status_code >= 300:
            exit(1)

        return response.text


if __name__ == '__main__':
    today = date.today()
    start = today - timedelta(days=today.day - 1)

    print("Получение новостей за текущий месяц...")

    api = Api(BASE_URL)
    start_timestamp = time.time()
    news_items = []
    page = 0
    page_limit = 20
    stop = False

    while not stop:
        page += 1

        if page >= page_limit:
            break

        soup = BeautifulSoup(api.get(page=page), 'html.parser')
        news_list_item_tags = soup.find(class_='news-list').select('.item-container')

        if len(news_list_item_tags) == 0:
            break

        for item in news_list_item_tags:
            date_str = tuple(item.select_one('.news-line-dates small').children)[0].text.strip().split('.')
            day, month, year = map(int, date_str)
            news_date = date(year, month, day)

            if start > news_date:
                stop = True
                break

            news_title = item.select_one('.news-line-item h4').text.strip()
            news_description = ''.join(map(lambda t: t.text, tuple(item.select('.news-line-item > :not(h4)'))))
            url = item.select_one('.news-line-item a').attrs['href'].split('?')[0]

            news_items.append({
                'date': news_date.isoformat(),
                'title': news_title,
                'description': news_description,
                'url': url,
            })

    task_time = round(time.time() - start_timestamp, 2)
    rps = round(page / task_time, 1)
    print(f"| Requests: {page}; Total time: {task_time} s; RPS: {rps}. |")

    with open('data.json', 'wt', encoding='utf-8') as json_file:
        json.dump(news_items, json_file, ensure_ascii=False, indent=2)
