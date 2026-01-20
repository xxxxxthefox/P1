# ULTRA GLOBAL ROBLOX CHAT SERVER FOR RENDER
# OWNER: xxxxxthefox
# ⚡ WebSocket + Rooms + Anti-Spam + Anti-Swear + Logging

import asyncio, websockets, json, time, re
from collections import defaultdict, deque
from http import HTTPStatus

HOST = "0.0.0.0"
PORT = 8765

clients = {}                 # ws -> username
rooms = defaultdict(set)    # room -> websockets
history = defaultdict(lambda: deque(maxlen=10))
mute = {}                   # user -> unmute_time

# ================== CONFIG ==================
MAX_MSG = 6
WINDOW = 5
MUTE_TIME = 30
LOG_FILE = "server.log"

# ================== BAD WORDS (MULTI-LANG) ==================
BAD_WORDS = [
    "fuck","shit","bitch","asshole",
    "كس","زب","قحبه","شرموطه",
    "puta","mierda",
    "pute","merde",
    "сука","блять","хуй"
]
BAD_REGEX = re.compile("|".join(BAD_WORDS), re.IGNORECASE)

# ================== UTILS ==================
def log(text):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{time.ctime()}] {text}\n")
    print(text)

def spam(user):
    now = time.time()
    history[user].append(now)
    return len(history[user]) >= MAX_MSG and now - history[user][0] < WINDOW

def muted(user):
    return user in mute and time.time() < mute[user]

def clean(msg):
    return BAD_REGEX.sub("***", msg)

# ================== IGNORE HTTP REQUESTS ==================
async def ignore_http(path, request_headers):
    # أي طلب HTTP عادي (GET/HEAD) يتم تجاهله وإرجاع 200
    return HTTPStatus.OK, [], b"WebSocket server running\n"

# ================== MAIN HANDLER ==================
async def handler(ws):
    user, room = None, None
    try:
        async for raw in ws:
            try:
                data = json.loads(raw)
            except Exception:
                continue  # تجاهل أي رسالة ليست JSON صحيحة

            t = data.get("type")
            if t == "connect":
                user = data["username"]
                room = data["room"]
                clients[ws] = user
                rooms[room].add(ws)
                log(f"[+] {user} joined {room}")
                await ws.send(json.dumps({"type":"system","message":"Connected to Global Network"}))

            elif t == "message":
                msg = data["message"]

                if muted(user):
                    await ws.send(json.dumps({"type":"system","message":"🔇 You are muted"}))
                    continue

                if spam(user):
                    mute[user] = time.time() + MUTE_TIME
                    await ws.send(json.dumps({"type":"system","message":"⛔ Spam detected, muted"}))
                    log(f"[SPAM] {user}")
                    continue

                if BAD_REGEX.search(msg):
                    msg = clean(msg)
                    mute[user] = time.time() + 10
                    await ws.send(json.dumps({"type":"system","message":"🚫 Bad words blocked"}))
                    log(f"[SWEAR] {user}")

                payload = json.dumps({
                    "type":"message",
                    "username":user,
                    "message":msg
                })

                for c in list(rooms[room]):
                    if c.open:
                        await c.send(payload)

                log(f"[{room}] {user}: {msg}")

    except Exception as e:
        log(f"[ERROR] {e}")
    finally:
        if ws in clients:
            log(f"[-] {clients[ws]} disconnected")
            del clients[ws]
        if room and ws in rooms[room]:
            rooms[room].remove(ws)

# ================== START SERVER ==================
async def main():
    log("🚀 GLOBAL SERVER ONLINE (NO ENCRYPTION) FOR RENDER")
    async with websockets.serve(
        handler,
        HOST,
        PORT,
        process_request=ignore_http,  # يتجاهل HEAD/HTTP requests
        max_size=2**20
    ):
        await asyncio.Future()  # keep running

if __name__ == "__main__":
    asyncio.run(main())
