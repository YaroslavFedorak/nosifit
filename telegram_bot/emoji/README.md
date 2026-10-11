# NosiFit Telegram custom emoji

The custom emoji set the NosiFit bot will use in its messages. The style follows the website: the Lucide-style round 2 px stroke from `web/app/static/js/icons/`, the dark rounded tile and line weight of the brand mark (`web/app/static/img/brand/`), and accent colours from `web/app/static/css/core/variables.css`.

| key | colour token | fallback |
|---|---|---|
| calories | `--nf-orange` | 🔥 |
| protein | `--nf-red` | 🥩 |
| fat | `--nf-yellow-soft` | 🥑 |
| carbs | `--nf-violet` | 🍞 |
| fiber | `--nf-green` | 🌾 |
| sugar | `--nf-violet-soft` | 🍬 |
| meal | `--nf-text-main` | 🍽️ |
| water | `--nf-accent-water` | 💧 |
| training | `--nf-accent-training` | 🏋️ |
| recovery | `--nf-accent-recovery` | ❤️ |
| sleep | `--nf-blue-soft` | 🌙 |

`icons.json` is the single source of truth for this mapping.

## Layout

```
src/*.svg          editable glyph sources (100×100 grid, currentColor, stroke 10)
icons.json         key → colour, fallback emoji, custom_emoji_id (null until registered)
build.py           renders PNGs and the preview, then validates them (stdlib + headless Chromium)
telegram_pack.py   eligibility check, pack creation, ID write-back (stdlib, uses TELEGRAM_BOT_TOKEN)
png/color/*.png    brand tile + accent glyph, 100×100 RGBA
png/mono/*.png     white glyph on transparent, 100×100 RGBA
preview.html/.png  every icon on light and dark chat backgrounds, at 64, 24 and 20 px
```

To rebuild after editing a source, run `python telegram_bot/emoji/build.py`. It fails if any output is not a 100×100 8-bit RGBA PNG with a transparent corner.

## Two packs, pick one

- **color** (`needs_repainting = false`): uses the brand tile and accent colours. Each icon sits on its own dark tile, so it reads the same in light and dark chats.
- **mono** (`needs_repainting = true`): Telegram repaints these to the current text colour, so they blend into the text of both themes.

## Telegram requirements (checked 2026-10-10)

- **Asset format:** a static custom emoji is a 100×100 PNG or WEBP (official Stickers docs). `InputSticker.format = "static"` takes .PNG or .WEBP (Bot API 10.3, as documented in aiogram 3.31).
- **Creating the pack:** use `createNewStickerSet` with `sticker_type="custom_emoji"`, or `/newemojipack` in @Stickers. Each sticker needs at least one standard emoji in `emoji_list`. Use the `fallback` column.
- **Sending:** in HTML parse mode (this bot's default) write `<tg-emoji emoji-id="ID">FALLBACK</tg-emoji>`. The inner text must be a valid standard emoji. Telegram shows it wherever custom emoji can't render, such as notifications and some forwards.
- **Eligibility:** the bot can send custom emoji if it bought an additional username on Fragment. It can also send them in messages sent directly to private, group and supergroup chats if the bot's owner has Telegram Premium. If neither applies, Telegram shows only the fallback emoji.

## Remaining steps

Every PNG was checked after downscaling to 20 and 24 px on light and dark backgrounds.

1. **Eligibility (do this first).** Run `python telegram_bot/emoji/telegram_pack.py check --chat-id <your chat id>`.
   It sends a test message with a real custom emoji (pass `--emoji-id`, or send the bot any custom emoji first with the bot stopped).
   It then reports whether Telegram kept the `custom_emoji` entity. Confirm by eye on a phone as well.
2. **Register.** Run `telegram_pack.py create --owner-id <your Telegram user id> --variant color` (or `mono`).
   This creates `nosifit_by_<bot>` and writes the real IDs into `icons.json`.
   If you made the pack by hand in @Stickers, run `telegram_pack.py ids --set <name>` instead.
3. **Integration is automatic.** `telegram_bot/custom_emoji.py` (registered in `bot.py`) wraps each fallback emoji in outgoing HTML messages with `<tg-emoji>` once its `custom_emoji_id` is set. Commit `icons.json` and redeploy the `bot` service.
   Test on Android and iOS, in both light and dark themes.
