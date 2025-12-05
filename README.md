# 🕸️ HLTV Match Scraper

A Python-based web scraper that collects **HLTV.org match data**, including:

- Match ID  
- Event name  
- Match date & time  
- Team names  
- Player names  
- Player nationalities  

The script outputs the data into:

- `matches.json`  
- `matches.csv`

All configurable options (e.g., request delay, file paths, impersonated browser) are available in a single **CONFIG** block at the top of the script.

---

## 🚀 Features

- Scrapes any HLTV date (`--days-ahead` offset)
- Configurable delay between match requests
- Outputs JSON and CSV
- Automatically extracts:
  - Team rosters  
  - Player nationalities  
  - Event info  
  - Match timestamp  
- Uses lightweight, fast scraping via `curl_cffi`

---

## 📦 Installation

### 1. Clone the repo  
git clone https://github.com/99ita/HLTVScraper

cd HLTVScraper

### 2. Install dependencies  
Install all required libraries:

pip install curl_cffi beautifulsoup4

---

## 📁 Dependencies

| Package | Purpose |
|---------|---------|
| **curl_cffi** | Fast and reliable HTTP requests with browser impersonation |
| **beautifulsoup4** | HTML parsing |
| **re / datetime / csv / json / logging** | Standard library modules |

---

## ▶️ Running the Scraper

### Scrape today's matches (default):

python scraper.py

### Scrape matches **N days ahead**:

Example: scrape matches 2 days from now:

python scraper.py 2

This calculates:

target_date = today + 2 days

---

## ⚙️ Configuration

At the very top of the script there is a `CONFIG` dictionary:

CONFIG = {
    "base_url": "https://www.hltv.org/matches?selectedDate=",
    "delay_between_match_requests": 0.2,
    "impersonate_browser": "chrome120",
    "json_output_path": "matches.json",
    "csv_output_path": "matches.csv",
    "csv_header": [...]
}

You can change:

- request delay  
- output filenames  
- impersonation settings  
- CSV column ordering  
- base URL  

---

## 📝 Output Files

### `matches.json`

A structured JSON list:

[
    {
        "match_id": "2367210",
        "url": "https://www.hltv.org/matches/2367210/...",
        "event": "IEM Katowice 2025",
        "datetime": "12-05-2025 16:30",
        "teams": [
            {
                "name": "G2",
                "players": [
                    {"name": "NiKo", "nationality": "Bosnia"},
                    ...
                ]
            },
            ...
        ]
    }
]

### `matches.csv`

Flat CSV format ideal for Excel, Sheets, or ML preprocessing.

---

## 🛠️ Troubleshooting

### HLTV blocks requests  
Increase delay or change impersonated browser:

"delay_between_match_requests": 1.0,
"impersonate_browser": "chrome124",

### Missing players / teams  
HLTV sometimes hides lineups before the match starts — this is expected.

---

## 📄 License

MIT — free to use and modify.

---