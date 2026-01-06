import re
import logging
import cloudscraper
import time

import json
def extract_json_arrays_from_socketio(msg):
    """
    Find all '42' application messages and extract the JSON array that follows.
    This does bracket-matching to handle nested arrays/objects and string escapes.
    Returns a list of parsed JSON Python objects (e.g. ["eventName", {...}]).
    """
    results = []
    i = 0
    L = len(msg)

    while i < L:
        # Find the next '42' token
        idx = msg.find('42', i)
        if idx == -1:
            break

        # After '42' we expect a JSON array starting with '[' (maybe after some whitespace)
        j = idx + 2
        # skip whitespace
        while j < L and msg[j].isspace():
            j += 1

        if j >= L or msg[j] != '[':
            # not an array, skip this '42' and continue searching
            i = idx + 2
            continue

        # Now perform bracket matching to find the end of the JSON array.
        start = j
        k = start
        depth = 0
        in_string = False
        escape = False

        while k < L:
            ch = msg[k]

            if in_string:
                if escape:
                    escape = False
                elif ch == '\\':
                    escape = True
                elif ch == '"':
                    in_string = False
            else:
                if ch == '"':
                    in_string = True
                elif ch == '[' or ch == '{':
                    depth += 1
                elif ch == ']' or ch == '}':
                    depth -= 1
                    # If we've closed the initial array and depth is 0, we are done
                    if depth == 0:
                        k += 1  # include this closing bracket
                        break
            k += 1

        # If we didn't close properly, bail out for this token
        if k > L or depth != 0:
            i = idx + 2
            continue

        json_text = msg[start:k]
        try:
            parsed = json.loads(json_text)
            results.append(parsed)
        except Exception:
            # malformed JSON — skip
            pass

        # continue searching after k
        i = k

    return results


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


BASE_SITE = "https://www.hltv.org"
SOCKET_BASE = "https://scorebot-lb.hltv.org"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"

class LiveMatch():
    def __init__(self,url):
        match = re.search(r"https:\/\/www\.hltv\.org\/matches\/(\d+)\/.+", url)
        self.match_id = match.group(1) if match else None
        self.matchLive = True
        self.reset()

    def run(self):
        self.reset()
        self.connect()
        self.listen_loop()

    def reset(self, resetSolvedCloudflare = True, resetSidFetched = True, resetReadyForMatchSent = True):
        if resetSolvedCloudflare:
            self.solvedCloudflare = False
        if resetSidFetched:
            self.sidFetched = False
        if resetReadyForMatchSent:
            self.readyForMatchSent = False

    def connect(self):
        self.reset()
        self.solveCloudflare()
        self.fetchSID()
        self.readyForMatch()


    def solveCloudflare(self):
        logger.info("Solving Cloudflare...")
        try:
            self.scraper = cloudscraper.create_scraper(browser={"browser":"chrome","platform":"windows","desktop":True})
            self.scraper.headers.update({"User-Agent": UA, "Origin": BASE_SITE, "Referer": BASE_SITE})
            self.scraper.get(BASE_SITE)
            logger.info("Solved Cloudflare!")
            self.solvedCloudflare = True
        except Exception as e:
            logger.exception("Error solving Cloudflare",e)
            

    def fetchSID(self):
        logger.info("Fetching SID...")
        try:
            t = str(int(time.time() * 1000))
            poll_url = f"{SOCKET_BASE}/socket.io/?EIO=3&transport=polling&t={t}"
            r = self.scraper.get(poll_url)
            data = r.text

            # Extract SID
            sid_match = re.search(r'"sid":"([^"]+)"', data)
            self.sid = None
            if not sid_match:
                raise Exception("SID not found")

            self.sid = sid_match.group(1)
            logger.info("SID fetched!")
            self.sidFetched = True
        except Exception as e:
            logger.exception("Error fetching SID",e)
    
    def readyForMatch(self):
        logger.info("Sending 'readyForMatch' message...")
        try:
            post_t = str(int(time.time()*1000))
            post_url = f"{SOCKET_BASE}/socket.io/?EIO=3&transport=polling&t={post_t}&sid={self.sid}"

            payload = f'42["readyForMatch","{{\\"token\\":\\"\\",\\"listId\\":\\"{self.match_id}\\"}}"]'
            self.scraper.post(post_url, data=payload, headers={"Content-Type":"text/plain;charset=UTF-8"}) 
            logger.info("'readyForMatch' message sent!")
            self.readyForMatchSent = True
        except Exception as e:
            logger.exception("Error sending 'readyForMatch' message",e)

    def listen_loop(self):
        with open("LOG_FILE.json", "a", encoding="utf-8") as log_file:
            while self.matchLive:
                try:
                    t = str(int(time.time() * 1000))
                    poll_url = f"{SOCKET_BASE}/socket.io/?EIO=3&transport=polling&t={t}&sid={self.sid}"
                    r = self.scraper.get(poll_url)
                    raw = r.text

                    # Extract JSON arrays (each should be [eventName, eventData, ...])
                    arrays = extract_json_arrays_from_socketio(raw)

                    for arr in arrays:
                        if not isinstance(arr, list) or len(arr) < 2:
                            continue

                        event_name = arr[0]
                        event_data = arr[1]

                        # Only keep "log" events
                        if event_name != "scoreboard":
                            continue

                        # Decode nested JSON inside data
                        if isinstance(event_data, str):
                            try:
                                event_data = json.loads(event_data)
                            except Exception:
                                continue

                        score = {
                            "mapName" : event_data["mapName"],
                            "terroristTeamName" : event_data["terroristTeamName"],
                            "ctTeamName" : event_data["ctTeamName"],
                            "currentRound" : event_data["currentRound"],
                            "counterTerroristScore" : event_data["counterTerroristScore"],
                            "terroristScore" : event_data["terroristScore"],
                            "ctTeamId" : event_data["ctTeamId"],
                            "tTeamId" : event_data["tTeamId"],
                            "frozen" : event_data["frozen"],
                            "live" : event_data["live"],
                            "ctTeamScore" : event_data["ctTeamScore"],
                            "tTeamScore" : event_data["tTeamScore"],
                            "startingCt" : event_data["startingCt"],
                            "startingT" : event_data["startingT"],
                            "regulationHalfLength" : event_data["regulationHalfLength"],
                            "overtimeHalfLength" : event_data["overtimeHalfLength"]
                        }


                        print(json.dumps(score, ensure_ascii=False))
                        print("\n\n\n-----\n\n\n")
                        log_file.write(json.dumps(score, ensure_ascii=False) + "\n")
                        log_file.flush()

                    time.sleep(20)



                except KeyboardInterrupt:
                    self.matchLive = False

                except Exception as e:
                    logger.exception("Error in listening loop",e)
                    logger.info("Reconnecting...")
                    self.connect()
            




lm = LiveMatch('https://www.hltv.org/matches/2388856/mouz-nxt-vs-algo-urban-riga-open-season-2')
lm.run()