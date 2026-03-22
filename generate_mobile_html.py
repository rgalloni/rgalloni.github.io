import json
import os
import re
from pathlib import Path

import markdown


def clean_openxml_markdown(text: str) -> str:
    if not text:
        return text

    # Remove pandoc/openxml fenced blocks
    text = re.sub(r"```\{=openxml\}.*?```", "", text, flags=re.DOTALL)

    # Remove raw OpenXML page break snippets if present
    text = re.sub(r"<w:p>\s*<w:r>\s*<w:br\s+w:type=\"page\"\s*/>\s*</w:r>\s*</w:p>", "", text)

    # Remove generic fenced code blocks containing page-break OpenXML
    text = re.sub(r"```[\s\S]*?<w:br\s+w:type=\"page\"\s*/>[\s\S]*?```", "", text)

    # Remove already-escaped HTML snippet if it was pasted into markdown
    text = re.sub(
        r"<pre><code>&lt;w:p&gt;&lt;w:r&gt;&lt;w:br\s+w:type=\"page\"/?&gt;&lt;/w:r&gt;&lt;/w:p&gt;</code></pre>",
        "",
        text,
    )

    return text.strip()


def process_html_chunk(html_content: str) -> str:
    html_content = re.sub(r"(</h[1-6]>)\s*<br\s*/?>", r"\1", html_content)

    html_content = re.sub(
        r"\[\[IMG-FULL:(.*?)\]\]",
        r'<div class="img-wrapper"><img src="images/\1" class="full-image" alt="\1"></div>',
        html_content,
    )
    html_content = re.sub(
        r"\[\[IMG:(.*?)\]\]",
        r'<div class="img-wrapper"><img src="images/\1" class="full-image" alt="\1"></div>',
        html_content,
    )
    html_content = re.sub(r"\[\[ICON:(.*?)\]\]", r'<i class="\1 section-icon"></i>', html_content)

    html_content = re.sub(r"(<br\s*/?>\s*)+(<h[1-6]>)", r"\n\2", html_content)

    lines = html_content.split("\n")
    processed_lines = []

    warning_pattern = re.compile(r"<(p|li)>(.*?(?:Warning|Attention|Nightmare|Scam|Never|Problem).*?)<\/\1>", re.IGNORECASE)
    tip_pattern = re.compile(r"<(p|li)>(.*?(?:Tip|Advice|Essential|Golden rule|Note|Solution|Card).*?)<\/\1>", re.IGNORECASE)

    for line in lines:
        if warning_pattern.search(line):
            line = warning_pattern.sub(
                r'<div class="alert-box warning-box"><i class="fa-solid fa-triangle-exclamation alert-icon"></i><div><strong>Warning:</strong> \2</div></div>',
                line,
            )
        elif tip_pattern.search(line):
            line = tip_pattern.sub(
                r'<div class="alert-box tip-box"><i class="fa-solid fa-lightbulb alert-icon"></i><div><strong>Tip:</strong> \2</div></div>',
                line,
            )
        processed_lines.append(line)

    html_content = "\n".join(processed_lines)
    chunks = re.split(r"<hr\s*/?>", html_content)
    wrapped_chunks = [f'<div class="card">{chunk.strip()}</div>' for chunk in chunks if chunk.strip()]
    return "\n".join(wrapped_chunks)


def section_markdown(section: dict, chapter: dict, itinerary: dict) -> str:
    section_type = section.get("type")

    if section_type == "intro":
        body = clean_openxml_markdown(itinerary.get("context_markdown", ""))
        return f"# Chapter 1: {chapter['title']}\n\n{body}\n"

    if section_type == "day":
        label = section.get("label", "Day")
        date_label = section.get("date_label", "")
        day_title = section.get("title", "")
        overview = clean_openxml_markdown(itinerary.get("overview_markdown", ""))
        schedule = clean_openxml_markdown(itinerary.get("schedule_markdown", ""))
        schedule_items = itinerary.get("schedule_items", [])
        context = clean_openxml_markdown(itinerary.get("context_markdown", ""))

        parts = [f"# {label}: {date_label} — {day_title}"]

        if overview:
            parts.extend(["", "## [[ICON:fa-solid fa-compass]] Daily Overview", "", overview])
        if schedule_items:
            schedule_lines = []
            for item in schedule_items:
                time = (item.get("time") or "").strip()
                title = (item.get("title") or "").strip()
                details = item.get("details") or []

                if time:
                    schedule_lines.append(f"- **{time}**")
                else:
                    schedule_lines.append("-")

                if title:
                    schedule_lines.append(f"    - **{title}**")

                for detail in details:
                    schedule_lines.append(f"    - {detail}")

            parts.extend(["", "## [[ICON:fa-regular fa-clock]] Schedule", "", "\n".join(schedule_lines)])
        elif schedule:
            parts.extend(["", "## [[ICON:fa-regular fa-clock]] Schedule", "", schedule])
        if context:
            parts.extend(["", "## [[ICON:fa-solid fa-map-location-dot]] Detailed Context", "", context])

        return "\n".join(parts).strip() + "\n"

    body = clean_openxml_markdown(itinerary.get("context_markdown", ""))
    return f"# {section.get('label', 'Section')}\n\n{body}\n"


def infer_booking_type(item: dict) -> str:
    explicit = (item.get("booking_type") or "").strip().lower()
    if explicit:
        return explicit

    text = " ".join(
        [
            item.get("title", ""),
            item.get("time", ""),
            item.get("note", ""),
        ]
    ).lower()

    if "flight" in text or "arrival" in text or "departure" in text or "tk" in text:
        return "flight"
    if "hotel" in text or "apart" in text or "reservation" in text or "stay" in text:
        return "hotel"
    return "activity"


def infer_hotel_action(item: dict) -> str:
    explicit = (item.get("overview_hotel_action") or "").strip().lower()
    if explicit:
        return explicit

    text = " ".join([item.get("title", ""), item.get("time", ""), item.get("note", "")]).lower()
    if "check-in" in text or "check in" in text:
        return "checkin"
    if "check-out" in text or "check out" in text:
        return "checkout"
    return "same"


def include_in_daily_overview(item: dict, section: dict) -> bool:
    if item.get("show_in_daily_overview") is False:
        return False
    scope = (item.get("overview_section_id") or "").strip()
    if scope and scope != section.get("id"):
        return False

    event_date = (item.get("event_date") or "").strip()
    section_date = (section.get("date") or "").strip()
    if event_date and section_date and event_date != section_date:
        return False
    return True


def render_mobile_pages(data_dir: Path, out_dir: Path) -> None:
    languages = ["en", "it", "ar"]
    data_by_lang = {}
    for lang in languages:
        data_by_lang[lang] = {
            "sections": json.loads((data_dir / f"mobile_sections.{lang}.json").read_text(encoding="utf-8")),
            "itineraries": json.loads((data_dir / f"mobile_itineraries.{lang}.json").read_text(encoding="utf-8")),
            "activities": json.loads((data_dir / f"mobile_activities.{lang}.json").read_text(encoding="utf-8")),
            "bookings": json.loads((data_dir / f"mobile_bookings.{lang}.json").read_text(encoding="utf-8")),
        }

    language_labels = {
        "en": "English",
        "it": "Italiano",
        "ar": "العربية",
    }

    ui_labels = {
        "en": {
            "tab_itinerary": "Itinerary",
            "tab_context": "Context",
            "tab_activities": "Activities",
            "tab_bookings": "Bookings",
            "no_bookings": "No bookings added for this section yet.",
            "no_activities": "No activities or restaurants saved yet.",
            "booking_flight": "Flight",
            "booking_hotel": "Hotel",
            "booking_activity": "Activity",
            "booking_transport": "Transport",
            "booking_default": "Booking",
            "label_flights_today": "Flights Today",
            "label_hotel": "Hotel",
            "label_checkin": "Check-in",
            "label_checkout": "Check-out",
        },
        "it": {
            "tab_itinerary": "Itinerario",
            "tab_context": "Contesto",
            "tab_activities": "Attività",
            "tab_bookings": "Prenotazioni",
            "no_bookings": "Nessuna prenotazione aggiunta per questa sezione.",
            "no_activities": "Nessuna attività o ristorante salvato.",
            "booking_flight": "Volo",
            "booking_hotel": "Hotel",
            "booking_activity": "Attività",
            "booking_transport": "Trasporto",
            "booking_default": "Prenotazione",
            "label_flights_today": "Voli di oggi",
            "label_hotel": "Hotel",
            "label_checkin": "Check-in",
            "label_checkout": "Check-out",
        },
        "ar": {
            "tab_itinerary": "خط السير",
            "tab_context": "السياق",
            "tab_activities": "الأنشطة",
            "tab_bookings": "الحجوزات",
            "no_bookings": "لا توجد حجوزات مضافة لهذا القسم بعد.",
            "no_activities": "لا توجد أنشطة أو مطاعم محفوظة بعد.",
            "booking_flight": "رحلة",
            "booking_hotel": "فندق",
            "booking_activity": "نشاط",
            "booking_transport": "نقل",
            "booking_default": "حجز",
            "label_flights_today": "رحلات اليوم",
            "label_hotel": "الفندق",
            "label_checkin": "تسجيل وصول",
            "label_checkout": "تسجيل مغادرة",
        },
    }

    css = """
    <link rel="stylesheet" href="assets/fontawesome/css/all.min.css">
    <style>
        :root {
            --bg-color: #f0f2f5;
            --card-bg: #ffffff;
            --text-main: #1c1e21;
            --text-muted: #65676b;
            --primary: #1877f2;
            --divider: #e4e6eb;
        }
        * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            color: var(--text-main);
            background-color: var(--bg-color);
            line-height: 1.6;
            margin: 0;
            padding: 0;
            padding-top: 60px;
            padding-bottom: 90px;
        }
        header {
            position: fixed; top: 0; left: 0; right: 0; height: 60px;
            background: var(--card-bg);
            display: flex; align-items: center; justify-content: center;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            z-index: 1000;
            padding: 0 15px;
        }
        .header-controls { width: 100%; max-width: 560px; display: flex; align-items: center; gap: 8px; }
        .day-switcher { position: relative; flex: 1; min-width: 0; }
        .day-switcher-btn {
            width: 100%; border: 1px solid #d8dee6; border-radius: 12px;
            background: #f6f9ff; color: var(--text-main);
            padding: 8px 14px; cursor: pointer;
            display: flex; align-items: center; justify-content: space-between;
            text-align: left;
        }
        .day-switcher-meta { display: flex; flex-direction: column; }
        .day-switcher-chapter { font-size: 0.72rem; color: #7b8896; font-weight: 600; }
        .day-switcher-current { font-size: 0.98rem; color: var(--primary); font-weight: 700; margin-top: 1px; }
        .day-switcher-icon { color: var(--primary); transition: transform 0.2s ease; }
        .day-switcher.open .day-switcher-icon { transform: rotate(180deg); }
        .day-switcher-menu {
            position: absolute; left: 0; right: 0; top: calc(100% + 8px);
            background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px;
            box-shadow: 0 10px 24px rgba(17, 24, 39, 0.14);
            overflow: hidden; display: none; z-index: 1100;
        }
        .day-switcher.open .day-switcher-menu { display: block; }
        .day-switcher-label {
            padding: 10px 14px; font-size: 0.74rem; font-weight: 700;
            color: #7b8896; background: #f8fafc; border-bottom: 1px solid #eef2f7;
        }
        .day-option {
            width: 100%; border: 0; background: #fff; text-align: left;
            padding: 11px 14px 11px 28px; font-family: 'Inter', sans-serif;
            font-size: 0.95rem; color: #334155; cursor: pointer;
        }
        .day-option + .day-option { border-top: 1px solid #f1f5f9; }
        .day-option:hover { background: #f8fbff; }
        .day-option.active { color: var(--primary); font-weight: 700; background: #eef5ff; }

        .lang-switcher { position: relative; }
        .lang-btn {
            height: 42px;
            min-width: 66px;
            border: 1px solid #d8dee6;
            border-radius: 12px;
            background: #f6f9ff;
            color: #334155;
            font-weight: 700;
            font-size: 0.85rem;
            padding: 0 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            cursor: pointer;
        }
        .lang-switcher-menu {
            position: absolute;
            top: calc(100% + 8px);
            right: 0;
            min-width: 150px;
            background: #fff;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            box-shadow: 0 10px 24px rgba(17,24,39,0.14);
            overflow: hidden;
            display: none;
            z-index: 1100;
        }
        .lang-switcher.open .lang-switcher-menu { display: block; }
        .lang-option {
            display: block;
            width: 100%;
            border: 0;
            background: #fff;
            text-align: left;
            padding: 10px 12px;
            font-size: 0.9rem;
            color: #334155;
            cursor: pointer;
        }
        .lang-option + .lang-option { border-top: 1px solid #f1f5f9; }
        .lang-option.active { background: #eef5ff; color: #1d4ed8; font-weight: 700; }

        [dir="rtl"] body { font-family: 'Segoe UI', Tahoma, Arial, sans-serif; }
        [dir="rtl"] .header-controls { direction: rtl; }
        [dir="rtl"] .day-switcher-btn,
        [dir="rtl"] .day-option,
        [dir="rtl"] .lang-option { text-align: right; }
        [dir="rtl"] summary {
            padding-left: 44px;
            padding-right: 18px;
        }
        [dir="rtl"] summary::after {
            left: 16px;
            right: auto;
        }
        [dir="rtl"] .summary-thumb {
            margin: -14px -18px -14px 0;
            border-right: 0;
            border-left: 1px solid #dbe4ff;
            order: 2;
        }
        [dir="rtl"] .summary-text {
            order: 1;
            text-align: right;
        }

        .container { padding: 15px; max-width: 600px; margin: 0 auto; }
        h1, h2, h3, h4 { color: var(--text-main); margin-top: 1rem; margin-bottom: 0.5rem; font-weight: 700; line-height: 1.3; }
        h1 { font-size: 1.6rem; border-bottom: 2px solid var(--primary); padding-bottom: 10px; margin-top: 0; }
        h2 { font-size: 1.3rem; color: var(--primary); margin-top: 1.5rem; }
        h3 { font-size: 1.15rem; color: #d35400; }
        p, li { font-size: 1rem; color: var(--text-muted); }
        ul { padding-left: 20px; margin-bottom: 1rem; }
        li { margin-bottom: 8px; }

        .card {
            background: var(--card-bg); border-radius: 12px; padding: 16px;
            margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            border: 1px solid rgba(0,0,0,0.04);
        }
        .card > h1:first-child,
        .card > h2:first-child,
        .card > h3:first-child {
            margin-top: 0;
        }
        .card:first-child h1 {
            border: none; text-align: center; font-size: 1.8rem;
            background: linear-gradient(90deg, #1877f2, #e74c3c);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .day-hero { text-align: center; margin-bottom: 8px; }
        .day-hero-kicker { font-size: 1.25rem; font-weight: 800; color: var(--primary); line-height: 1.2; }
        .day-hero-date { font-size: 0.92rem; color: #64748b; margin-top: 2px; line-height: 1.35; }
        .day-hero-title {
            margin: 10px 0 4px;
            font-size: 1.8rem;
            line-height: 1.2;
            color: #0f172a;
            font-weight: 800;
            border: none;
            background: none;
            -webkit-text-fill-color: initial;
        }

        .intro-hero { text-align: center; margin-bottom: 8px; }
        .intro-hero-kicker { font-size: 1.05rem; font-weight: 800; color: var(--primary); line-height: 1.2; }
        .intro-hero-title {
            margin: 8px 0 2px;
            font-size: 1.85rem;
            line-height: 1.2;
            color: #0f172a;
            font-weight: 800;
            border: none;
            background: none;
            -webkit-text-fill-color: initial;
        }

        .img-wrapper { margin: 15px -20px; overflow: hidden; display: flex; justify-content: center; }
        .full-image { width: 100%; height: auto; display: block; border-top: 1px solid var(--divider); border-bottom: 1px solid var(--divider); }
        .section-icon { margin-right: 8px; color: var(--primary); }
        h3 .section-icon { color: #d35400; }

        .alert-box { display: flex; padding: 15px; border-radius: 12px; margin: 15px 0; font-size: 0.95rem; line-height: 1.5; }
        .warning-box { background-color: #fff3cd; color: #856404; }
        .tip-box { background-color: #e8f4fd; color: #0c5460; }
        .alert-icon { font-size: 1.2rem; margin-right: 12px; margin-top: 2px; }

        .booking-item-title { margin: 0; color: #1f2937; font-weight: 700; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
        .booking-item-icon { color: #3b82f6; width: 18px; text-align: center; }
        .booking-type {
            display: inline-block; font-size: 0.72rem; font-weight: 700;
            color: #475569; background: #eef2ff; border: 1px solid #dbe4ff;
            border-radius: 999px; padding: 2px 8px;
        }

        .daily-overview-meta {
            margin: 10px 0 18px;
            border: 1px solid #dbe7ff;
            background: #f5f9ff;
            border-radius: 12px;
            padding: 12px;
        }
        .overview-meta-item { display: flex; align-items: flex-start; gap: 10px; }
        .overview-meta-item + .overview-meta-item { margin-top: 8px; }
        .overview-meta-item i { color: #2563eb; margin-top: 2px; }
        .overview-meta-label { font-size: 0.78rem; font-weight: 700; color: #334155; text-transform: uppercase; letter-spacing: 0.04em; }
        .overview-meta-value { font-size: 0.92rem; color: #1e293b; margin-top: 1px; }

        details { background: #ffffff; border: 1px solid var(--divider); margin-bottom: -1px; border-radius: 0; overflow: hidden; }
        details:first-of-type { border-top-left-radius: 12px; border-top-right-radius: 12px; }
        details:last-of-type { border-bottom-left-radius: 12px; border-bottom-right-radius: 12px; margin-bottom: 20px; }
        summary { padding: 14px 18px; padding-right: 44px; font-weight: 600; font-size: 1rem; color: var(--text-main); cursor: pointer; list-style: none; display: flex; align-items: center; justify-content: flex-start; background: #ffffff; transition: background 0.2s ease; gap: 10px; position: relative; }
        summary::-webkit-details-marker { display: none; }
        summary::after { content: '▾'; color: #94a3b8; font-size: 1rem; line-height: 1; transition: transform 0.3s ease; position: absolute; right: 16px; top: 50%; transform: translateY(-50%); }
        details[open] summary::after { transform: translateY(-50%) rotate(180deg); color: var(--primary); }
        details[open] summary { border-bottom: 1px solid var(--divider); color: var(--primary); background: #f8f9fa; }
        .details-content { padding: 15px; }
        .summary-thumb {
            width: 74px;
            height: 72px;
            flex: 0 0 74px;
            object-fit: cover;
            margin: -14px 0 -14px -18px;
            border-radius: 0;
            border: 0;
            border-right: 1px solid #dbe4ff;
        }
        .summary-text {
            display: block;
            min-width: 0;
            line-height: 1.3;
        }

        .schedule-list { list-style: none; padding: 0; margin: 0; }
        .schedule-list > li { margin: 0 0 14px; padding: 0; }
        .schedule-item {
            border: 1px solid #e6edf8;
            border-radius: 12px;
            background: #fbfdff;
            padding: 10px 12px;
        }
        .schedule-time {
            color: #1d4ed8;
            font-weight: 800;
            font-size: 0.92rem;
            line-height: 1.2;
            margin-bottom: 6px;
        }
        .schedule-title {
            color: #0f172a;
            font-weight: 700;
            font-size: 0.98rem;
            line-height: 1.35;
        }
        .schedule-details {
            list-style: none;
            margin: 8px 0 0;
            padding: 0 0 0 14px;
            border-left: 2px solid #dbe4ff;
        }
        .schedule-details li {
            margin: 0 0 10px;
            padding: 0 0 0 12px;
            position: relative;
        }
        .schedule-details li:last-child { margin-bottom: 0; }
        .schedule-details li::before {
            content: "";
            position: absolute;
            left: -19px;
            top: 0.56em;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #93c5fd;
            box-shadow: 0 0 0 1px #93c5fd;
        }

        .bottom-nav {
            position: fixed; bottom: 0; left: 0; right: 0; height: 70px;
            background: #ffffff; display: flex; justify-content: space-around; align-items: center;
            box-shadow: 0 -2px 10px rgba(0,0,0,0.05); z-index: 1000;
            padding-bottom: env(safe-area-inset-bottom);
        }
        .nav-item {
            display: flex; flex-direction: column; align-items: center; justify-content: center;
            color: var(--text-muted); text-decoration: none; font-size: 0.75rem;
            flex: 1; height: 100%; cursor: pointer; transition: color 0.2s;
            border: none; background: none; font-family: 'Inter', sans-serif; padding: 0;
        }
        .nav-item.active { color: var(--primary); }
        .nav-item i { font-size: 1.4rem; margin-bottom: 4px; transition: transform 0.2s; }
        .nav-item:active i { transform: scale(0.9); }

        .tab-pane { display: none; animation: fadeIn 0.3s ease; }
        .tab-pane.active { display: block; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px);} to { opacity: 1; transform: translateY(0);} }

        #image-viewer {
            position: fixed; top: 0; left: 0; right: 0; bottom: 0;
            background: #000; z-index: 2000; opacity: 0; visibility: hidden;
            transition: opacity 0.3s ease; display: flex; align-items: center; justify-content: center;
        }
        #image-viewer.active { opacity: 1; visibility: visible; }
        #viewer-container { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; overflow: hidden; touch-action: none; }
        #viewer-image { max-width: 100%; max-height: 100vh; }
        #close-viewer {
            position: absolute; top: 20px; right: 20px; color: white; font-size: 24px;
            background: rgba(255,255,255,0.2); border: none; cursor: pointer; z-index: 2001;
            width: 44px; height: 44px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
        }
    </style>
    """

    js = """
    <script>
        document.addEventListener("DOMContentLoaded", function() {
            const pageConfig = __PAGE_CONFIG__;
            const defaultTab = pageConfig.default_tab || 'itinerary';
            const contextOnlyMode = pageConfig.content_mode === 'context_only';
            const labels = pageConfig.ui_labels || {};

            const daySwitcher = document.getElementById('day-switcher');
            const daySwitcherBtn = document.getElementById('day-switcher-btn');
            const dayOptions = document.querySelectorAll('.day-option');
            const langSwitcher = document.getElementById('lang-switcher');
            const langBtn = document.getElementById('lang-btn');
            const langOptions = document.querySelectorAll('.lang-option');

            daySwitcherBtn.addEventListener('click', () => daySwitcher.classList.toggle('open'));
            dayOptions.forEach(option => {
                option.addEventListener('click', () => {
                    window.location.href = option.dataset.href;
                });
            });
            document.addEventListener('click', (event) => {
                if (!daySwitcher.contains(event.target)) daySwitcher.classList.remove('open');
                if (langSwitcher && !langSwitcher.contains(event.target)) langSwitcher.classList.remove('open');
            });

            if (langBtn) {
                langBtn.addEventListener('click', () => langSwitcher.classList.toggle('open'));
            }
            langOptions.forEach(option => {
                option.addEventListener('click', () => {
                    window.location.href = option.dataset.href;
                });
            });

            const firstCard = document.querySelector('.container .card');
            const firstH1 = firstCard ? firstCard.querySelector('h1') : null;
            if (firstH1) {
                const raw = firstH1.textContent.trim();
                const dayMatch = raw.match(/^DAY\\s+(\\d+):\\s*(.*?)\\s*[—-]\\s*(.*)$/i);
                if (dayMatch) {
                    const hero = document.createElement('div');
                    hero.className = 'day-hero';
                    hero.innerHTML = `
                        <div class="day-hero-kicker">Day ${dayMatch[1]}</div>
                        <div class="day-hero-date">${dayMatch[2].trim()}</div>
                        <h1 class="day-hero-title">${dayMatch[3].trim()}</h1>
                    `;
                    firstH1.replaceWith(hero);
                } else {
                    const chapterMatch = raw.match(/^Chapter\\s+(\\d+):\\s*(.*)$/i);
                    if (chapterMatch) {
                        const introHero = document.createElement('div');
                        introHero.className = 'intro-hero';
                        introHero.innerHTML = `
                            <div class="intro-hero-kicker">Chapter ${chapterMatch[1]}</div>
                            <h1 class="intro-hero-title">${chapterMatch[2].trim()}</h1>
                        `;
                        firstH1.replaceWith(introHero);
                    }
                }
            }

            const cards = document.querySelectorAll('.container > .card');
            cards.forEach(card => {
                const elements = Array.from(card.children);
                let currentDetails = null;
                let detailsContent = null;

                elements.forEach(el => {
                    if (el.tagName === 'H3') {
                        currentDetails = document.createElement('details');
                        const summary = document.createElement('summary');
                        summary.innerHTML = el.innerHTML;

                        detailsContent = document.createElement('div');
                        detailsContent.className = 'details-content';

                        currentDetails.appendChild(summary);
                        currentDetails.appendChild(detailsContent);
                        card.insertBefore(currentDetails, el);
                        card.removeChild(el);
                    } else if (el.tagName === 'H1' || el.tagName === 'H2') {
                        currentDetails = null;
                    } else if (currentDetails) {
                        detailsContent.appendChild(el);
                    }
                });
            });

            const container = document.querySelector('.container');
            const processedCards = Array.from(container.querySelectorAll('.card'));

            const tabs = {
                itinerary: document.createElement('div'),
                bookings: document.createElement('div'),
                context: document.createElement('div'),
                activities: document.createElement('div')
            };

            for (const [key, el] of Object.entries(tabs)) {
                el.id = 'tab-' + key;
                el.className = 'tab-pane';
                if (key === defaultTab) el.classList.add('active');
                container.appendChild(el);
            }

            const bookingIcons = {
                flight: 'fa-solid fa-plane',
                hotel: 'fa-solid fa-hotel',
                activity: 'fa-solid fa-ticket',
                transport: 'fa-solid fa-train-subway',
                other: 'fa-solid fa-bookmark'
            };

            function bookingLabel(type) {
                if (type === 'flight') return labels.booking_flight || 'Flight';
                if (type === 'hotel') return labels.booking_hotel || 'Hotel';
                if (type === 'activity') return labels.booking_activity || 'Activity';
                if (type === 'transport') return labels.booking_transport || 'Transport';
                return labels.booking_default || 'Booking';
            }

            function renderInfoItems(tabEl, items, emptyText, iconClass, mode) {
                if (!items || !items.length) {
                    tabEl.innerHTML = `<div class="card" style="text-align:center; padding:40px 20px;"><i class="${iconClass}" style="font-size:3rem; color:#e4e6eb; margin-bottom:15px;"></i><p>${emptyText}</p></div>`;
                    return;
                }

                const listCard = document.createElement('div');
                listCard.className = 'card';
                items.forEach(item => {
                    const block = document.createElement('div');
                    block.style.padding = '10px 0';
                    block.style.borderBottom = '1px solid #eef2f7';
                    const isBooking = mode === 'bookings';
                    const itemType = (item.booking_type || 'other').toLowerCase();
                    const rowIcon = isBooking ? (item.icon || bookingIcons[itemType] || bookingIcons.other) : iconClass;
                    const typeBadge = isBooking ? `<span class="booking-type">${bookingLabel(itemType)}</span>` : '';
                    block.innerHTML = `
                        <p class="booking-item-title"><i class="${rowIcon} booking-item-icon"></i>${item.title || ''}${typeBadge}</p>
                        ${item.location ? `<p style="margin:2px 0 0; font-size:0.9rem; color:#64748b;">${item.location}</p>` : ''}
                        ${item.time ? `<p style="margin:2px 0 0; font-size:0.9rem; color:#64748b;">${item.time}</p>` : ''}
                        ${item.note ? `<p style="margin:4px 0 0; font-size:0.92rem; color:#475569;">${item.note}</p>` : ''}
                    `;
                    listCard.appendChild(block);
                });
                const last = listCard.lastElementChild;
                if (last) last.style.borderBottom = '0';
                tabEl.appendChild(listCard);
            }

            renderInfoItems(tabs.bookings, pageConfig.bookings, labels.no_bookings || 'No bookings added for this section yet.', 'fa-solid fa-ticket', 'bookings');
            renderInfoItems(tabs.activities, pageConfig.activities, labels.no_activities || 'No activities or restaurants saved yet.', 'fa-solid fa-utensils', 'activities');

            let currentTab = contextOnlyMode ? tabs.context : tabs.itinerary;
            let currentCard = document.createElement('div');
            currentCard.className = 'card';
            currentTab.appendChild(currentCard);

            processedCards.forEach(card => {
                Array.from(card.children).forEach(el => {
                    if (!contextOnlyMode) {
                        if (el.tagName === 'H2' && el.textContent.includes('Detailed Context')) {
                            currentTab = tabs.context;
                            currentCard = document.createElement('div');
                            currentCard.className = 'card';
                            currentTab.appendChild(currentCard);
                            el.style.display = 'none';
                        }
                    }

                    if (el.tagName === 'H1' || el.tagName === 'H2') {
                        if (currentCard.children.length > 0 && el.style.display !== 'none') {
                            currentCard = document.createElement('div');
                            currentCard.className = 'card';
                            currentTab.appendChild(currentCard);
                        }
                    }
                    currentCard.appendChild(el);
                });
                card.remove();
            });

            Object.values(tabs).forEach(tab => {
                Array.from(tab.children).forEach(card => {
                    if (card.children.length === 0) card.remove();
                });
            });

            // Context accordions: add square thumbnail preview in closed summary
            function enhanceContextAccordionThumbnails() {
                const contextPane = document.getElementById('tab-context');
                if (!contextPane) return;

                const contextDetails = contextPane.querySelectorAll('details');
                contextDetails.forEach(details => {
                    const summary = details.querySelector(':scope > summary');
                    const img = details.querySelector('.details-content .full-image');
                    if (!summary || !img || summary.querySelector('.summary-thumb')) return;

                    const textWrap = document.createElement('span');
                    textWrap.className = 'summary-text';
                    while (summary.firstChild) {
                        textWrap.appendChild(summary.firstChild);
                    }

                    const thumb = document.createElement('img');
                    thumb.className = 'summary-thumb';
                    thumb.src = img.getAttribute('src') || '';
                    thumb.alt = '';
                    thumb.loading = 'lazy';

                    summary.appendChild(thumb);
                    summary.appendChild(textWrap);
                });
            }

            enhanceContextAccordionThumbnails();

            // Schedule readability: time row + title + connected detail line
            function enhanceScheduleLayout(scope) {
                const headers = Array.from(scope.querySelectorAll('h2')).filter(h => h.textContent.includes('Schedule'));
                headers.forEach(h => {
                    const list = h.nextElementSibling;
                    if (!list || list.tagName !== 'UL' || list.dataset.enhancedSchedule === '1') return;
                    list.classList.add('schedule-list');
                    list.dataset.enhancedSchedule = '1';

                    const topItems = Array.from(list.children).filter(el => el.tagName === 'LI');
                    topItems.forEach(item => {
                        const time = item.querySelector(':scope > strong');
                        const sub = item.querySelector(':scope > ul');
                        if (!time || !sub) return;

                        const subItems = Array.from(sub.children).filter(el => el.tagName === 'LI');
                        const titleHtml = subItems[0] ? subItems[0].innerHTML : '';
                        const detailItems = subItems.slice(1).map(li => li.innerHTML);

                        const wrapper = document.createElement('div');
                        wrapper.className = 'schedule-item';
                        wrapper.innerHTML = `
                            <div class="schedule-time">${time.innerHTML}</div>
                            <div class="schedule-title">${titleHtml}</div>
                            ${detailItems.length ? `<ul class="schedule-details">${detailItems.map(d => `<li>${d}</li>`).join('')}</ul>` : ''}
                        `;

                        item.innerHTML = '';
                        item.appendChild(wrapper);
                    });
                });
            }

            enhanceScheduleLayout(document);

            // Daily overview highlights from bookings (flights + hotel update)
            const overviewMeta = pageConfig.daily_overview_meta || {};
            const itineraryPane = document.getElementById('tab-itinerary');
            if (itineraryPane && (overviewMeta.flights?.length || overviewMeta.hotels?.length)) {
                const dailyHeader = Array.from(itineraryPane.querySelectorAll('h2')).find(h => h.textContent.includes('Daily Overview'));
                if (dailyHeader) {
                    const box = document.createElement('div');
                    box.className = 'daily-overview-meta';

                    const pieces = [];
                    if (overviewMeta.flights?.length) {
                        const value = overviewMeta.flights
                            .map(f => f.time ? `${f.title} (${f.time})` : f.title)
                            .join(' · ');
                        pieces.push(`<div class="overview-meta-item"><i class="fa-solid fa-plane"></i><div><div class="overview-meta-label">${labels.label_flights_today || 'Flights Today'}</div><div class="overview-meta-value">${value}</div></div></div>`);
                    }
                    if (overviewMeta.hotels?.length) {
                        const value = overviewMeta.hotels
                            .map(h => `${h.action_label}: ${h.location || h.title}`)
                            .join(' · ');
                        pieces.push(`<div class="overview-meta-item"><i class="fa-solid fa-hotel"></i><div><div class="overview-meta-label">${labels.label_hotel || 'Hotel'}</div><div class="overview-meta-value">${value}</div></div></div>`);
                    }

                    box.innerHTML = pieces.join('');
                    const next = dailyHeader.nextElementSibling;
                    if (next) {
                        next.insertAdjacentElement('afterend', box);
                    } else {
                        dailyHeader.insertAdjacentElement('afterend', box);
                    }
                }
            }

            const navItems = document.querySelectorAll('.nav-item');
            const tabPanes = document.querySelectorAll('.tab-pane');
            navItems.forEach(item => {
                item.addEventListener('click', () => {
                    navItems.forEach(nav => nav.classList.remove('active'));
                    item.classList.add('active');

                    const targetTab = item.getAttribute('data-tab');
                    tabPanes.forEach(pane => {
                        pane.classList.remove('active');
                        if (pane.id === 'tab-' + targetTab) pane.classList.add('active');
                    });
                    window.scrollTo(0, 0);
                });
            });

            const allDetails = document.querySelectorAll('details');
            allDetails.forEach(details => {
                details.addEventListener('toggle', () => {
                    if (details.open) {
                        allDetails.forEach(other => {
                            if (other !== details && other.open) other.open = false;
                        });
                        setTimeout(() => {
                            const y = details.getBoundingClientRect().top + window.scrollY - 70;
                            window.scrollTo({ top: y, behavior: 'smooth' });
                        }, 100);
                    }
                });
            });

            const viewer = document.getElementById('image-viewer');
            const viewerImage = document.getElementById('viewer-image');
            const closeViewerBtn = document.getElementById('close-viewer');
            const images = document.querySelectorAll('.full-image');
            let pz = null;

            images.forEach(img => {
                img.addEventListener('click', () => {
                    viewerImage.src = img.src;
                    viewer.classList.add('active');
                    if (pz) pz.destroy();
                    pz = Panzoom(viewerImage, { maxScale: 10, step: 0.3, contain: '' });
                    viewerImage.parentElement.addEventListener('wheel', pz.zoomWithWheel);
                });
            });

            function closeViewer() {
                viewer.classList.remove('active');
                setTimeout(() => { if (pz) pz.reset(); }, 300);
            }

            closeViewerBtn.addEventListener('click', closeViewer);
        });
    </script>
    """

    tab_icons = {
        "itinerary": "fa-solid fa-map-location-dot",
        "context": "fa-solid fa-book-open",
        "activities": "fa-solid fa-utensils",
        "bookings": "fa-solid fa-ticket",
    }

    generated_files = []
    page_by_lang_and_section = {}
    for lang in languages:
        sec_map = {s["id"]: s for s in data_by_lang[lang]["sections"]}
        page_by_lang_and_section[lang] = {sid: sec_map[sid].get("page") for sid in sec_map if sec_map[sid].get("page")}

    for lang in languages:
        sections = data_by_lang[lang]["sections"]
        itineraries = data_by_lang[lang]["itineraries"]
        activities = data_by_lang[lang]["activities"]
        bookings = data_by_lang[lang]["bookings"]

        section_by_id = {s["id"]: s for s in sections}
        itinerary_by_section = {i["section_id"]: i for i in itineraries}

        chapter = next(s for s in sections if s.get("type") == "chapter")
        nav_section_ids = chapter.get("children", [])
        nav_sections = [section_by_id[sid] for sid in nav_section_ids]

        chapter_title = chapter.get("title", "Istanbul")
        chapter_city = chapter_title.split("—")[-1].strip() if "—" in chapter_title else chapter_title
        chapter_nav_label = f"Chapter 1 - {chapter_city}"

        for section in nav_sections:
            sid = section["id"]
            itinerary = itinerary_by_section.get(sid, {"overview_markdown": "", "schedule_markdown": "", "context_markdown": ""})

            page_filename = section.get("page")
            if not page_filename:
                page_filename = f"index_mobile.{lang}.html" if section.get("type") == "intro" else f"{sid}_mobile.{lang}.html"

            enabled_tabs = section.get("tabs", ["itinerary", "context", "activities", "bookings"])
            default_tab = enabled_tabs[0] if enabled_tabs else "itinerary"

            bookings_for_section = [dict(b) for b in bookings if b.get("section_id") == sid]
            for b in bookings_for_section:
                b["booking_type"] = infer_booking_type(b)

            activities_for_section = [a for a in activities if a.get("section_id") == sid]

            flights_today = [
                {"title": b.get("title", ""), "time": b.get("time", "")}
                for b in bookings_for_section
                if b.get("booking_type") == "flight" and include_in_daily_overview(b, section)
            ]
            hotels_today = []
            for b in bookings_for_section:
                if b.get("booking_type") != "hotel":
                    continue
                if not include_in_daily_overview(b, section):
                    continue

                action = infer_hotel_action(b)
                if action == "checkin":
                    action_label = ui_labels[lang]["label_checkin"]
                elif action == "checkout":
                    action_label = ui_labels[lang]["label_checkout"]
                else:
                    continue

                hotels_today.append(
                    {
                        "title": b.get("title", ""),
                        "location": b.get("location") or b.get("time", ""),
                        "action": action,
                        "action_label": action_label,
                    }
                )

            page_config = {
                "content_mode": "context_only" if section.get("type") == "intro" else "standard",
                "default_tab": default_tab,
                "bookings": bookings_for_section,
                "activities": activities_for_section,
                "daily_overview_meta": {
                    "flights": flights_today,
                    "hotels": hotels_today,
                },
                "ui_labels": ui_labels[lang],
            }

            nav_html_parts = []
            for tab in ["itinerary", "context", "activities", "bookings"]:
                if tab in enabled_tabs:
                    icon = tab_icons[tab]
                    label = ui_labels[lang][f"tab_{tab}"]
                    active = " active" if tab == default_tab else ""
                    nav_html_parts.append(
                        f'''        <button class="nav-item{active}" data-tab="{tab}">\n            <i class="{icon}"></i>\n            <span>{label}</span>\n        </button>'''
                    )
            nav_html = "\n".join(nav_html_parts)

            day_options = []
            for opt in nav_sections:
                active = " active" if opt["id"] == sid else ""
                opt_page = opt.get("page") or (f"index_mobile.{lang}.html" if opt.get("type") == "intro" else f"{opt['id']}_mobile.{lang}.html")
                day_options.append(f'<button class="day-option{active}" data-href="{opt_page}">{opt.get("label", opt["id"])}</button>')
            day_options_html = "\n                ".join(day_options)

            lang_options = []
            for opt_lang in languages:
                lang_active = " active" if opt_lang == lang else ""
                href = page_by_lang_and_section.get(opt_lang, {}).get(sid, page_filename)
                lang_options.append(
                    f'<button class="lang-option{lang_active}" data-href="{href}">{language_labels[opt_lang]}</button>'
                )
            lang_options_html = "\n                    ".join(lang_options)

            md_for_page = section_markdown(section, chapter, itinerary)
            raw_html = markdown.markdown(md_for_page, extensions=["tables", "fenced_code", "nl2br"])
            processed_html = process_html_chunk(raw_html)
            page_js = js.replace("__PAGE_CONFIG__", json.dumps(page_config, ensure_ascii=False))
            dir_attr = "rtl" if lang == "ar" else "ltr"

            full_html = f"""<!DOCTYPE html>
<html lang="{lang}" dir="{dir_attr}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="theme-color" content="#1877f2">
    <link rel="manifest" href="manifest.webmanifest">
    <link rel="apple-touch-icon" href="icons/icon-192.png">
    <title>Istanbul Guide - {section.get('label', sid)}</title>
    {css}
</head>
<body>
    <header>
        <div class="header-controls">
            <div class="day-switcher" id="day-switcher">
                <button class="day-switcher-btn" id="day-switcher-btn" type="button">
                    <div class="day-switcher-meta">
                        <span class="day-switcher-chapter">{chapter_nav_label}</span>
                        <span class="day-switcher-current">{section.get('label', sid)}</span>
                    </div>
                    <i class="fa-solid fa-chevron-down day-switcher-icon"></i>
                </button>
                <div class="day-switcher-menu">
                    <div class="day-switcher-label">{chapter_nav_label}</div>
                    {day_options_html}
                </div>
            </div>

            <div class="lang-switcher" id="lang-switcher">
                <button class="lang-btn" id="lang-btn" type="button">
                    <span>{lang.upper()}</span>
                    <i class="fa-solid fa-chevron-down"></i>
                </button>
                <div class="lang-switcher-menu">
                    {lang_options_html}
                </div>
            </div>
        </div>
    </header>

    <div class="container">
        {processed_html}
    </div>

    <nav class="bottom-nav">
{nav_html}
    </nav>

    <div id="image-viewer">
        <button id="close-viewer"><i class="fa-solid fa-xmark"></i></button>
        <div id="viewer-container">
            <img id="viewer-image" src="" alt="Zoomed Image">
        </div>
    </div>

    <script src="assets/js/panzoom.min.js"></script>
    {page_js}
    <script>
        if ('serviceWorker' in navigator) {{
            window.addEventListener('load', function() {{
                navigator.serviceWorker.register('./service-worker.js');
            }});
        }}
    </script>
</body>
</html>
"""

            target = out_dir / page_filename
            target.write_text(full_html, encoding="utf-8")
            generated_files.append(target)
            print(f"Generated {target}")

    write_pwa_files(data_dir, out_dir, generated_files)


def write_pwa_files(data_dir: Path, out_dir: Path, generated_pages: list[Path]) -> None:
    manifest = {
        "name": "Istanbul Trip Guide",
        "short_name": "Istanbul Guide",
        "start_url": "./index_mobile.html",
        "scope": "./",
        "display": "standalone",
        "background_color": "#f0f2f5",
        "theme_color": "#1877f2",
        "description": "Offline travel guide for Istanbul with itinerary, context, activities and bookings.",
        "icons": [
            {"src": "icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "icons/icon-512.png", "sizes": "512x512", "type": "image/png"}
        ]
    }
    (out_dir / "manifest.webmanifest").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    precache = set()
    for page in generated_pages:
        precache.add(page.name)

    for name in [
        "mobile_sections.en.json",
        "mobile_sections.it.json",
        "mobile_sections.ar.json",
        "mobile_itineraries.en.json",
        "mobile_itineraries.it.json",
        "mobile_itineraries.ar.json",
        "mobile_activities.en.json",
        "mobile_activities.it.json",
        "mobile_activities.ar.json",
        "mobile_bookings.en.json",
        "mobile_bookings.it.json",
        "mobile_bookings.ar.json",
        "mobile_sections.json",
        "mobile_itineraries.json",
        "mobile_activities.json",
        "mobile_bookings.json",
        "manifest.webmanifest",
        "icons/icon-192.png",
        "icons/icon-512.png",
        "assets/js/panzoom.min.js",
        "assets/fontawesome/css/all.min.css",
    ]:
        if (out_dir / name).exists():
            precache.add(name)

    for folder in ["images", "assets/fontawesome/webfonts"]:
        root = out_dir / folder
        if root.exists():
            for fp in root.rglob("*"):
                if fp.is_file():
                    precache.add(str(fp.relative_to(out_dir)).replace("\\", "/"))

    precache_list = sorted(precache)
    sw_body = f"""
const CACHE_NAME = 'istanbul-guide-v1';
const PRECACHE_URLS = {json.dumps(precache_list, ensure_ascii=False, indent=2)};

self.addEventListener('install', (event) => {{
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE_URLS)));
  self.skipWaiting();
}});

self.addEventListener('activate', (event) => {{
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))))
  );
  self.clients.claim();
}});

self.addEventListener('fetch', (event) => {{
  if (event.request.method !== 'GET') return;
  event.respondWith(
    caches.match(event.request).then((cached) => cached || fetch(event.request).then((response) => {{
      const copy = response.clone();
      caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
      return response;
    }}).catch(() => caches.match('index_mobile.html')))
  );
}});
"""
    (out_dir / "service-worker.js").write_text(sw_body.strip() + "\n", encoding="utf-8")


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parents[1]
    render_mobile_pages(base_dir / "itinerary", base_dir / "itinerary")
