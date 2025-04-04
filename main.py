from selenium import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from datetime import datetime
from dateutil.relativedelta import relativedelta
import re
import time

def scrape_movie_dates_with_selenium(url):
    """Seleniumを使って指定されたURLの映画.com公開予定ページから映画のタイトルと気になる数をスクレイピングする"""
    movie_data = {}
    try:
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_experimental_option("excludeSwitches", ["enable-logging"])
        driver = webdriver.Chrome(options=options)
        print(f"Seleniumで {url} のスクレイピングを開始します...")
        driver.get(url)
        time.sleep(2)

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        elements = soup.find_all(['h2', 'div'], class_=['title-square', 'list-block list-block2'])

        current_release_date = None
        seen_titles = set()

        for element in elements:
            if element.name == 'h2' and 'title-square' in element.get('class', []):
                year_span = element.find('span', class_='year')
                calendar_span = element.find('span', class_='icon calendar')

                if year_span and calendar_span:
                    year_text = year_span.text.replace('年', '')
                    date_text_raw = calendar_span.text.replace('（土）公開・配信開始', '').replace('（水）公開・配信開始', '').replace('（木）公開・配信開始', '').replace('（金）公開・配信開始', '')

                    try:
                        date_match = re.search(r'(\d+)月(\d+)日', date_text_raw)
                        if date_match:
                            month_text = date_match.group(1)
                            day_text = date_match.group(2)
                            current_release_date = datetime.strptime(f"{year_text}{month_text}月{day_text}日", '%Y%m月%d日')
                        else:
                            month_match = re.search(r'(\d+)月', date_text_raw)
                            if month_match:
                                month_text = month_match.group(1)
                                current_release_date = datetime.strptime(f"{year_text}{month_text}月1日", '%Y%m月%d日')
                            else:
                                current_release_date = None
                    except ValueError:
                        current_release_date = None
                    seen_titles = set() # 新しい日付になったらseen_titlesをリセット
                    if current_release_date:
                        print(f"  新しい日付を検出: {current_release_date}")

            elif element.name == 'div' and 'list-block2' in element.get('class', []):
                if current_release_date:
                    title_element = element.find('h3', class_='title')
                    checkin_box = element.find('div', class_='txt-box txt-box2')
                    if title_element and title_element.find('a') and checkin_box:
                        title = title_element.find('a').text.strip()
                        normalized_title = title.strip()
                        checkin_button = checkin_box.find('input', class_='checkin-btn checkin-count')
                        if normalized_title not in seen_titles:
                            if checkin_button and 'value' in checkin_button.attrs:
                                checkin_count_str = checkin_button['value'].strip()
                                if checkin_count_str and checkin_count_str.isdigit():
                                    checkin_count_int = int(checkin_count_str)
                                    print(f"    タイトル: {normalized_title}, 公開日: {current_release_date}")
                                    if current_release_date not in movie_data:
                                        movie_data[current_release_date] = []
                                    movie_data[current_release_date].append({'title': normalized_title, 'checkin_count': checkin_count_int})
                                    seen_titles.add(normalized_title)

        print(f"Seleniumで {url} のスクレイピングを終了しました。")

    except Exception as e:
        print(f"Seleniumエラーが発生しました ({url}): {e}")
    finally:
        driver.quit()

    return movie_data

def get_upcoming_movie_data(num_months=4):
    all_movies = {}
    today = datetime.now()

    # 今月のURL
    current_month_url = 'https://eiga.com/coming/'
    print(f"今月の映画情報を取得します: {current_month_url}")
    all_movies.update(scrape_movie_dates_with_selenium(current_month_url))

    # 翌月から指定した月数までのURLを生成してスクレイピング
    for i in range(1, num_months):
        target_date = today + relativedelta(months=+i)
        year_month_str = target_date.strftime('%Y%m')
        monthly_url = f'https://eiga.com/coming/{year_month_str}/'
        print(f"{target_date.strftime('%Y年%m月')}の映画情報を取得します: {monthly_url}")
        all_movies.update(scrape_movie_dates_with_selenium(monthly_url))

    return all_movies

def filter_and_format_output(movie_data, min_checkin=1000):
    today = datetime.now().date()
    future_movies = {}
    for date, movie_list in movie_data.items():
        release_date = date.date()
        if release_date >= today:
            if release_date not in future_movies:
                future_movies[release_date] = []
            for movie in movie_list:
                if movie['checkin_count'] >= min_checkin:
                    future_movies[release_date].append(movie['title'])

    output = []
    sorted_dates = sorted(future_movies.keys())
    current_month = None
    for date in sorted_dates:
        month = date.month
        day = date.day
        if current_month != month:
            output.append(f"\n{month}月")
            current_month = month
        for title in sorted(list(set(future_movies[date]))): # 最終出力時にも念のため重複排除
            output.append(f"{month}/{day} {title}")
    return "\n".join(output)

if __name__ == "__main__":
    upcoming_movie_data = get_upcoming_movie_data(num_months=4)
    output_text = filter_and_format_output(upcoming_movie_data, min_checkin=1000)

    output_file = "movie_dates.txt"
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(output_text)
        print(f"結果を {output_file} に保存しました。")
    except Exception as e:
        print(f"ファイルへの書き込み中にエラーが発生しました: {e}")
        print("エラー内容:")
        print(output_text)