"""Barcode scanning in the Telegram bot, end to end.

The real dispatcher talks to the real Flask API (same harness as
test_telegram_nutrition). The photo "download" is replaced by in-memory
bytes; decoding is the real zxing-cpp; Open Food Facts is the FakeOFF stub.
"""

import io
from datetime import datetime

import pytest
import zxingcpp
from aiogram.types import Chat, Document, Message, PhotoSize, Update
from PIL import Image

from backend.app.extensions import db
from backend.app.models import BarcodeLookup, Product
from telegram_bot import security
from telegram_bot.handlers import nutrition as handlers
from telegram_bot.services.barcode_reader import BarcodeImageError, decode_barcode
from web.tests.security.test_telegram_bot import ALICE
from web.tests.unit.test_nutrition_barcode import COLA, MISSING, NUTELLA, off  # noqa: F401
from web.tests.unit.test_telegram_nutrition import entries, food, start_breakfast, tg  # noqa: F401
from web.tests.unit.test_telegram_training import button, buttons, press, text


def barcode_jpeg(code: str, scale: int = 4) -> bytes:
    rendered = zxingcpp.create_barcode(code, zxingcpp.BarcodeFormat.EAN13).to_image(scale=scale)
    height, width = rendered.shape
    image = Image.frombuffer("L", (width, height), bytes(rendered))
    # A white margin and some size, like a real photo of a label.
    canvas = Image.new("L", (width + 200, height + 200), 255)
    canvas.paste(image, (100, 100))
    buffer = io.BytesIO()
    canvas.save(buffer, "JPEG", quality=90)
    return buffer.getvalue()


def blank_png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (400, 300), "white").save(buffer, "PNG")
    return buffer.getvalue()


@pytest.fixture
def photos(monkeypatch):
    """file_id -> bytes served by the patched download."""
    files = {}
    downloads = []

    async def download(bot, file_id):
        downloads.append(file_id)
        return files[file_id]

    monkeypatch.setattr(handlers, "_download_file", download)
    security.barcode_throttle._attempts.clear()
    files["downloads"] = downloads
    return files


def send_photo(h, file_id, size=50_000):
    return h.feed(Update(
        update_id=h._next(),
        message=Message(
            message_id=h._next(),
            date=datetime.now(),
            chat=Chat(id=ALICE.id, type="private"),
            from_user=ALICE,
            photo=[
                PhotoSize(file_id=file_id + "-small", file_unique_id="s", width=90, height=60, file_size=1000),
                PhotoSize(file_id=file_id, file_unique_id="b", width=1280, height=960, file_size=size),
            ],
        ),
    ))


def send_document(h, file_id, mime, size=50_000):
    return h.feed(Update(
        update_id=h._next(),
        message=Message(
            message_id=h._next(),
            date=datetime.now(),
            chat=Chat(id=ALICE.id, type="private"),
            from_user=ALICE,
            document=Document(file_id=file_id, file_unique_id="d", mime_type=mime, file_size=size),
        ),
    ))


# --- decoding -------------------------------------------------------------------------


def test_decoder_reads_ean13_from_a_jpeg():
    assert decode_barcode(barcode_jpeg(NUTELLA)) == NUTELLA


def test_decoder_returns_none_without_a_barcode():
    assert decode_barcode(blank_png()) is None


def test_decoder_rejects_non_images_and_oversized_files():
    with pytest.raises(BarcodeImageError):
        decode_barcode(b"%PDF-1.4 not an image")
    with pytest.raises(BarcodeImageError):
        decode_barcode(b"")
    with pytest.raises(BarcodeImageError):
        decode_barcode(b"\xff\xd8" + b"0" * (11 * 1024 * 1024))
    gif = io.BytesIO()
    Image.new("L", (10, 10)).save(gif, "GIF")
    with pytest.raises(BarcodeImageError):
        decode_barcode(gif.getvalue())


# --- flow ---------------------------------------------------------------------------------


def test_photo_of_external_product_is_previewed_imported_and_logged(tg, off, photos):
    off.found(NUTELLA)
    photos["photo-1"] = barcode_jpeg(NUTELLA)
    start_breakfast(tg)
    press(tg, "Штрихкод")
    assert "Надішліть фото штрихкоду" in text(tg)

    sent = len(tg.http.requests)
    send_photo(tg, "photo-1")

    # The largest size was downloaded; only the digits went to NosiFit.
    assert photos["downloads"] == ["photo-1"]
    assert tg.http.requests[sent:] == [("GET", f"/api/nutrition/products/barcode/{NUTELLA}")]
    preview = text(tg)
    assert "Горіхова паста" in preview
    assert "не перевірені" in preview
    assert "Open Food Facts" in preview and "ODbL" in preview
    assert "539" in preview
    assert Product.query.filter_by(barcode=NUTELLA).count() == 0

    press(tg, "Додати продукт")
    assert "додано до каталогу" in text(tg)
    tg.message("20")
    press(tg, "Зберегти")
    assert [(e.name, e.amount, e.calories) for e in entries(tg)] == [("Горіхова паста", 20, 108)]
    product = Product.query.filter_by(barcode=NUTELLA).one()
    assert product.source == "imported" and product.verified is False
    assert off.count() == 1


def test_known_product_goes_straight_to_the_amount(tg, off, photos):
    product = tg.food["oats"]
    product.barcode = COLA
    db.session.commit()
    photos["p"] = barcode_jpeg(COLA)
    start_breakfast(tg)

    send_photo(tg, "p")

    assert "Вівсянка" in text(tg)
    assert "Введіть кількість" in text(tg)
    tg.message("50")
    press(tg, "Зберегти")
    assert [(e.name, e.amount) for e in entries(tg)] == [("Вівсянка", 50)]
    assert off.count() == 0


def test_unreadable_photo_asks_for_a_clearer_one_or_the_digits(tg, off, photos):
    off.found(NUTELLA)
    photos["blank"] = blank_png()
    start_breakfast(tg)

    send_photo(tg, "blank")
    assert "Надішліть чіткіше фото" in text(tg)
    assert "цифри" in text(tg)

    # The digits typed by hand work the same way.
    tg.message(NUTELLA)
    assert "Горіхова паста" in text(tg)


def test_typed_digits_in_search_are_a_barcode_lookup(tg, off):
    off.found(NUTELLA)
    start_breakfast(tg)
    tg.message(NUTELLA)
    assert "Горіхова паста" in text(tg)
    assert tg.http.requests[-1] == ("GET", f"/api/nutrition/products/barcode/{NUTELLA}")


def test_invalid_digits_are_explained(tg, off):
    start_breakfast(tg)
    tg.message("1234567890123")
    assert "контрольною цифрою" in text(tg)
    assert off.count() == 0


def test_not_found_leads_to_an_own_product_with_the_barcode(tg, off, photos):
    off.missing(MISSING)
    start_breakfast(tg)
    tg.message(MISSING)
    assert "немає ні в каталозі NosiFit, ні в Open Food Facts" in text(tg)

    press(tg, "Створити свій продукт")
    assert MISSING in text(tg)
    tg.message("Домашній сир")
    press(tg, "Без бренду")
    for value in ("120", "16", "5", "2"):
        tg.message(value)
    press(tg, "пропустити")  # sugar
    press(tg, "пропустити")  # fiber
    own = Product.query.filter_by(owner_user_id=tg.user.id).one()
    assert own.barcode == MISSING
    assert own.sugar_per_100g is None and own.fiber_per_100g is None

    # Next time the scan finds the user's own product.
    tg.message("100")
    press(tg, "Зберегти")
    tg.callback("nutrition:add")
    tg.callback("nutrition:meal:breakfast")  # exists now: straight to products
    tg.message(MISSING)
    assert "Домашній сир" in text(tg)
    assert off.count(MISSING) == 1


def test_incomplete_external_data_cannot_be_added_directly(tg, off):
    off.found(NUTELLA, nutriments={"energy-kcal_100g": 539})
    start_breakfast(tg)
    tg.message(NUTELLA)
    assert "Бракує: білки, жири, вуглеводи" in text(tg)
    assert not [b for b in buttons(tg) if "Додати продукт" in b.text]
    assert button(tg, "Створити свій продукт")


def test_open_food_facts_outage_is_reported_and_not_cached(tg, off):
    import requests

    off.fail(NUTELLA, exc=requests.Timeout())
    start_breakfast(tg)
    tg.message(NUTELLA)
    assert "тимчасово недоступний" in text(tg)
    assert db.session.get(BarcodeLookup, NUTELLA) is None


def test_product_names_are_escaped(tg, off):
    off.found(NUTELLA, product_name_uk="<b>Паста</b> & <script>")
    start_breakfast(tg)
    tg.message(NUTELLA)
    assert "&lt;b&gt;Паста&lt;/b&gt; &amp; &lt;script&gt;" in text(tg)


def test_photo_limits(tg, off, photos):
    photos["big-small"] = blank_png()
    send_photo(tg, "big", size=30 * 1024 * 1024)
    # The oversized size is never downloaded; the smaller one is used instead.
    assert photos["downloads"] == ["big-small"]
    send_document(tg, "doc", "application/pdf")
    assert "JPEG, PNG або WebP" in text(tg)
    assert off.count() == 0


def test_photos_are_throttled_per_user(tg, off, photos):
    photos["p"] = blank_png()
    for _ in range(10):
        send_photo(tg, "p")
    send_photo(tg, "p")
    assert "Забагато фото" in text(tg)
    assert len(photos["downloads"]) == 10
