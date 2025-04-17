#!/usr/bin/python3

import requests
from bs4 import BeautifulSoup
import os
import time
import re
import argparse
from datetime import datetime, timedelta

BASE_URL = "https://community.elitedangerous.com"
START_URL = f"{BASE_URL}/en/"
OUTPUT_DIR = "elite_news"

MONTH_NAMES = {
    1: "JAN", 2: "FEB", 3: "MAR", 4: "APR", 5: "MAY", 6: "JUN",
    7: "JUL", 8: "AUG", 9: "SEP", 10: "OCT", 11: "NOV", 12: "DEC"
}

def add_years(d, years):
    try:
        return d.replace(year=d.year + years)
    except ValueError:
        # obsługa 29 lutego w nieprzestępnym roku
        return d.replace(month=2, day=28, year=d.year + years)

def find_latest_date():
    latest = None
    if not os.path.exists(OUTPUT_DIR):
        return None

    for root, _, files in os.walk(OUTPUT_DIR):
        for f in files:
            match = re.match(r'(\d{4}-\d{2}-\d{2})', f)
            if match:
                try:
                    date_obj = datetime.strptime(match.group(1), "%Y-%m-%d")
                    if not latest or date_obj > latest:
                        latest = date_obj
                except ValueError:
                    continue
    return latest.strftime("%Y-%m-%d") if latest else None

def get_soup(url):
    print(f"Pobieranie: {url}")
    headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64)'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return BeautifulSoup(response.text, 'html.parser')

def get_all_galnet_links():
    soup = get_soup(START_URL)
    return [
        BASE_URL + a['href']
        for a in soup.select('a.galnetLinkBoxLink[href]')
    ]

def normalize_date(date_str):
    months = {
        'JAN': '01', 'FEB': '02', 'MAR': '03', 'APR': '04',
        'MAY': '05', 'JUN': '06', 'JUL': '07', 'AUG': '08',
        'SEP': '09', 'OCT': '10', 'NOV': '11', 'DEC': '12'
    }
    match = re.match(r'(\d{1,2}) ([A-Z]{3}) (\d{4})', date_str)
    if match:
        day, mon, year = match.groups()
        return f"{year}-{months.get(mon, '00')}-{int(day):02d}"
    return "unknown-date"

def extract_paragraphs(article):
    paragraphs = []
    for p in article.find_all('p'):
        raw_html = str(p)
        split_paragraphs = re.split(r'<br\s*/?><br\s*/?>', raw_html)
        for raw_para in split_paragraphs:
            soup = BeautifulSoup(raw_para, 'html.parser')
            text = soup.get_text(strip=True)
            if text:
                paragraphs.append(text)

    return paragraphs

def adjust_title_and_paragraphs(title, raw_date, paragraphs):
    if not paragraphs:
        return title, paragraphs

    def is_date_string(s):
        return re.match(r'\d{2} [A-Z]{3} \d{4}', s)

    if not title:
        if is_date_string(paragraphs[0]):
            paragraphs = paragraphs[1:]
        if paragraphs:
            title = paragraphs.pop(0)
    elif title == raw_date and len(paragraphs) > 1:
        if is_date_string(paragraphs[0]):
            paragraphs = paragraphs[1:]
        if paragraphs:
            title = paragraphs.pop(0)

    return title, paragraphs

def save_articles_from_page(url, fix_missing_titles=True, skip_existing=True, selected_dates=None):
    try:
        soup = get_soup(url)
    except requests.HTTPError as e:
        print(f"Błąd HTTP: {e}")
        return

    articles = soup.select('div.article')
    narts = len(articles)
    date_counter = {}

    for art in articles:
        title_tag = art.select_one('h3.hiLite.galnetNewsArticleTitle')
        date_tag = art.select_one('p.small[style="color:#888;"]')

        title = title_tag.get_text(strip=True) if title_tag else None
        raw_date = date_tag.get_text(strip=True) if date_tag else "unknown date"
        norm_date = normalize_date(raw_date)

        if selected_dates and norm_date not in selected_dates:
            continue

        year = norm_date.split("-")[0] if norm_date != "unknown-date" else "unknown"
        year_dir = os.path.join(OUTPUT_DIR, year)
        os.makedirs(year_dir, exist_ok=True)

        date_counter[norm_date] = date_counter.get(norm_date, 0) + 1
        index = date_counter[norm_date]

        if narts == 1:
            filename = f"{year_dir}/{norm_date}.md"
        else:
            filename = f"{year_dir}/{norm_date} ({index}).md"

        if skip_existing and os.path.exists(filename):
            print(f"Pomijam istniejący plik: {filename}")
            continue

        paragraphs = extract_paragraphs(art)

        if fix_missing_titles:
            title, paragraphs = adjust_title_and_paragraphs(title, raw_date, paragraphs)

        with open(filename, 'w', encoding='utf-8') as f:
            if title:
                f.write(f"## {title}\n\n")
            f.write(f"**{raw_date}**\n\n")
            for para in paragraphs:
                if para and para != raw_date:
                    f.write(para + "\n\n")

        # Usuwamy puste linie na końcu, jeśli opcja skip_empty_lines jest aktywna
        with open(filename, 'r', encoding='utf-8') as f:
            linie = f.read().splitlines()
        while linie and linie[-1].strip() == "":
            linie.pop()
        with open(filename, 'w', encoding='utf-8') as f:
#                f.write("\n".join(linie) + "\n")
            f.write("\n".join(linie))

        # Oznacz cytaty
        with open(filename, 'r', encoding='utf-8') as f:
            tekst = f.read()
        def dodaj_znak_cytatu(match):
            return '> ' + match.group(0)
        wynik = re.sub(r'(?m)(^“.*?”$)', dodaj_znak_cytatu, tekst)
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(wynik) 
 
        print(f"Zapisano: {filename}")

def date_range(start, end):
    start_date = datetime.strptime(start, "%Y-%m-%d")
    end_date = datetime.strptime(end, "%Y-%m-%d")
    delta = (end_date - start_date).days
    return [(start_date + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(delta + 1)]

def build_direct_link(date):
    dt = datetime.strptime(date, "%Y-%m-%d")
    month_name = MONTH_NAMES[dt.month]
    return f"{BASE_URL}/galnet/{dt.day:02d}-{month_name}-{dt.year}"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--fix-titles', action='store_true', help='Koryguj brakujące tytuły')
    parser.add_argument('--all', action='store_true', help='Pobierz wszystkie artykuły')
    parser.add_argument('--update', action='store_true', help='Pobierz nowe artykuły od ostatnio zapisanej daty')
    parser.add_argument('--date', type=str, help='Pobierz artykuły z konkretnej daty (YYYY-MM-DD)')
    parser.add_argument('--from-date', type=str, help='Pobierz artykuły po wskazanej dacie (YYYY-MM-DD)')
    parser.add_argument('--range', nargs=2, metavar=('START', 'END'), help='Zakres dat do pobrania (YYYY-MM-DD YYYY-MM-DD)')
    parser.add_argument('--no-skip', action='store_true', help='Nie pomijaj istniejących plików')
    parser.add_argument('--fast', action='store_true', help='Bez opóźnień między żądaniami')
    args = parser.parse_args()


    selected_dates = None
    links = []

    if args.date:
        selected_dates = [args.date]
        links = [build_direct_link(args.date)]
    elif args.range:
        selected_dates = date_range(args.range[0], args.range[1])
        links = [build_direct_link(d) for d in selected_dates]
    elif args.from_date:
        current = datetime.strptime(args.from_date, "%Y-%m-%d")
        today = add_years(datetime.today(), 1286)
        selected_dates = [(current + timedelta(days=i)).strftime("%Y-%m-%d") for i in range((today - current).days + 1)]
        links = [build_direct_link(d) for d in selected_dates]
    elif args.all:
        links = get_all_galnet_links()
    elif args.update:
        last_date = find_latest_date()
        if not last_date:
            print("Nie znaleziono żadnych zapisanych artykułów.")
            return
        today_plus_1286 = add_years(datetime.today(), 1286)
        selected_dates = date_range(last_date, today_plus_1286.strftime("%Y-%m-%d"))
        links = [build_direct_link(d) for d in selected_dates]

    for link in links:
        try:
            save_articles_from_page(
                link,
                fix_missing_titles=args.fix_titles,
                skip_existing=not args.no_skip,
                selected_dates=selected_dates
            )
            if not args.fast:
                time.sleep(1)
        except Exception as e:
            print(f"Błąd przy {link}: {e}")

if __name__ == "__main__":
    main()
