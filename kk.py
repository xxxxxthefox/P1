# ULTRA GLOBAL ROBLOX CHAT SERVER (HTTP API)
# OWNER: xxxxxthefox
# ⚡ FastAPI + Rooms + Anti-Spam + Anti-Swear + Logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import asyncio, time, re
from collections import defaultdict, deque
import uvicorn

app = FastAPI()

# ================== DATA STRUCTURES ==================
clients = defaultdict(list)  # room -> list of asyncio.Queue (for broadcasting)
messages = defaultdict(list) # room -> list of messages
history = defaultdict(lambda: deque(maxlen=10))
mute = {}                     # user -> unmute_time

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

# ================== ENDPOINTS ==================

@app.post("/send")
async def send_message(data: dict):
    username = data.get("username", "Unknown")
    room = data.get("room", "global")
    msg = data.get("message", "")

    if muted(username):
        return {"status":"error","message":"🔇 You are muted"}

    if spam(username):
        mute[username] = time.time() + MUTE_TIME
        log(f"[SPAM] {username} in {room}")
        return {"status":"error","message":"⛔ Spam detected, muted"}

    if BAD_REGEX.search(msg):
        msg = clean(msg)
        mute[username] = time.time() + 10
        log(f"[SWEAR] {username} in {room}")

    # سجل الرسالة
    messages[room].append({"username": username, "message": msg, "time": time.time()})
    log(f"[{room}] {username}: {msg}")

    # أرسل لكل العملاء المسجلين في الغرفة
    for queue in clients[room]:
        await queue.put({"username": username, "message": msg})

    return {"status":"ok"}

@app.get("/recv")
async def recv_messages(room: str):
    # جلب آخر 50 رسالة للغرفة
    msgs = messages[room][-50:]
    return {"messages": msgs}

@app.websocket("/ws/{room}/{username}")
async def websocket_endpoint(websocket, room: str, username: str):
    import websockets
    await websocket.accept()
    queue = asyncio.Queue()
    clients[room].append(queue)
    log(f"[+] {username} connected to room {room}")

    try:
        while True:
            # تحقق إذا وصل أي رسالة جديدة للغرفة
            done, _ = await asyncio.wait(
                [queue.get(), websocket.receive_text()],
                return_when=asyncio.FIRST_COMPLETED,
            )

            for task in done:
                result = task.result()
                if isinstance(result, str):
                    # رسالة من العميل (يمكن تجاهلها أو إعادة إرسال)
                    pass
                else:
                    # رسالة من السيرفر
                    await websocket.send_json(result)

    except Exception as e:
        log(f"[ERROR] WebSocket {username}: {e}")
    finally:
        clients[room].remove(queue)
        log(f"[-] {username} disconnected from room {room}")

# ================== RUN SERVER ==================
if __name__ == "__main__":
    log("🚀 GLOBAL HTTP API SERVER ONLINE FOR ROBLOX")
    uvicorn.run(app, host="0.0.0.0", port=8765)
