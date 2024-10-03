import requests
import os
import csv
import sqlite3
from datetime import datetime

class MangasIoScraper:
    def __init__(self, db_name):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:99.0) Gecko/20100101 Firefox/99.0",
            "Accept": "*/*",
            "Accept-Language": "fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3",
            "Content-Type": "application/json; charset=utf-8",
            "Origin": "https://www.mangas.io",
            "DNT": "1",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
        }
        self.db_name = db_name
        self.create_database()

    def create_database(self):
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS chapters
                     (chapter_url TEXT PRIMARY KEY, scraped_date TEXT)''')
        conn.commit()
        conn.close()

    def get_chapter_list(self, slug, outputfile):
        json_data = {
            "operationName": "GetManga",
            "variables": {
                "slug": slug,
            },
            "query": "query GetManga($slug: String) {\n  manga(slug: $slug) {\n    _id\n    slug\n    title\n    description\n    releaseDate\n    age\n    trailer\n    isOngoing\n    alternativeTitles\n    chapterCount\n    ctas {\n      url\n      image {\n        url\n        __typename\n      }\n      __typename\n    }\n    bannerMobile: banner(target: MOBILE) {\n      url\n      __typename\n    }\n    banner {\n      url\n      __typename\n    }\n    categories {\n      label\n      level\n      __typename\n    }\n    authors {\n      _id\n      name\n      __typename\n    }\n    thumbnail {\n      url\n      __typename\n    }\n    publishers {\n      publisher {\n        _id\n        name\n        countryCode\n        logo {\n          url\n          __typename\n        }\n        __typename\n      }\n      releaseDate\n      __typename\n    }\n    volumes {\n      _id\n      title\n      ean13\n      label\n      description\n      number\n      publicationDate\n      releaseDate\n      thumbnail {\n        url\n        pos_x\n        pos_y\n        __typename\n      }\n      chapterStart\n      chapterEnd\n      chapters {\n        _id\n        number\n        title\n        isRead\n        isBonus\n        isSeparator\n        access\n        publicationDate\n        releaseDate\n        pageCount\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n}",
        }
        response = requests.post(
            "https://api.mangas.io/api", headers=self.headers, json=json_data, allow_redirects=True
        )
        if response.status_code != 200:
            print(f"Error: {response.status_code}")
            return False
        data = response.json()
        new_chapters = False
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        current_date = datetime.now().strftime("%Y-%m-%d")

        with open(outputfile, "a") as f:
            for volume in data["data"]["manga"]["volumes"]:
                for chapter in volume["chapters"]:
                    chapter_url = f'https://www.mangas.io/lire/{slug}/{chapter["number"]}/1'
                    c.execute("SELECT * FROM chapters WHERE chapter_url=?", (chapter_url,))
                    result = c.fetchone()
                    if result is None:
                        new_chapters = True  # Set flag to True if a new chapter is found
                        c.execute("INSERT INTO chapters VALUES (?, ?)", (chapter_url, current_date))
                        f.write(f'{chapter_url}\n')
        if new_chapters:
            print(f"New chapter URLs appended to {outputfile}, form {slug}")
        else:
            # If no new chapters were found, clear the output file
            print(f"No new chapters found , form {slug}. {outputfile} has been cleared.")

        conn.commit()
        conn.close()

        return data["data"]["manga"]["isOngoing"]

if __name__ == "__main__":
    outputfile = "nouveau.txt"
    dbname = "mangasio.db"
    csvfile = "listeserie.csv"

    scraper = MangasIoScraper(dbname)

    updated_rows = []
    with open(csvfile, mode='r') as infile:
        reader = csv.reader(infile)
        next(reader)  # Skip header row
        for row in reader:
            url, ongoing = row
            if ongoing.lower() == 'true':
                slug = url.split("/")[-2]
                isOngoing = scraper.get_chapter_list(slug, outputfile)
                updated_rows.append([url, isOngoing])
                if isOngoing != 'true':
                    print("-----------------------------------------------------------",slug)
            else:
                updated_rows.append([url, ongoing])

    with open(csvfile, mode='w', newline='') as outfile:
        writer = csv.writer(outfile)
        writer.writerow(['url', 'ongoing'])
        writer.writerows(updated_rows)
