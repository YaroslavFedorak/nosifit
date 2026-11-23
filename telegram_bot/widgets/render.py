import html
import json
import re
import zlib
from functools import lru_cache
from pathlib import Path

from telegram_bot.i18n import translate

SOURCE = Path(__file__).with_name("today.html")

# Telegram refuses a widget over these (INPUT_MEDIA_WIDGET_TOO_LARGE); the
# compressed size is measured with zlib at level 9.
MAX_BYTES = 32768
MAX_COMPRESSED = 4096
LABELS = "fwsthkm"


def minify(source: str) -> str:
    """Drop comments and indentation. Line breaks stay: the script relies on them."""
    text = re.sub(r"<!--.*?-->", "", source, flags=re.S)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def compressed_size(text: str) -> int:
    return len(zlib.compress(text.encode("utf-8"), 9))


@lru_cache(maxsize=8)
def today_html(language: str) -> str:
    labels = {key: translate(language, f"w.label.{key}") for key in LABELS}
    page = (
        minify(SOURCE.read_text(encoding="utf-8"))
        .replace("{{labels}}", json.dumps(labels, ensure_ascii=False).replace("</", "<\\/"))
        .replace("{{title}}", html.escape(translate(language, "w.loading")))
        .replace("{{error}}", html.escape(translate(language, "w.error")))
    )
    if len(page.encode("utf-8")) > MAX_BYTES or compressed_size(page) > MAX_COMPRESSED:
        raise ValueError("The Today widget is over Telegram's size limit")
    return page
