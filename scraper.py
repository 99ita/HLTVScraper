from curl_cffi import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import re
import json
import csv
import sys
import logging
from enum import Enum

class MatchStatus(Enum):
    FUTURE = "future"
    LIVE = "live"
    PAST = "past"


# ------------------------------------------------ #
#                     CONFIG                       #
# ------------------------------------------------ #
CONFIG = {
    "base_url": "https://www.hltv.org/matches?selectedDate=",
    "delay_between_match_requests": 0.2,       # seconds
    "impersonate_browser": "chrome120",
    
    # File outputs
    "json_output_path": "matches.json",

}
# ------------------------------------------------ #


# ------------------ Logging Setup ------------------ #
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# ------------------ Helper Functions ------------------ #
def convert_date_string(date_str):
    clean_str = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_str)
    dt = datetime.strptime(clean_str, "%d of %B %Y")
    return dt.strftime("%d-%m-%Y")

MATCH_ID_RE_PATTERN = r"https:\/\/www\.hltv\.org\/matches\/(\d+)\/.+"


# ------------------ Classes ------------------ #
class Matches():
    def __init__(self, base_url, day):
        self.url = base_url + day
        self.soup = None
        self.match_urls = []
        self.matches = []

    def fetch_html(self):
        resp = requests.get(self.url, impersonate=CONFIG["impersonate_browser"])
        self.soup = BeautifulSoup(resp.text, "html.parser")

    def scrape_html(self):
        urls = []
        for match in self.soup.select("div.match-wrapper"):
            teams = match.select(".match-team .match-teamname")
            if len(teams) < 2:
                continue

            a_tag = match.find("a", href=True)
            if not a_tag:
                continue

            href = a_tag["href"]
            if href.startswith("/matches/"):
                urls.append("https://www.hltv.org" + href)

        self.match_urls = urls
        logger.info(f"Scraped matches page, found {len(urls)} matches.")

    def load_matches(self):
        delay = CONFIG["delay_between_match_requests"]

        self.fetch_html()
        self.scrape_html()

        total = len(self.match_urls)
        logger.info(f"Scraping {total} matches with {delay}s delay between requests")

        for i, match_url in enumerate(self.match_urls, start=1):
            match = Match(match_url)
            match.load()
            self.matches.append(match)

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\r{timestamp} [PROGRESS] Retrieved match {i}/{total}", end="", flush=True)
            time.sleep(delay)

        print()  # Newline after progress
        logger.info("Finished scraping all matches.")

    def to_json(self):
        return [match.to_json() for match in self.matches]

    def to_csv(self):
        return [match.to_csv() for match in self.matches]


class Match():
    def __init__(self, url):
        self.url = url
        self.soup = None

        match = re.search(MATCH_ID_RE_PATTERN, url)
        self.match_id = match.group(1) if match else None

        self.teams = []
        self.event = None
        self.datetime = None
        self.status = None

    def load(self):
        self.fetch_html()
        self.scrape_html()

    def fetch_html(self):
        resp = requests.get(self.url, impersonate=CONFIG["impersonate_browser"])
        self.soup = BeautifulSoup(resp.text, "html.parser")
        with open("single_match_future.html", "w", encoding="utf-8") as f:
            f.write(self.soup.prettify())

    def scrape_html(self):
        self.extract_teams_players()
        self.extract_time_and_event()

    def extract_teams_players(self):
        lineups = self.soup.select("div.lineup.standard-box")
        for lineup in lineups:
            team_name_tag = lineup.select_one(".box-headline a.text-ellipsis")
            team_name = team_name_tag.get_text(strip=True)

            player_divs = lineup.select("div.player-compare")
            players = []
            for pdiv in player_divs:
                name_div = pdiv.select_one(".text-ellipsis")
                if not name_div:
                    continue
                player_name = name_div.get_text(strip=True)

                flag_img = pdiv.find("img", class_="flag")
                nationality = flag_img['title'] if flag_img else None

                players.append(Player(player_name, nationality))

            self.teams.append(Team(team_name, players))

    def extract_time_and_event(self):
        container = self.soup.find("div", class_="timeAndEvent")
        if not container:
            return None

        time_div = container.find("div", class_="time")
        date_div = container.find("div", class_="date")
        event_div = container.find("div", class_="event")
        status_div = container.find("div", class_="countdown")

        time_str = time_div.text.strip() if time_div else None
        date_str = convert_date_string(date_div.text.strip()) if date_div else None
        event_name = event_div.text.strip() if event_div else None

        self.datetime = date_str + f' {time_str}' if date_str and time_str else None
        self.event = event_name


        if status_div:
            text = status_div.get_text(strip=True).lower()

            if "match over" in text:
                self.status = MatchStatus.PAST
            elif "live" in text:
                self.status = MatchStatus.LIVE
            else:
                self.status = MatchStatus.FUTURE
            

    def to_json(self):
        return {
            "match_id": self.match_id,
            "url": self.url,
            "event": self.event,
            "datetime": self.datetime,
            "status": self.status.value,
            "teams": [team.to_json() for team in self.teams]
            
        }

    def to_csv(self):
        row = [self.match_id, self.url, self.event, self.datetime]
        for team in self.teams:
            row.extend(team.to_csv())
        return row


class Team():
    def __init__(self, name, players):
        self.name = name
        self.players = players

    def to_json(self):
        return {
            "name": self.name,
            "players": [player.to_json() for player in self.players]
        }

    def to_csv(self):
        row = [self.name]
        for player in self.players:
            row.extend(player.to_csv())
        return row


class Player():
    def __init__(self, name, nationality):
        self.name = name
        self.nationality = nationality

    def to_json(self):
        return {
            "name": self.name,
            "nationality": self.nationality
        }

    def to_csv(self):
        return [self.name, self.nationality]


# ------------------ Main Script ------------------ #
if __name__ == '__main__':
    start_time = time.time()

    url = 'https://www.hltv.org/matches/2388121/b8-vs-natus-vincere-starladder-budapest-major-2025'
    m = Match(url)
    m.load()
    print(m.to_json())
    # days_ahead = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    # target_date = datetime.now() + timedelta(days=days_ahead)
    # formatted = target_date.strftime("%Y-%m-%d")

    # logger.info(f"Scraping HLTV matches for date: {formatted}")

    # ms = Matches(CONFIG["base_url"], formatted)
    # ms.load_matches()

    # # Save JSON
    # with open(CONFIG["json_output_path"], "w", encoding="utf-8") as f:
    #     json.dump(ms.to_json(), f, ensure_ascii=False, indent=4)
    # logger.info(f"Saved {CONFIG['json_output_path']}")


    end_time = time.time()
    logger.info(f"Total execution time: {end_time - start_time:.2f} seconds")
