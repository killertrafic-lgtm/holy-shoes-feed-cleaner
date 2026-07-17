# Holy-Shoes Feed Cleaner

Автоматическая уникализация Google Shopping фида holy-shoes.com для каталога Meta Ads.

## Что делает

Скачивает оригинальный фид с holy-shoes.com (1458 товаров — каждый размер отдельной
позицией, плюс дубли выгрузки), схлопывает размерные варианты до **одной карточки на
модель** (~264) с чистым названием (без размера в конце), проставленным
`<g:item_group_id>`, `<g:size>` и `<g:google_product_category>`.

**URL очищенного фида:** `https://killertrafic-lgtm.github.io/holy-shoes-feed-cleaner/feed.xml`

## Как работает

1. **GitHub Actions** запускается каждый час по cron
2. Качает свежий фид с holy-shoes.com
3. Прогоняет через `scripts/filter_feed.py`
4. Сохраняет в `docs/feed.xml`
5. Коммитит в репо → GitHub Pages автоматически публикует

## Логика группировки

У holy-shoes (Horoshop) размер зашит в конце `<g:title>` («… Adidas Sandals Black White **40**»),
а `<g:id>` — сквозная нумерация без модели. Поэтому ключ модели = title с отрезанным
хвостовым размером (число 35–47 после пробела — чтобы не порезать модельные номера типа
Yeezy Slide / New Balance 530). Цвет всегда в названии → расцветки не слипаются.
Из группы остаётся представитель (ходовой размер 40/41).

## Безопасность

- Если после фильтрации < 50 моделей — публикация прерывается, старая версия остаётся
  (защита от битого оригинала на стороне Horoshop).

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
