from match import MatchFactory,Match
from configs import MATCHES_DATE_URL, DELAY_BETWEEN_REQUESTS, IMPERSONATE_BROWSER, JSON_OUTPUT_PATH

from bs4 import BeautifulSoup
from datetime import datetime,timedelta
import logging
from curl_cffi import requests


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)



def get_match_list_day(days_ahead):
    target_date = datetime.now() + timedelta(days=days_ahead)
    formatted_date = target_date.strftime("%Y-%m-%d")
    logger.info(f"Scraping HLTV matches for date: {formatted_date}")

    url = MATCHES_DATE_URL + formatted_date

    resp = requests.get(url, impersonate=IMPERSONATE_BROWSER)
    soup = BeautifulSoup(resp.text, "html.parser")
    
    match_urls = []
    for match in soup.select("div.match-wrapper"):
        teams = match.select(".match-team .match-teamname")
        if len(teams) < 2:
            continue

        a_tag = match.find("a", href=True)
        if not a_tag:
            continue

        href = a_tag["href"]
        if href.startswith("/matches/"):
            match_urls.append("https://www.hltv.org" + href)

    return match_urls