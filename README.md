# Holy-Shoes Feed Cleaner

Автоматическая уникализация Google Shopping фида holy-shoes.com для каталога Meta Ads.

## Что делает

Скачивает оригинальный фид с holy-shoes.com (десятки тысяч позиций — каждый размер
отдельной позицией, плюс дубли выгрузки), схлопывает размерные варианты до **одной
карточки на модель** с чистым названием (без размера в конце), проставленным
`<g:item_group_id>`, `<g:size>` и `<g:google_product_category>`.

Фид сезонный: осень 2026 — **42 384 SKU кроссовок → 6 377 карточек**; летом был
ассортимент сандалі/капці (1458 → 264). Механика одна, правок кода при смене сезона не нужно.

**URL очищенного фида:** `https://killertrafic-lgtm.github.io/holy-shoes-feed-cleaner/feed.xml`

## Как работает

1. **GitHub Actions** запускается каждые 6 часов по cron
2. Качает свежий фид с holy-shoes.com (~130 МБ)
3. Прогоняет через `scripts/filter_feed.py`
4. Пишет `docs/feed.xml` (~18 МБ)
5. Деплоит через **Pages-артефакт** (`actions/deploy-pages`) — БЕЗ коммита фида в git
   (иначе история пухнет на 18 МБ за прогон)

## Логика группировки

У holy-shoes (Horoshop) размер зашит в конце `<g:title>` («… New Balance 9060 Grey **42**»),
а `<g:id>` — сквозная нумерация без модели. Поэтому ключ модели = title с отрезанным
хвостовым размером (число 35–47 **только после пробела** — чтобы не порезать модельные
номера: New Balance 9060/574/530, Yeezy 350, Air Max 90/95/97). Цвет всегда в названии →
расцветки не слипаются, unisex и жіночі — раздельно. Из группы остаётся представитель
(ходовой размер 40/41).

## Безопасность

- Если после фильтрации < 1000 моделей — публикация прерывается, старая версия остаётся
  (защита от частичного/битого оригинала на стороне Horoshop).

## Подключение к Meta

1. Открыть [Meta Commerce Manager](https://business.facebook.com/commerce_manager/)
2. Каталог → **Data Sources** → **Add items** → **Use bulk upload** → **Scheduled feed**
3. Вставить URL: `https://killertrafic-lgtm.github.io/holy-shoes-feed-cleaner/feed.xml`
4. Поставить **Update hourly**

## Ручной запуск

Вкладка Actions → «Update filtered feed» → «Run workflow».

## Локальный тест

```bash
python3 scripts/filter_feed.py
# → docs/feed.xml будет создан
```
