#!/usr/bin/env python3
r"""
Holy-Shoes Feed Cleaner

Скачивает Google Shopping фид holy-shoes.com (Horoshop) и схлопывает
размерные дубли ДО ОДНОЙ карточки на модель — чтобы каталог Meta показывал
уникальные товары, а не по 10 одинаковых карточек одной пары в разных размерах.

Проблема, которую чиним:
  Horoshop выгружает КАЖДЫЙ размер отдельным <item> с уникальным g:id и БЕЗ
  g:item_group_id. Размер зашит в конце g:title ("... New Balance 9060 Grey 42"),
  а g:id — сквозная нумерация, модель в нём не закодирована.
  Хуже: один и тот же размер модели встречается по 3-4 раза (дубли выгрузки).
  Meta видит десятки тысяч «разных» товаров вместо тысяч моделей → каталог/карусель
  забиты дублями одной пары.

  Фид сезонный: ассортимент меняется (лето — сандалі/капці, осень — кроссовки),
  но механика одна. Модельные номера (9060, 574, 350, Air Max 90/95/97) НЕ путаются
  с размером: размер = хвостовое число 35..47 ТОЛЬКО после пробела.

Логика группировки (выведена из РЕАЛЬНОГО фида, не из головы):
  Ключ модели = g:title с отрезанным ХВОСТОВЫМ размером.
    "Adidas Sandals Black White 40" → модель "Adidas Sandals Black White", размер 40
    "Adidas Adilette Sandal Red White" (без числа) → модель = сам title, размер ""
  Размер = хвостовое число 35..47 (+.5) ТОЛЬКО после пробела — чтобы НЕ порезать
  модельные номера (Yeezy Slide, New Balance 530, Air Max и т.п.).
  Цвет всегда в названии → разные расцветки одной модели НЕ слипаются.

Из каждой группы оставляем ОДНОГО представителя (ходовой размер 40/41 в приоритете),
чистим ему title от размера и проставляем:
  g:item_group_id             — стабильный хеш модели
  g:size                      — размер представителя
  g:google_product_category   — "Apparel & Accessories > Shoes" (весь фид — обувь)

Safety check: если после фильтрации < MIN_ITEMS товаров — не публикуем,
сохраняется предыдущая версия (защита от битого/частичного оригинала Horoshop).

Проверено:
  2026-07-17 (лето):  1 458 SKU  →   264 карточки
  2026-07-21 (осень): 42 384 SKU → 6 377 карточек кроссовок (та же логика без правок)
"""

import hashlib
import os
import re
import sys
import urllib.request
from collections import defaultdict
from xml.etree import ElementTree as ET

SOURCE_FEED_URL = (
    "https://holy-shoes.com/marketplace-integration/google-feed/"
    "b573742161465e3a2deba881f9129298?langId=3"
)
OUTPUT_PATH = os.environ.get("OUTPUT_PATH", "docs/feed.xml")
MIN_ITEMS_THRESHOLD = 1000  # ниже = не публикуем (частичный/битый фид Horoshop)

NS = "http://base.google.com/ns/1.0"
ET.register_namespace("g", NS)

# Весь фид holy-shoes — обувь (кроссовки / летом сандалі-капці). Одна категория Google.
GOOGLE_CATEGORY = "Apparel & Accessories > Shoes"

# Хвостовой размер: число 35..47 (+ опц. .5) ТОЛЬКО после пробела в конце строки.
# Пробел обязателен → "New Balance 530" / "Yeezy Slide" не считаются размером.
SIZE_RE = re.compile(r"\s+(3[5-9]|4[0-7])(?:[.,]5)?\s*$")

# Приоритет размера при выборе представителя (ходовые в середине).
SIZE_PRIORITY = {
    s: i for i, s in enumerate(
        ["40", "41", "39", "42", "38", "43", "37", "44", "36", "45", "46", "35", "47"]
    )
}


def split_title(title: str):
    """('Adidas Sandals Black White 40') → ('Adidas Sandals Black White', '40').
    Если хвостового размера нет — вернёт (title, '')."""
    title = (title or "").strip()
    m = SIZE_RE.search(title)
    if m:
        size = m.group(0).strip().replace(",", ".")
        model = SIZE_RE.sub("", title).strip()
        return model, size
    return title, ""


def download_feed(url: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; HolyShoesFeedCleaner/1.0)"},
    )
    with urllib.request.urlopen(req, timeout=300) as resp:  # 130+ МБ — нужен запас
        return resp.read()


def add_or_replace(item: ET.Element, tag: str, value: str):
    qname = f"{{{NS}}}{tag}"
    existing = item.find(qname)
    if existing is not None:
        existing.text = value
    else:
        el = ET.SubElement(item, qname)
        el.text = value


def filter_feed(xml_bytes: bytes):
    """Схлопывает размерные варианты до ОДНОГО представителя на модель."""
    root = ET.fromstring(xml_bytes)
    channel = root.find("channel")
    if channel is None:
        raise RuntimeError("Невалидный фид: нет <channel>")

    items = channel.findall("item")
    original_count = len(items)

    # 1. Группируем по ключу модели (title без хвостового размера).
    groups: dict[str, list] = defaultdict(list)
    for it in items:
        title_el = it.find(f"{{{NS}}}title")
        gid_el = it.find(f"{{{NS}}}id")
        if title_el is None or not (title_el.text or "").strip():
            continue
        model, size = split_title(title_el.text)
        gid = (gid_el.text or "").strip() if gid_el is not None else ""
        groups[model].append((size, gid, it))

    # 2. Из каждой группы — один представитель (ходовой размер, затем по id).
    kept_items: list[ET.Element] = []
    for model, candidates in groups.items():
        candidates.sort(key=lambda c: (SIZE_PRIORITY.get(c[0], 99), c[1]))
        size, gid, chosen = candidates[0]
        add_or_replace(chosen, "title", model)  # чистое имя карточки (без размера)
        add_or_replace(chosen, "item_group_id", hashlib.md5(model.encode()).hexdigest()[:12])
        if size:
            add_or_replace(chosen, "size", size)
        add_or_replace(chosen, "google_product_category", GOOGLE_CATEGORY)
        kept_items.append(chosen)

    # 3. Удаляем все товары, вставляем только представителей.
    for it in items:
        channel.remove(it)
    for it in kept_items:
        channel.append(it)

    stats = {
        "original": original_count,
        "filtered": len(kept_items),
        "ratio": f"{len(kept_items) / original_count * 100:.1f}%" if original_count else "0%",
    }
    return ET.ElementTree(root), stats


def main():
    print(f"→ Скачиваю фид: {SOURCE_FEED_URL}")
    xml_bytes = download_feed(SOURCE_FEED_URL)
    print(f"  получено: {len(xml_bytes):,} байт")

    print("→ Схлопываю размерные варианты до 1 карточки на модель...")
    tree, stats = filter_feed(xml_bytes)

    print(f"  товаров (SKU) в исходнике: {stats['original']}")
    print(f"  моделей (карточек) на выходе: {stats['filtered']}  ({stats['ratio']} от исходного)")

    if stats["filtered"] < MIN_ITEMS_THRESHOLD:
        print(
            f"✗ ОШИБКА: моделей {stats['filtered']} (< порога {MIN_ITEMS_THRESHOLD}). "
            f"Не публикую, прерываюсь."
        )
        sys.exit(1)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    tree.write(OUTPUT_PATH, xml_declaration=True, encoding="utf-8")

    out_size = os.path.getsize(OUTPUT_PATH)
    print(f"✓ Сохранено: {OUTPUT_PATH} ({out_size:,} байт)")


if __name__ == "__main__":
    main()
