"""Check bot eligibility and register the NosiFit custom emoji pack (stdlib only).

Reads TELEGRAM_BOT_TOKEN from the environment, like the bot itself.

  # 1. Eligibility: send a test message with a real custom emoji ID and see whether
  #    Telegram keeps the custom_emoji entity. Without --emoji-id, the newest custom
  #    emoji someone sent to the bot is taken from getUpdates (stop the bot first,
  #    polling conflicts with getUpdates).
  python telegram_bot/emoji/telegram_pack.py check --chat-id 123456789 [--emoji-id 5368...]

  # 2. Create the pack (the owner must be a real Telegram user who has started the bot)
  python telegram_bot/emoji/telegram_pack.py create --owner-id 123456789 --variant color

  # 3. Write the real IDs into icons.json (also works for a pack made in @Stickers)
  python telegram_bot/emoji/telegram_pack.py ids [--set nosifit_by_<bot>]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ICONS = ROOT / "icons.json"
VS16 = "️"


def api(method: str, fields: dict | None = None, files: dict[str, Path] | None = None) -> dict:
    token = os.environ.get("TELEGRAM_BOT_TOKEN") or sys.exit("TELEGRAM_BOT_TOKEN is not set")
    url = f"https://api.telegram.org/bot{token}/{method}"
    fields = {k: v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
              for k, v in (fields or {}).items() if v is not None}
    boundary = uuid.uuid4().hex
    body = bytearray()
    for name, value in fields.items():
        body += f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
    for name, path in (files or {}).items():
        body += (f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; filename="{path.name}"\r\n'
                 "Content-Type: image/png\r\n\r\n").encode() + path.read_bytes() + b"\r\n"
    body += f"--{boundary}--\r\n".encode()
    req = urllib.request.Request(url, bytes(body), {"Content-Type": f"multipart/form-data; boundary={boundary}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as e:
        data = json.load(e)
    if not data.get("ok"):
        sys.exit(f"{method} failed: {data.get('error_code')} {data.get('description')}")
    return data["result"]


def load_icons() -> dict:
    return json.loads(ICONS.read_text())


def default_set_name(prefix: str) -> str:
    return f"{prefix}_by_{api('getMe')['username']}"


def latest_custom_emoji_id() -> str:
    for update in reversed(api("getUpdates", {"allowed_updates": ["message"]})):
        msg = update.get("message") or {}
        for ent in msg.get("entities") or []:
            if ent.get("type") == "custom_emoji":
                return ent["custom_emoji_id"]
    sys.exit("No custom emoji found in recent updates. Stop the bot, send it any custom emoji, retry, "
             "or pass --emoji-id.")


def cmd_check(args) -> None:
    emoji_id = args.emoji_id or latest_custom_emoji_id()
    text = f'<tg-emoji emoji-id="{emoji_id}">⭐</tg-emoji> NosiFit custom emoji test'
    msg = api("sendMessage", {"chat_id": args.chat_id, "text": text, "parse_mode": "HTML"})
    kept = [e for e in msg.get("entities") or [] if e.get("type") == "custom_emoji"]
    print(json.dumps(msg.get("entities") or [], ensure_ascii=False))
    if kept:
        print("custom_emoji entity kept -> the bot can send custom emoji to this chat. "
              "Confirm visually on Android and iOS.")
    else:
        print("custom_emoji entity dropped -> users see only the fallback. The bot needs a Fragment "
              "username, or its owner needs Telegram Premium (private/group/supergroup chats only).")


def cmd_create(args) -> None:
    icons = load_icons()["icons"]
    name = args.set or default_set_name(args.prefix)
    stickers, files = [], {}
    for key, spec in icons.items():
        files[key] = ROOT / "png" / args.variant / f"{key}.png"
        stickers.append({"sticker": f"attach://{key}", "format": "static",
                         "emoji_list": [spec["fallback"]], "keywords": [key]})
    api("createNewStickerSet", {
        "user_id": str(args.owner_id), "name": name, "title": args.title,
        "sticker_type": "custom_emoji", "needs_repainting": args.variant == "mono", "stickers": stickers,
    }, files)
    print(f"created https://t.me/addemoji/{name}")
    write_ids(name)


def write_ids(name: str) -> None:
    data = load_icons()
    by_emoji = {spec["fallback"].replace(VS16, ""): key for key, spec in data["icons"].items()}
    found = {}
    for st in api("getStickerSet", {"name": name})["stickers"]:
        key = by_emoji.get((st.get("emoji") or "").replace(VS16, ""))
        if key and st.get("custom_emoji_id"):
            found[key] = st["custom_emoji_id"]
    missing = sorted(set(data["icons"]) - set(found))
    for key, emoji_id in found.items():
        data["icons"][key]["custom_emoji_id"] = emoji_id
    data["pack"] = name
    ICONS.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    print(f"wrote {len(found)} IDs to icons.json" + (f"; missing: {', '.join(missing)}" if missing else ""))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("--chat-id", required=True)
    c.add_argument("--emoji-id")
    c.set_defaults(func=cmd_check)
    n = sub.add_parser("create")
    n.add_argument("--owner-id", type=int, required=True)
    n.add_argument("--variant", choices=("color", "mono"), default="color")
    n.add_argument("--prefix", default="nosifit")
    n.add_argument("--set")
    n.add_argument("--title", default="NosiFit")
    n.set_defaults(func=cmd_create)
    i = sub.add_parser("ids")
    i.add_argument("--set")
    i.add_argument("--prefix", default="nosifit")
    i.set_defaults(func=lambda a: write_ids(a.set or default_set_name(a.prefix)))
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
