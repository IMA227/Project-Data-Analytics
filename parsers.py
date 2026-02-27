import re
import json
from urllib.parse import unquote
from typing import List, Dict, Optional

from bs4 import BeautifulSoup, Tag


# Small helper: normalize whitespace and return None for empty strings
def clean_space(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    return re.sub(r"\s+", " ", s.strip()) or None


# Extract an integer like "1.234 Empfehlungen" from a text snippet
# Note: the keyword "Empfehlungen" is German because the source site is German.
def extract_number_from_text(text: str) -> Optional[int]:
    if not text:
        return None
    m = re.search(r"(\d[\d\.\s]*)\s*Empfehlungen", text, flags=re.I)
    if not m:
        return None
    num = m.group(1).replace(".", "").replace(" ", "")
    try:
        return int(num)
    except ValueError:
        return None


# Parse JSON-LD blocks and return the first Restaurant/LocalBusiness entry 
def parse_ld_json(soup: BeautifulSoup) -> Optional[dict]:
    for s in soup.select("script[type='application/ld+json']"):
        try:
            data = json.loads(s.string or s.get_text(strip=True) or "{}")
        except Exception:
            continue
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and item.get("@type") in ("Restaurant", "LocalBusiness"):
                    return item
        if isinstance(data, dict) and data.get("@type") in ("Restaurant", "LocalBusiness"):
            return data
    return None


# Find listing cards in search/listing pages 
def find_cards(soup: BeautifulSoup) -> List[Tag]:
    candidates = soup.select("div.bg-white.shadow-md")
    cards = []
    for div in candidates:
        a = div.select_one("h2 a[href*='/restaurant/']")
        if a:
            cards.append(div)
    if not cards:
        for a in soup.select("h2 a[href*='/restaurant/']"):
            parent_card = a.find_parent("div")
            if parent_card:
                cards.append(parent_card)
    out, seen = [], set()
    for c in cards:
        if id(c) not in seen:
            seen.add(id(c))
            out.append(c)
    return out


# Pick a "secondary" description from a listing card 
# Note: those keywords are German because the site is German.
def pick_listing_description(card: Tag) -> Optional[str]:
    for p in card.select("p.text-sm"):
        cls = " ".join(p.get("class", []))
        if "leading-relaxed" in cls and "font-normal" in cls and "text-left" in cls:
            t = p.get_text(" ", strip=True)
            if t and not re.search(r"\b(geöffnet|geschlossen|jetzt)\b", t, re.I):
                return clean_space(t)
    for p in card.select("p"):
        cls = " ".join(p.get("class", []))
        if "leading-relaxed" in cls:
            t = p.get_text(" ", strip=True)
            if t and not re.search(r"\b(geöffnet|geschlossen|jetzt|Empfehlungen)\b", t, re.I):
                if "," in t or len(t.split()) >= 3:
                    return clean_space(t)
    return None


# Price pattern: German format like "12,50" 
PRICE_RE = re.compile(r"(\d{1,3}(?:\.\d{3})*,\d{2})\s*€?")


# Extract "favourite dish" fields from a listing card
# Returns (name, price, ingredients). Many labels are German because the UI is German.
def extract_favourite_from_card(card: Tag) -> (Optional[str], Optional[str], Optional[str]):
    label = None
    for el in card.find_all(["span", "p", "div"]):
        t = el.get_text(" ", strip=True)
        if t and "Beliebtestes Gericht" in t:
            label = el
            break
    if not label:
        # Fallback path if the explicit label isn't found
        name = None
        upper_el = card.select_one(".uppercase")
        if upper_el:
            name = upper_el.get_text(" ", strip=True)
        price = None
        if name:
            m = PRICE_RE.search(name)
            if m:
                price = m.group(1)
                name = PRICE_RE.sub("", name).strip(" -–•|")
        ing = None
        for el in card.select(".text-ellipsis, .ellipsis"):
            tx = el.get_text(" ", strip=True)
            if tx and not PRICE_RE.search(tx):
                ing = tx
                break
        return clean_space(name), price, clean_space(ing)

    # If the "Beliebtestes Gericht" label exists, try to locate the associated dish box
    dish_box = label.find_next(
        lambda t: isinstance(t, Tag)
        and t.name == "div"
        and "shadow-md" in " ".join(t.get("class", []))
    )
    if not dish_box:
        dish_box = label.find_next("div")

    name = None
    left = dish_box.select_one(".float-left")
    if left:
        name = left.get_text(" ", strip=True)

    price = None
    right = dish_box.select_one(".float-right")
    if right:
        m = PRICE_RE.search(right.get_text(" ", strip=True))
        if m:
            price = m.group(1)

    ing = None
    after_box = dish_box.find_next(
        lambda t: isinstance(t, Tag)
        and (
            "text-ellipsis" in " ".join(t.get("class", []))
            or "ellipsis" in " ".join(t.get("class", []))
        )
    )
    if after_box:
        tx = after_box.get_text(" ", strip=True)
        if tx and not PRICE_RE.search(tx):
            ing = tx

    if name:
        name = PRICE_RE.sub("", name).strip(" -–•|")
    return clean_space(name), price, clean_space(ing)


# Parse one listing card into a normalized dictionary 
def parse_listing_card(card: Tag) -> Dict[str, Optional[str]]:
    data = {
        "city": "Aachen",
        "title": None,
        "restaurant_url": None,
        "desc_1": None,
        "star_count": None,
        "empfehlungen": None,
        "desc_2": None,
        "favourite_dish_name": None,
        "favourite_dish_price": None,
        "favourite_dish_ingredients": None,
        "page_url": None,
    }

    title_a = card.select_one("h2 a[href]")
    if title_a:
        data["title"] = clean_space(title_a.get_text(strip=True))
        href = (title_a.get("href") or "").strip()
        data["restaurant_url"] = href if href.startswith("http") else "https://www.speisekarte.de" + href

    # First short description line 
    desc_1 = None
    for p in card.select("p.text-sm, p.text-xs"):
        t = p.get_text(" ", strip=True)
        if not t:
            continue
        if re.search(r"\b(geöffnet|geschlossen|jetzt|Empfehlungen)\b", t, re.I):
            continue
        desc_1 = t
        break
    data["desc_1"] = clean_space(desc_1)

    # "Hearts" on the listing are used as a rough popularity indicator
    hearts = card.select("i.fa-heart")
    data["star_count"] = len(hearts) if hearts is not None else 0

    # Extract recommendation count ("Empfehlungen")
    emp_block = None
    for el in card.select("span, p, div"):
        txt = el.get_text(" ", strip=True)
        if "Empfehlungen" in txt:
            emp_block = txt
            break
    data["empfehlungen"] = extract_number_from_text(emp_block) if emp_block else None

    # Second description line 
    data["desc_2"] = pick_listing_description(card)

    # Favourite dish fields if present
    name, price, ing = extract_favourite_from_card(card)
    data["favourite_dish_name"] = name
    data["favourite_dish_price"] = price
    data["favourite_dish_ingredients"] = ing

    return data


# Used to detect opening hours lines that start with German weekdays
GERMAN_DAYS_RE = re.compile(r"^(Montag|Dienstag|Mittwoch|Donnerstag|Freitag|Samstag|Sonntag|Feiertag)", re.I)


# Find a heading where the text matches exactly (case-insensitive)
def find_heading_precise(soup: BeautifulSoup, label: str) -> Optional[Tag]:
    for tag in soup.find_all(["h2", "h3", "p", "div"]):
        t = tag.get_text(" ", strip=True)
        if t and t.strip().lower() == label.lower():
            return tag
    return None


# Extract rating value from the detail page (prefer specific CSS selector, then fallback to text search)
def extract_rating(soup: BeautifulSoup) -> Optional[str]:
    el = soup.select_one("span.text-4xl.font-bold.text-speisekarte-red-100")
    if el:
        return clean_space(el.get_text(strip=True)).replace(",", ".")
    txt = soup.get_text(" ", strip=True)
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*von\s*5\s*möglichen\s*Sternen", txt, flags=re.I)
    return m.group(1).replace(",", ".") if m else None


# Extract opening hours from the detail page.
# First try a structured block under the "Öffnungszeiten" heading, then fallback to JSON-LD.
def extract_opening_hours(soup: BeautifulSoup) -> Optional[str]:
    head = find_heading_precise(soup, "Öffnungszeiten")
    if head:
        sib = head.find_next_sibling()
        for _ in range(5):
            if isinstance(sib, Tag) and sib.name == "div":
                container = sib
                break
            sib = sib.find_next_sibling() if isinstance(sib, Tag) else None
        else:
            container = None

        if container:
            lines = []
            for el in container.find_all(["div", "p", "li", "span"], recursive=True):
                t = el.get_text(" ", strip=True)
                if not t:
                    continue
                if GERMAN_DAYS_RE.match(t) or "Ruhetag" in t:
                    lines.append(t)
            if lines:
                return " ".join(lines)

    ld = parse_ld_json(soup)
    if ld and isinstance(ld.get("openingHours"), list):
        try:
            return " ".join([clean_space(x) for x in ld["openingHours"] if x])
        except Exception:
            pass
    return None


# Extract services from the detail page 
def extract_services(soup: BeautifulSoup) -> Optional[str]:
    head = find_heading_precise(soup, "Service")
    if not head:
        return None
    sib = head.find_next_sibling()
    container = None
    for _ in range(5):
        if isinstance(sib, Tag) and sib.name == "div":
            container = sib
            break
        sib = sib.find_next_sibling() if isinstance(sib, Tag) else None
    if not container:
        return None
    chips = [clean_space(s.get_text(" ", strip=True)) for s in container.select("span")]
    chips = [c for c in chips if c]
    return " ".join(chips) if chips else None


# Extract address from either a map section, an address section, or JSON-LD
def extract_address(soup: BeautifulSoup) -> Optional[str]:
    dm = soup.select_one("#detail-map")
    if dm:
        p = dm.find("p")
        if p:
            return clean_space(p.get_text(" ", strip=True))
    head = find_heading_precise(soup, "Karte & Adresse") or find_heading_precise(soup, "Adresse")
    if head:
        p = head.find_next("p")
        if p:
            return clean_space(p.get_text(" ", strip=True))
    ld = parse_ld_json(soup)
    if ld and isinstance(ld.get("address"), dict):
        a = ld["address"]
        parts = [a.get("streetAddress"), a.get("postalCode"), a.get("addressLocality")]
        parts = [p for p in parts if p]
        if parts:
            return clean_space(", ".join(parts))
    return None


# Convert a URL path segment into a city name 
def city_name_from_path(path: str) -> str:
    slug = unquote(path.strip("/").split("/")[0])
    return slug.replace("-", " ").strip().title()