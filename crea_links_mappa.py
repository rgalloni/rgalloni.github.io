#!/usr/bin/env python3
"""
Genera elenco luoghi da Itinerary/ con link Google Maps.
Output:
- Itinerary/elenco_luoghi_mappa.md
- Itinerary/elenco_luoghi_mappa.csv
"""

import csv
import re
from pathlib import Path
from urllib.parse import quote_plus

ITINERARY_DIR = Path("Itinerary")
OUTPUT_MD = ITINERARY_DIR / "elenco_luoghi_mappa.md"
OUTPUT_CSV = ITINERARY_DIR / "elenco_luoghi_mappa.csv"

# Termini da escludere (non sono luoghi)
SKIP_EXACT = {
    "Option A",
    "Option B",
    "Opzione A",
    "Opzione B",
    "Vibe",
    "Highlight",
    "Info",
    "What",
    "Theme",
    "Location",
    "Booking",
    "Transport",
    "Transfer",
    "Must-See",
    "Experience",
    "Recommendation",
    "Alternative",
    "Important",
    "Immigration",
    "Baggage Claim",
    "SIM Card",
    "Cash",
    "Water",
    "Dress Code",
    "Trasporti",
    "Biglietti",
    "Temperature",
    "Duration",
    "Drive",
    "Flight",
    "Sunset",
    "Disconnect",
    "Motion Sickness",
    "Electricity",
    "To Buy",
    "View",
    "Night Market",
    "Cena",
    "Pranzo",
    "Grab",
    "Bolt",
    "inDrive",
    "Lake",
    "Pier",
    "Day Trip from Krabi",
    "Old City Temples",
    "Railay Beach Exploration",
    "Sunset on Railay West",
    "Into the Forest",
    "Boat Ride to Paradise",
}

SKIP_CONTAINS = {
    "morning",
    "evening",
    "dinner",
    "lunch",
    "sleep",
    "check-in",
    "check out",
    "departure",
    "arrival",
    "return",
    "back at hotel",
    "schedule",
    "practical tips",
    "vibe 24enne",
    "opzione",
    "option",
    "come arrivare",
    "cosa mangiare",
    "l'idea",
    "cena",
    "pranzo",
    "breakfast",
    "afternoon",
    "late breakfast",
    "decision time",
    "magic hour",
    "check-in",
    "pick up",
}

PLACE_HINTS = {
    "wat",
    "beach",
    "road",
    "market",
    "night bazaar",
    "park",
    "bar",
    "rooftop",
    "cafe",
    "café",
    "island",
    "islands",
    "pier",
    "temple",
    "stadium",
    "mall",
    "center",
    "centre",
    "tower",
    "museum",
    "lake",
    "falls",
    "river",
    "cave",
    "street",
    "bay",
    "lagoon",
    "pool",
    "palace",
    "bridge",
    "station",
    "airport",
    "aeroporto",
    "district",
    "skywalk",
    "khao",
    "railay",
    "ao nang",
    "bangkok",
    "chiang",
    "krabi",
    "ayutthaya",
    "phuket",
    "phi phi",
    "yaowarat",
    "sukhumvit",
}

ALWAYS_INCLUDE = {
    "Nimman",
    "SookSiam",
    "Rajadamnern Stadium",
    "Jay Fai",
    "Jeh O Chula",
    "Thipsamai",
    "Khao Sok",
    "Khao Lak",
    "Ao Nang",
    "Railay",
    "Chiang Mai",
    "Chiang Rai",
    "Ayutthaya",
    "Bangkok",
    "Krabi",
    "Phuket",
}


def clean_place(raw: str) -> str:
    text = raw.strip()
    text = re.sub(r"\s+", " ", text)
    text = text.strip("-–;,. ")

    # Rimuovi prezzo finale es. "($$)"
    text = re.sub(r"\s*\([\$\?]+\)$", "", text).strip()

    return text


def normalize_candidate(raw: str) -> str:
    text = clean_place(raw)

    transformations = [
        r"^(?:Transfer|Flight|Return|Back to|Drive|Arrival|Arrivo|Ritorno|Viaggio)\s+(?:to|a|verso)\s+(.+)$",
        r"^(?:Touchdown at)\s+(.+)$",
        r"^(?:Cena|Pranzo|Dinner|Lunch)\s+(?:a|at|in)\s+(.+)$",
        r"^(?:Check-in)\s*\(([^)]+)\)$",
    ]

    for pattern in transformations:
        m = re.match(pattern, text, flags=re.IGNORECASE)
        if m:
            text = clean_place(m.group(1))
            break

    return text


def looks_like_place(name: str) -> bool:
    if name in ALWAYS_INCLUDE:
        return True

    lower = name.lower()

    if any(hint in lower for hint in PLACE_HINTS):
        return True

    if re.search(r"\([A-Z]{3}\)", name):
        return True

    return False


def is_valid_place(name: str, source: str = "generic") -> bool:
    if not name:
        return False

    if name.endswith(":"):
        return False

    if name in SKIP_EXACT:
        return False

    lower = name.lower()
    if any(token in lower for token in SKIP_CONTAINS):
        return False

    # Scarta orari
    if re.match(r"^\d{1,2}:\d{2}", name):
        return False

    if len(name) < 3:
        return False

    # Per gli item con prezzo (liste opzioni) accettiamo più libertà
    # perché sono quasi sempre luoghi reali.
    if source == "priced":
        return True

    if not looks_like_place(name):
        return False

    return True


def day_title_from_file(file_path: Path, content: str) -> str:
    for line in content.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return file_path.stem


def extract_places_from_content(content: str):
    places = []

    for line in content.splitlines():
        stripped = line.strip()

        # Estrai città/luoghi dalla riga Location
        loc_match = re.match(r"^\*\*Location:\*\*\s*(.+)$", stripped)
        if loc_match:
            loc_text = loc_match.group(1)
            chunks = re.split(r"→|,", loc_text)
            for chunk in chunks:
                candidate = normalize_candidate(chunk)
                if is_valid_place(candidate, source="location"):
                    places.append(candidate)

                # Se c'è una slash (es. Ao Nang / Railay), estrai le due parti
                if "/" in candidate:
                    # Caso "Krabi (Ao Nang / Railay)"
                    inner = re.search(r"\(([^)]+)\)", candidate)
                    if inner:
                        outer = normalize_candidate(re.sub(r"\([^)]*\)", "", candidate))
                        if is_valid_place(outer, source="location"):
                            places.append(outer)
                        for sub in inner.group(1).split("/"):
                            sub_candidate = normalize_candidate(sub)
                            if is_valid_place(sub_candidate, source="location"):
                                places.append(sub_candidate)
                    else:
                        for sub in candidate.split("/"):
                            sub_candidate = normalize_candidate(sub)
                            if is_valid_place(sub_candidate, source="location"):
                                places.append(sub_candidate)

            parenthetical = re.findall(r"\(([^)]+)\)", loc_text)
            for chunk in parenthetical:
                candidate = normalize_candidate(chunk)
                if is_valid_place(candidate, source="location"):
                    places.append(candidate)

        # Estrai luoghi da righe orarie tipo "**10:00 – Wat Arun ...**"
        timed = re.findall(r"^\*\*\d{1,2}:\d{2}\s*[–-]\s*([^*]+)\*\*$", stripped)
        for part in timed:
            candidate = normalize_candidate(part)
            if is_valid_place(candidate, source="timed"):
                places.append(candidate)

        # Bullet top-level con item luogo + prezzo, es. * **Tichuca** ($$$)
        priced_item = re.findall(r"^\*\s+\*\*([^*]+)\*\*\s+\((?:\$+|\?)\)", line)
        for part in priced_item:
            candidate = normalize_candidate(part)
            if is_valid_place(candidate, source="priced"):
                places.append(candidate)

        # Altri bold su bullet top-level (non sub-bullet):
        # es. * ... **The Hilltop** ... **Lae Lay Grill**
        if line.startswith("*") and "**" in line:
            inline_bold = re.findall(r"\*\*([^*]+)\*\*", line)
            for part in inline_bold:
                candidate = normalize_candidate(part)
                if is_valid_place(candidate, source="inline"):
                    places.append(candidate)

    # Dedup mantenendo ordine
    unique_places = list(dict.fromkeys(places))
    return unique_places


def collect_places_by_day():
    if not ITINERARY_DIR.exists():
        raise FileNotFoundError(f"Directory non trovata: {ITINERARY_DIR}")

    day_files = sorted(
        p
        for p in ITINERARY_DIR.glob("*.md")
        if re.match(r"^\d{2}_", p.name) and not p.name.startswith("00_")
    )

    result = []
    for file_path in day_files:
        content = file_path.read_text(encoding="utf-8")
        day_title = day_title_from_file(file_path, content)
        places = extract_places_from_content(content)
        result.append((day_title, places, file_path.name))

    return result


def write_markdown(data):
    base_url = "https://www.google.com/maps/search/?api=1&query="
    with OUTPUT_MD.open("w", encoding="utf-8") as f:
        f.write("# Elenco Luoghi Itinerario con Link a Google Maps\n\n")
        f.write("Generato automaticamente dai file in `Itinerary/`.\n\n")

        total = 0
        for day_title, places, file_name in data:
            f.write(f"## {day_title}\n")
            f.write(f"Fonte: `{file_name}`\n\n")
            if not places:
                f.write("- Nessun luogo estratto\n\n")
                continue

            for place in places:
                link = f"{base_url}{quote_plus(place)}"
                f.write(f"- [{place}]({link})\n")
                total += 1
            f.write("\n")

    return total


def write_csv(data):
    base_url = "https://www.google.com/maps/search/?api=1&query="
    with OUTPUT_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["day", "place", "google_maps_url", "source_file"])

        rows = 0
        for day_title, places, file_name in data:
            for place in places:
                writer.writerow(
                    [
                        day_title,
                        place,
                        f"{base_url}{quote_plus(place)}",
                        file_name,
                    ]
                )
                rows += 1
    return rows


def main():
    data = collect_places_by_day()
    total_md = write_markdown(data)
    total_csv = write_csv(data)

    print(f"✅ Creato: {OUTPUT_MD}")
    print(f"✅ Creato: {OUTPUT_CSV}")
    print(f"📍 Luoghi estratti: {total_md} (MD) / {total_csv} (CSV)")


if __name__ == "__main__":
    main()
