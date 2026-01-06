import re
from enum import Enum
from curl_cffi import requests
from bs4 import BeautifulSoup
from datetime import datetime
from configs import IMPERSONATE_BROWSER
from player import Player
from stats import Stats,PlayerStats
import json


def convert_date_string(date_str):
    clean_str = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_str)
    dt = datetime.strptime(clean_str, "%d of %B %Y")
    return dt.strftime("%d-%m-%Y")

class MatchStatus(Enum):
    FUTURE = "Match Scheduled"
    LIVE = "Live Match"
    PAST = "Match Finished"


class MatchFactory():
    def __init__(self, url, html, logger, ensure_pt = False):
        self.url = url
        self.logger = logger
        if html == None:
            self.logger.info(f"Fetching {url}")   
            html = self.fetch_html()

        self.soup = BeautifulSoup(html, "html.parser")
        self.ensure_pt = ensure_pt

    def fetch_html(self):
        resp = requests.get(self.url, impersonate=IMPERSONATE_BROWSER)
        return resp.text
    
    def get_match(self):
        return Match(self.url,self.soup,self.logger,self.ensure_pt)



class Match():
    def __init__(self, url, soup, logger, ensure_pt = False):
        self.logger = logger
        self.url = url
        self.soup = soup

        match = re.search(r"https:\/\/www\.hltv\.org\/matches\/(\d+)\/.+", url)
        self.match_id = match.group(1) if match else None

        
        self.players_scrape()
        self.logger.info(f"Players and nationalities scraped!")
        self.any_pt = False
        for player in self.team_a_players:
            if player.is_pt():
                self.any_pt = True
        for player in self.team_b_players:
            if player.is_pt():
                self.any_pt = True

        if ensure_pt:
            if self.any_pt:
                self.logger.info("Ensure PT is True, match has PT players, continue scraping")
            else:
                self.logger.info("Ensure PT is True, match has no PT players, returning")
                return
            


        self.init_scrape()
        self.logger.info(f"Match info: {self.team_a_name} vs {self.team_b_name} - {self.datetime} - {self.event} - {self.status.value}")
        self.stats = Stats()
        self.score = None
        self.scrape_map_info()
        self.logger.info("Maps info scraped!")

        if self.status in [MatchStatus.LIVE, MatchStatus.PAST]:
            self.extract_stats()
            self.logger.info(f"Stats scraped!")
        

    


        logger.info(f"Match data scrape complete ({"PT found" if self.any_pt else "No PT found"})")
        

    def init_scrape(self):
        # ---- TIME / EVENT / STATUS ----
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

        self.datetime = f"{date_str} {time_str}" if date_str and time_str else None
        self.event = event_name

        if status_div:
            text = status_div.get_text(strip=True).lower()
            if "match over" in text:
                self.status = MatchStatus.PAST
            elif "live" in text:
                self.status = MatchStatus.LIVE
            else:
                self.status = MatchStatus.FUTURE

        # ---- TEAM A / TEAM B ----
        teams_box = self.soup.find("div", class_="standard-box teamsBox")
        if not teams_box:
            return

        team_divs = teams_box.find_all("div", class_="team", limit=2)

        self.team_a_name = None
        self.team_b_name = None

        if len(team_divs) >= 1:
            team_a_name_div = team_divs[0].find("div", class_="teamName")
            self.team_a_name = team_a_name_div.get_text(strip=True) if team_a_name_div else None

        if len(team_divs) >= 2:
            team_b_name_div = team_divs[1].find("div", class_="teamName")
            self.team_b_name = team_b_name_div.get_text(strip=True) if team_b_name_div else None
            

    def extract_stats(self):
        map_lookup = self.build_map_name_lookup()
        stats_blocks = self.soup.select("div.stats-content")
        for block in stats_blocks:
            map_id = block.get("data-map-id")

            if map_id == "all" or block.get("id") == "all-content":
                map_name = "total"
                is_total = True
            else:
                map_name = map_lookup.get(map_id, "unknown")
                is_total = False

            tables = block.select("table.table.totalstats")
            for table in tables:
                header = table.select_one("tr.header-row")
                team_tag = header.select_one("a.teamName") if header else None
                team_name = team_tag.get_text(strip=True) if team_tag else None

                for row in table.select("tr"):
                    if "header-row" in row.get("class", []):
                        continue

                    nick_tag = row.select_one("span.player-nick")
                    nickname = nick_tag.get_text(strip=True)


                    # nationality 
                    flag = row.select_one("img.flag") 
                    nationality = flag["title"] if flag else None

                    kd = row.select_one("td.kd.traditional-data")
                    adr = row.select_one("td.adr.traditional-data")
                    kast = row.select_one("td.kast.traditional-data")
                    rating = row.select_one("td.rating")
                    swing = row.select_one("td.roundSwing")

                    kd_text = kd.get_text(strip=True) if kd else None
                    adr_text = adr.get_text(strip=True) if adr else None
                    kast_text = kast.get_text(strip=True) if kast else None
                    rating_text = rating.get_text(strip=True) if rating else None
                    swing_text = swing.get_text(strip=True) if swing else None

                    kills = deaths = None
                    if kd_text and "-" in kd_text:
                        k, d = kd_text.split("-")
                        kills, deaths = int(k), int(d)

                    ps = PlayerStats(
                        nickname=nickname,
                        kills=kills,
                        deaths=deaths,
                        kd=kd_text,
                        adr=adr_text,
                        kast=kast_text,
                        rating=rating_text,
                        swing=swing_text
                    )

                    # Add to Stats object
                    if is_total:
                        self.stats.add_total(team_name, ps)
                    else:
                        self.stats.add_map(map_name, team_name, ps)


    def scrape_map_info(self):
        """Scrapes map info: picks, bans, results, scores, and stats URLs."""
        self.maps_info = []

        maps_container = self.soup.select_one("div.col-6.col-7-small")
        if not maps_container:
            return

        # Extract veto/pick info (if available)
        veto_boxes = maps_container.select("div.veto-box")
        self.veto_info = []
        for vb in veto_boxes:
            text_div = vb.select_one("div.padding")
            if text_div:
                # Each line is a pick/ban
                lines = [line.strip() for line in text_div.stripped_strings if line.strip()]
                self.veto_info.extend(lines)

        # Extract per-map results
        mapholders = maps_container.select("div.mapholder")
        for m in mapholders:
            map_name_div = m.select_one(".mapname")
            map_name = map_name_div.get_text(strip=True) if map_name_div else None

            results = m.select_one(".results")
            if not results:
                continue

            left_team_div = results.select_one(".results-left")
            right_team_div = results.select_one(".results-right")

            def parse_team(team_div):
                if not team_div:
                    return {"name": None, "score": None, "status": None}
                name_div = team_div.select_one(".results-teamname")
                score_div = team_div.select_one(".results-team-score")
                classes = team_div.get("class", [])
                if "won" in classes:
                    status = "won"
                elif "lost" in classes:
                    status = "lost"
                elif "tie" in classes:
                    status = "tie"
                else:
                    status = None
                # If score is "-", treat as None
                score = score_div.get_text(strip=True) if score_div else None
                if score == "-":
                    score = None
                return {
                    "name": name_div.get_text(strip=True) if name_div else None,
                    "score": score,
                    "status": status
                }

            left_team = parse_team(left_team_div)
            right_team = parse_team(right_team_div)

            self.maps_info.append({
                "map_name": map_name,
                "team_a": left_team,
                "team_b": right_team
            })


    def build_map_name_lookup(self):
        mapping = {}

        full_names = self.soup.select(".dynamic-map-name-full")
        for div in full_names:
            map_id = div.get("id")
            map_name = div.get_text(strip=True)
            if map_id:
                mapping[map_id] = map_name

        return mapping

    def players_scrape(self):
        self.team_a_players = []
        self.team_b_players = []
        lineups = self.soup.select("div.lineup.standard-box")
        fst = True
        for lineup in lineups:
            team_name_tag = lineup.select_one(".box-headline a.text-ellipsis")
            team_name = team_name_tag.get_text(strip=True)

            player_divs = lineup.select("div.player-compare")
            for pdiv in player_divs:
                name_div = pdiv.select_one(".text-ellipsis")
                if not name_div:
                    continue
                player_name = name_div.get_text(strip=True)

                flag_img = pdiv.find("img", class_="flag")
                nationality = flag_img['title'] if flag_img else None

                if fst:
                    self.team_a_players.append(Player(player_name, nationality))
                else:
                    self.team_b_players.append(Player(player_name, nationality))
                    
            fst = False

    def to_json(self):
        return {
            "match_id": self.match_id,
            "url": self.url,
            "event": self.event,
            "datetime": self.datetime,
            "match_status": self.status.value,
            "any_pt": getattr(self, "any_pt", None),
            "team_a_name": self.team_a_name,
            "team_b_name": self.team_b_name,
            "team_a_players": [player.to_json() for player in self.team_a_players],
            "team_b_players": [player.to_json() for player in self.team_b_players],
            "stats": self.stats.to_json(),
            "veto_info": getattr(self, "veto_info", []),
            "maps_info": getattr(self, "maps_info", [])
        }

   

if __name__ == "__main__":

    
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    logger = logging.getLogger(__name__)
    mtcs = {
        "past": {"url": "https://www.hltv.org/matches/2388113/furia-vs-g2-starladder-budapest-major-2025", "file_name" : "single_match_past.html"},
        "live": {"url": "https://www.hltv.org/matches/2388596/ground-zero-vs-rooster-dfrag-open-series-2", "file_name" : "single_match_live.html"},
        "future": {"url": "https://www.hltv.org/matches/2388121/b8-vs-natus-vincere-starladder-budapest-major-2025", "file_name" : "single_match_future.html"}

    }


    mode = "past"


    url = mtcs[mode]["url"]
    file_name = mtcs[mode]["file_name"]
    with open(file_name,"r",encoding='utf-8') as fp:
        html = fp.read()

    mf = MatchFactory(url,html,logger,False)
    match = mf.get_match()
    #print("\n\n\n\n")
    #print(json.dumps(match.to_json(),ensure_ascii=False))


