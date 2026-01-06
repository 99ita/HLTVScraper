import cloudscraper
import re
import time
import json
HLTV_MATCH_ID = "2388440"
BASE_SITE = "https://www.hltv.org"
SOCKET_BASE = "https://scorebot-lb.hltv.org"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"

# -------------------------------
# 1. Create Cloudscraper session
# -------------------------------
scraper = cloudscraper.create_scraper(browser={"browser":"chrome","platform":"windows","desktop":True})
scraper.headers.update({"User-Agent": UA, "Origin": BASE_SITE, "Referer": BASE_SITE})

print("[*] Solving Cloudflare...")
scraper.get(BASE_SITE)

# -------------------------------
# 2. Initial polling GET to get SID
# -------------------------------
t = str(int(time.time() * 1000))
poll_url = f"{SOCKET_BASE}/socket.io/?EIO=3&transport=polling&t={t}"
r = scraper.get(poll_url)
data = r.text

# Extract SID
sid_match = re.search(r'"sid":"([^"]+)"', data)
if not sid_match:
    raise Exception("SID not found")

sid = sid_match.group(1)
print(f"[+] SID: {sid}")

# Update io cookie
scraper.cookies.set("io", sid, domain="scorebot-lb.hltv.org")

# -------------------------------
# 3. Send readyForMatch event
# -------------------------------
post_t = str(int(time.time()*1000))
post_url = f"{SOCKET_BASE}/socket.io/?EIO=3&transport=polling&t={post_t}&sid={sid}"

payload = f'42["readyForMatch","{{\\"token\\":\\"\\",\\"listId\\":\\"{HLTV_MATCH_ID}\\"}}"]'
scraper.post(post_url, data=payload, headers={"Content-Type":"text/plain;charset=UTF-8"})
print("[*] Sent readyForMatch, starting event listener...")
# -------------------------------
# 4. Long-poll loop
# -------------------------------
def parse_socketio_message(msg):
    """
    Socket.IO messages are prefixed with numbers.
    We only handle '42' events (application messages)
    """
    messages = []
    parts = re.findall(r'42\[.*?\]', msg)
    for p in parts:
        try:
            json_part = p[2:]  # remove '42'
            data = json.loads(json_part)
            messages.append(data)
        except Exception:
            continue
    return messages


import json
import time

all_messages = []
LOG_FILE = "socket_json.log"
LOG_FILE_FULL = "socket_json_full.log"
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


# -------------------------------
# Long-poll loop (uses the new parser)
# -------------------------------
all_messages = []



try:
    with open(LOG_FILE, "a", encoding="utf-8") as log_file, open(LOG_FILE_FULL, "a",encoding='utf-8') as log_file_full:
        while True:
            try:
                t = str(int(time.time() * 1000))
                poll_url = f"{SOCKET_BASE}/socket.io/?EIO=3&transport=polling&t={t}&sid={sid}"
                r = scraper.get(poll_url)
                raw = r.text

                # Extract JSON arrays (each should be [eventName, eventData, ...])
                arrays = extract_json_arrays_from_socketio(raw)

                log_file_full.write(json.dumps(arrays,ensure_ascii=False) + "\n")

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
                    event_data["mapName"]
                    event_data["terroristTeamName"]
                    event_data["ctTeamName"]
                    event_data["currentRound"]
                    event_data["counterTerroristScore"]
                    event_data["terroristScore"]

                    print(json.dumps(event_data, ensure_ascii=False))
                    log_file.write(json.dumps(event_data, ensure_ascii=False) + "\n")

                log_file.flush()
                time.sleep(5)

            except Exception as ex:
                error_record = {
                    "timestamp": time.time(),
                    "error": str(ex)
                }
                log_file.write(json.dumps(error_record, ensure_ascii=False) + "\n")
                log_file.flush()
                time.sleep(1)

except KeyboardInterrupt:
    print("\n[CTRL+C] Stopped. JSON logs saved to", LOG_FILE)

    # optional: also save in-memory parsed messages to messages.json
    with open("messages.json", "w", encoding="utf-8") as f:
        json.dump(all_messages, f, indent=2, ensure_ascii=False)

    print(f"[DONE] Saved {len(all_messages)} parsed messages to messages.json")