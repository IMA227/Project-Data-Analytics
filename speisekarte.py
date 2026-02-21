import string
from urllib.parse import urljoin

import scrapy
from bs4 import BeautifulSoup

from .parsers import (
    find_cards,
    parse_listing_card,
    city_name_from_path,
    extract_rating,
    extract_opening_hours,
    extract_services,
    extract_address,
)

BASE = "https://www.speisekarte.de"


class SpeisekarteSpider(scrapy.Spider):
    name = "speisekarte"
    allowed_domains = ["speisekarte.de"]

    custom_settings = {
        "ROBOTSTXT_OBEY": True,
        "DOWNLOAD_DELAY": 1.0,
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 1.0,
        "AUTOTHROTTLE_MAX_DELAY": 20.0,
        "RETRY_TIMES": 6,
        "CONCURRENT_REQUESTS": 8,
        "FEED_EXPORT_ENCODING": "utf-8",
        "LOG_LEVEL": "INFO",
    }

    def __init__(self, letters=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.letters = (letters or string.ascii_lowercase).lower()
        self._seen_city_paths = {ch: set() for ch in self.letters if ch.isalpha()}

    def start_requests(self):
        for ch in self.letters:
            if not ch.isalpha():
                continue
            url = f"{BASE}/staedteverzeichnis/{ch}"
            yield scrapy.Request(url, callback=self.parse_dir, meta={"letter": ch, "dir_page": 1})

    def parse_dir(self, response):
        letter = response.meta["letter"]
        dir_page = response.meta.get("dir_page", 1)

        soup = BeautifulSoup(response.text, "lxml")

        anchors = soup.select("div.grid a[href$='/restaurants'], a[href$='/restaurants']")
        new_count = 0

        for a in anchors:
            href = (a.get("href") or "").strip()
            if not (href.startswith("/") and href.endswith("/restaurants")):
                continue

            if href in self._seen_city_paths[letter]:
                continue

            self._seen_city_paths[letter].add(href)
            new_count += 1

            city_url = urljoin(BASE, href)
            yield scrapy.Request(
                city_url,
                callback=self.parse_city,
                meta={"city_path": href, "city_page": 1},
            )

        if new_count > 0:
            next_page = dir_page + 1
            next_url = f"{BASE}/staedteverzeichnis/{letter}?page={next_page}"
            yield scrapy.Request(next_url, callback=self.parse_dir, meta={"letter": letter, "dir_page": next_page})

    def parse_city(self, response):
        city_path = response.meta["city_path"]
        city_page = response.meta.get("city_page", 1)

        city_name = city_name_from_path(city_path)
        soup = BeautifulSoup(response.text, "lxml")

        cards = find_cards(soup)
        if not cards:
            return

        for card in cards:
            row = parse_listing_card(card)
            row["city"] = city_name
            row["page_url"] = response.url

            detail_url = row.get("restaurant_url")
            if detail_url:
                yield scrapy.Request(
                    detail_url,
                    callback=self.parse_detail,
                    meta={"row": row},
                )
            else:
                yield row

        next_city_page = city_page + 1
        base_city_url = urljoin(BASE, city_path)
        next_url = f"{base_city_url}?page={next_city_page}"
        yield scrapy.Request(
            next_url,
            callback=self.parse_city,
            meta={"city_path": city_path, "city_page": next_city_page},
        )

    def parse_detail(self, response):
        row = response.meta["row"]
        soup = BeautifulSoup(response.text, "lxml")

        row["rating_exact"] = extract_rating(soup)
        row["opening_hours"] = extract_opening_hours(soup)
        row["services"] = extract_services(soup)
        row["address"] = extract_address(soup)

        yield row

