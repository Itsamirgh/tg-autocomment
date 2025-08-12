import asyncio
import json
import os
import re
from urllib.parse import urlparse
from telethon import TelegramClient, events
from telethon.tl.types import (
    MessageEntityUrl,
    MessageEntityTextUrl,
    MessageEntityMention,
    MessageEntityMentionName
)
from telethon.errors import FloodWaitError, ChannelPrivateError
from aiohttp import web

# Load settings
with open("config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

api_id       = cfg["api_id"]
api_hash     = cfg["api_hash"]
session_name = cfg["session_name"]
channels     = cfg["channels"]  # username -> dict or string

# Whitelist substrings (kept your Persian tokens + earlier whitelists)
ALLOWED_LINKS = [
    "t.me/ironetbot",
    "akharinkhabar.ir",
    "t.me/nikotinn_text",
    "🚀 فیلترشکن 🚀",
    "فیلترشکن",
    "پروکسی",
    "proxy?server",
    "t.me/proxy",
]

# optional: extra allowed mentions (lowercase, without @) — add usernames here if needed
ALLOWED_MENTIONS = {
    "akhbartelfori",
    "akharinkhabar",
    "twite_hub",
    "radiokocsher",
    "pastwrize",
    "teen_text",
    "fucktwit",
    "nikotiinn_text",
    "krolejudg",
    "angizeh_club",
    "minionshot",
    "khabar_fouri",
    "akhbare_fouri",
    "proxyhagh",
    "kosinuse",
    "badcandom",
    "kodex",
    "khateirat",
    "shakhnews",
    "alonews",
    "oqolmoqol",
    "angizeh_konkore",
}

client = TelegramClient(session_name, api_id, api_hash)

# track per-channel post count & rotation index
state = {username: {"count": 0, "index": 0} for username in channels}

# helpers
ZW_CHARS = ("\u200c", "\u200b", "\uFEFF")
def remove_zwsp(s: str) -> str:
    if not isinstance(s, str):
        s = str(s)
    for z in ZW_CHARS:
        s = s.replace(z, "")
    return s

def norm_username(s: str) -> str:
    s = remove_zwsp(s or "").strip()
    if s.startswith("@"):
        s = s[1:]
    s = re.sub(r'[^A-Za-z0-9_]', '', s)
    return s.lower()

def norm_token(s: str) -> str:
    s = remove_zwsp(s or "").strip().lower()
    return s.strip(" \t\n\r'\"()[]{}<>,؛،")

DOMAIN_RE = re.compile(r'([a-z0-9][a-z0-9\.-]+\.[a-z]{2,})', re.IGNORECASE)
TME_RE = re.compile(r'(t\.me/[A-Za-z0-9_+/=-]+)', re.IGNORECASE)
MENTION_RE = re.compile(r'@([A-Za-z0-9_]{1,64})')

def token_matches_channel(token: str, channel_username: str) -> bool:
    if not token or not channel_username:
        return False
    cu = channel_username.lower()
    cu_basic = re.sub(r'[^A-Za-z0-9_]', '', cu)
    tok = token.strip().lower()
    # direct substring
    if cu in tok:
        return True
    # parse domain-like tokens
    try:
        if not tok.startswith(("http://", "https://")):
            parsed = urlparse("http://" + tok)
        else:
            parsed = urlparse(tok)
        domain = (parsed.netloc or "").lower()
        path = (parsed.path or "").lower()
        if cu in domain or ('/' + cu) in path or path.strip('/') == cu:
            return True
    except Exception:
        pass
    tok_alnum = re.sub(r'[^A-Za-z0-9_]', '', tok)
    if not tok_alnum:
        return False
    if tok_alnum == cu_basic or tok_alnum.endswith(cu_basic):
        return True
    if len(cu_basic) >= 3 and tok_alnum.endswith(cu_basic[1:]):
        return True
    return False

def expand_url_token(token: str, orig_text: str, raw_text: str):
    """
    Try to find a longer/correct domain/url in orig_text/raw_text that contains token.
    Returns the best candidate (normalized) or original token if nothing found.
    """
    tok = norm_token(token)
    candidates = []
    # check MessageEntityTextUrl-like patterns via TME_RE and DOMAIN_RE on raw_text (cleaned)
    for m in TME_RE.findall(raw_text):
        candidates.append(norm_token(m))
    for m in DOMAIN_RE.findall(raw_text):
        candidates.append(norm_token(m))
    # Also search orig_text (un-cleaned) for domain-like substrings
    for m in DOMAIN_RE.findall(orig_text):
        candidates.append(norm_token(m))
    # choose best candidate that contains tok or where tok is suffix
    candidates = [c for c in candidates if c]
    if not candidates:
        return tok
    # prefer exact match
    for c in candidates:
        if tok == c:
            return c
    # prefer candidate that endswith tok or contains tok
    for c in sorted(candidates, key=lambda x: -len(x)):
        if tok in c or c in tok:
            return c
    return tok

def expand_mention_token(token: str, orig_text: str, raw_text: str):
    """
    Try to recover full mention from orig_text/raw_text if token is truncated.
    """
    tok = norm_username(token)
    mentions = []
    # find @mentions in orig_text and raw_text
    for m in MENTION_RE.findall(orig_text):
        mentions.append(norm_username(m))
    for m in MENTION_RE.findall(raw_text):
        mentions.append(norm_username(m))
    if not mentions:
        return tok
    mentions = list(dict.fromkeys(mentions))  # dedupe preserving order
    # exact or substring match
    for m in mentions:
        if tok == m:
            return m
    for m in mentions:
        if tok in m or m in tok:
            return m
    # fallback: longest mention
    return mentions[0]

@client.on(events.NewMessage(chats=list(channels.keys())))
async def comment_on_post(event):
    channel_key = event.chat.username
    channel_username = (channel_key or "").lower()
    msg = event.message

    orig_text = event.raw_text or ""        # use for slicing with ent.offset/ent.length
    raw = remove_zwsp(orig_text)            # cleaned version for regex searches / printing

    print("---- new post ----")
    print("channel_key:", channel_key)

    discovered_urls = []
    discovered_mentions = []
    hidden_mention_found = False

    # 1) Prefer MessageEntityTextUrl (contains target url)
    for ent in msg.entities or []:
        try:
            if isinstance(ent, MessageEntityTextUrl):
                u = getattr(ent, "url", None)
                if u:
                    discovered_urls.append(norm_token(u))
                else:
                    discovered_urls.append(norm_token(orig_text[ent.offset: ent.offset + ent.length]))
            elif isinstance(ent, MessageEntityUrl):
                try:
                    discovered_urls.append(norm_token(orig_text[ent.offset: ent.offset + ent.length]))
                except Exception:
                    discovered_urls.append(norm_token(getattr(ent, "url", "") or str(ent)))
            elif isinstance(ent, MessageEntityMention):
                try:
                    snippet = orig_text[ent.offset: ent.offset + ent.length]
                    m = MENTION_RE.search(snippet)
                    if m:
                        discovered_mentions.append(norm_username(m.group(0)))
                    else:
                        discovered_mentions.append(norm_username(snippet))
                except Exception:
                    discovered_mentions.append(norm_username(str(ent)))
            elif isinstance(ent, MessageEntityMentionName):
                hidden_mention_found = True
                print("Found hidden mention user_id:", getattr(ent, "user_id", None))
        except Exception as e:
            print("entity-extract-exc:", repr(e))

    # 2) Regex fallback on cleaned raw text for URLs and t.me
    for m in TME_RE.findall(raw):
        discovered_urls.append(norm_token(m))
    for dom in DOMAIN_RE.findall(raw):
        discovered_urls.append(norm_token(dom))

    # 3) Regex fallback for mentions (any @username in cleaned raw text)
    for m in MENTION_RE.findall(raw):
        discovered_mentions.append(m.lower())

    # attempt to expand/truthify tokens using orig_text/raw
    expanded_urls = []
    for u in discovered_urls:
        expanded = expand_url_token(u, orig_text, raw)
        expanded_urls.append(expanded)
    discovered_urls = expanded_urls

    expanded_mentions = []
    for m in discovered_mentions:
        expanded = expand_mention_token(m, orig_text, raw)
        expanded_mentions.append(expanded)

    # dedupe preserving order
    def dedupe(seq):
        seen = set()
        out = []
        for x in seq:
            if x and x not in seen:
                seen.add(x)
                out.append(x)
        return out

    discovered_urls = dedupe(discovered_urls)
    discovered_mentions = dedupe(discovered_mentions)

    print("discovered_urls:", discovered_urls)
    print("discovered_mentions:", discovered_mentions)
    if hidden_mention_found:
        print("Note: hidden mention entity present -> will SKIP")
        print("SKIP: hidden mention entity")
        return

    # decide about URLs: any external (not allowed, not channel) => skip
    for u in discovered_urls:
        allowed = False
        u_norm = norm_token(u)
        for a in ALLOWED_LINKS:
            if a.lower() in u_norm:
                allowed = True
                break
        if not allowed and token_matches_channel(u_norm, channel_username):
            allowed = True
        print(f" URL token: {u!r} -> allowed={allowed}")
        if not allowed:
            print(" => external URL found -> SKIP")
            return

    # decide about mentions: any mention that is not channel or allowed -> skip
    cu_norm = re.sub(r'[^a-z0-9_]', '', (channel_username or "").lower())
    for m in discovered_mentions:
        m_norm = re.sub(r'[^a-z0-9_]', '', (m or "").lower())
        allowed = False
        if cu_norm:
            if m_norm == cu_norm or cu_norm in m_norm or m_norm in cu_norm or token_matches_channel(m_norm, cu_norm):
                allowed = True
        if not allowed:
            for a in ALLOWED_MENTIONS:
                a_norm = re.sub(r'[^a-z0-9_]', '', a.lower())
                if not a_norm:
                    continue
                if a_norm == m_norm or a_norm in m_norm or m_norm in a_norm:
                    allowed = True
                    break
        print(f" Mention token: {m!r} -> allowed={allowed}")
        if not allowed:
            print(" => external mention found -> SKIP")
            return

    # === comment rotation logic (unchanged) ===
    cfg_val = channels.get(channel_key) or channels.get(channel_username)
    if isinstance(cfg_val, dict):
        messages = cfg_val.get("messages", [])
        freq = cfg_val.get("frequency", 1)
    else:
        messages = [cfg_val]
        freq = 1

    st = state.get(channel_key)
    if st is None:
        st = {"count": 0, "index": 0}
        state[channel_key] = st

    st["count"] += 1
    if st["count"] % freq != 0:
        print(f"⏭ Skipping #{st['count']} (freq={freq})")
        return

    idx = st["index"] % len(messages)
    reply = messages[idx]
    st["index"] += 1

    try:
        await asyncio.sleep(1)
        await client.send_message(entity=channel_key, message=reply, comment_to=msg.id)
        print(f"✅ Commented on {channel_username}:{msg.id} -> {repr(reply)[:120]}")
    except FloodWaitError as e:
        print(f"⏰ FloodWait: wait {e.seconds}s")
        await asyncio.sleep(e.seconds + 1)
    except ChannelPrivateError:
        print("❌ Join the discussion group first.")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

# Health
async def handle_health(request):
    return web.Response(text="OK")

async def main():
    port = int(os.environ.get("PORT", 8080))
    app  = web.Application()
    app.router.add_get("/health", handle_health)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", port).start()
    print(f"🌐 Health on http://0.0.0.0:{port}/health")
    print("🚀 Bot starting…")
    await client.start()
    print("✅ Bot is online")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
