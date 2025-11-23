import datetime
import logging
import re

import scrapy

from . import base_spider
from .. import scrapy_util
from ..pipelines import JSONItem, JSONLItem, TextItem

WIKI_DOMAIN = "https://digimoncardgame.fandom.com"

SET_LIST_PATHS = [
    "/wiki/Booster_Packs",
    "/wiki/Starter_Decks",
]

CARD_LIST_PATHS = [
    "/wiki/Category:Promo",
]

KNOWN_ERRATA_WITHOUT_TABLES = [
    'https://digimoncardgame.fandom.com/wiki/BT6-084/Errata',  # Sistermon Ciel
]

# DEBUG_CARD = 'EX10-074'
# DEBUG_CARD = 'EX9-021'
DEBUG_CARD = 'BT6-084'
DEBUG_ON = True


def wiki_url(path: str | None) -> str | None:
  if not path:
    return None
  if path.startswith('/'):
    return WIKI_DOMAIN + path
  return path


class DCGWikiSpider(base_spider.BaseSpider):
  # scrapy properties
  name = "DCG Wiki Spider"

  # custom properties
  output_dir = scrapy_util.ROOT_DIR / 'dataSources' / 'dcgWiki'
  clear_output_dir = True

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

    self.seen_cards: set[str] = set()

  def request(self, path, callback, **kwargs):
    return scrapy.Request(WIKI_DOMAIN + path, callback=callback, **kwargs)

  async def start(self):
    for path in CARD_LIST_PATHS:
      yield self.card_list_item(path)
      yield self.request(path, self.parse_card_list)

    for path in SET_LIST_PATHS:
      yield self.request(path, self.parse_set_list)

  def card_list_item(self, path):
    sort = self.card_list_sort_value(path)
    return JSONLItem(path, sort, subpath=['[cardListPages].jsonl'])

  def card_list_sort_value(self, path):
    # examples:
    # /wiki/AD-01:_Advanced_Booster_Digimon_Generation
    # /wiki/BT-11:_Booster_Dimensional_Phase
    # /wiki/BT01-03:_Release_Special_Booster_Ver.1.0
    # /wiki/Category:Promo
    # /wiki/EX-11:_Extra_Booster_Dawn_of_Liberator
    # /wiki/RB-01:_Resurgence_Booster
    # /wiki/ST-14:_Advanced_Deck_Set_Beelzemon
    # /wiki/ST-7:_Starter_Deck_Gallantmon

    page_name = path.split('/')[-1]
    if ':_' not in page_name:
      return page_name

    set_long_id = page_name.split(':')[0]
    set_type, set_num = set_long_id.split('-')
    return f"{set_type}-{int(set_num):03d}"

  def parse_set_list(self, response):
    # Parses a page that has a list OF sets.
    # NOT a page that has a list of cards in a set.
    logging.info('GET %s | %s', response.status, response.url)

    paths = response.css('.NavFrame .setLink a::attr(href)').getall()

    for path in paths:
      yield self.card_list_item(path)
      yield self.request(path, self.parse_card_list)

  def parse_card_list(self, response):
    # Parses a page that has a list of cards.
    logging.info('GET %s | %s', response.status, response.url)

    card_paths = response.css('.cardlist th a::attr(href)').getall()

    for card_path in card_paths:
      card_num = card_path.split('/')[-1]
      set_id = card_num.split('-')[0]

      if '-' not in card_num:
        set_id = 'tokens'

      if (card_num in self.seen_cards):
        # duplicates will be encountered whenever an older card gets a new
        # alt art alongside a new set (as a box topper, etc).
        continue

      yield JSONLItem(card_path,
                      card_num,
                      subpath=[set_id, '[cardPages].jsonl'])

      self.seen_cards.add(card_num)

      if DEBUG_ON and card_num != DEBUG_CARD:
        continue

      yield self.request(card_path,
                         self.parse_card_page,
                         meta={
                             'card_num': card_num,
                             'set_id': set_id
                         })

  def parse_card_page(self, response):
    logging.debug('GET %s | %s', response.status, response.url)

    meta = response.meta
    card_num = meta.get('card_num')
    set_id = meta.get('set_id')

    header_categories = response.css('.page-header__categories').get()
    header_title = response.css('.page-header__title').get()
    body = response.css('.page__main .mw-body-content').get()

    text = "\n".join([
        "<html>",
        header_categories,
        header_title,
        body,
        "</html>",
    ])

    main_img_url = response.css('.ctable a.image img').xpath('@src').get()
    meta['main_img_url'] = main_img_url

    yield TextItem(data=text, subpath=[set_id, card_num, 'main.html'])

    # FIXME: call these sequentially, store everything in a single json file
    nav_paths = response.css('.ctable .info-navigation a::attr(href)').getall()
    for path in nav_paths:
      if '/gallery' in path.lower():
        yield self.request(path, self.parse_card_gallery, meta=meta)
      elif '/rulings' in path.lower():
        yield self.request(path, self.parse_card_rulings, meta=meta)
      elif '/errata' in path.lower():
        yield self.request(path, self.parse_card_errata, meta=meta)

  def parse_card_gallery(self, response):
    logging.debug('GET %s | %s', response.status, response.url)

    meta = response.meta
    card_num = meta.get('card_num')
    set_id = meta.get('set_id')

    imgs = []

    gallery_items = response.css('.wikia-gallery-item')
    for item in gallery_items:
      # placeholders (eg, mid-reveal cards or other languages that haven't been
      # populated yet)
      empty_img = item.css('.thumb a.image-no-lightbox').get()
      if empty_img:
        continue

      wiki_file_path = item.css('.thumb a::attr(href)').get()
      thumb_img = item.css('.thumb img.thumbimage')
      img_name = thumb_img.xpath('@data-image-key').get()
      thumb_url = item.css('.thumb img.thumbimage').xpath('@src').get()
      full_url = self.full_img_for_thumb(thumb_url)
      caption_text = thumb_img.xpath('@alt').get()
      caption_link = item.css('.lightbox-caption a::attr(href)').get()
      if 'cb=' in full_url:
        ts = full_url.split('cb=')[-1]
        upload_date = datetime.datetime.strptime(ts, '%Y%m%d%H%M%S').isoformat()

      imgs.append({
          'img_name': img_name,
          'img_url': full_url,
          'file_page': wiki_url(wiki_file_path),
          'upload_date': upload_date,
          'caption_text': caption_text,
          'caption_link': wiki_url(caption_link)
      })

    # FIXME: store this in a main json file instead
    data = {'images': imgs}
    yield JSONItem(data=data, subpath=[set_id, card_num, 'gallery_images.json'])

  @staticmethod
  def full_img_for_thumb(thumb_url: str) -> str:
    return re.sub(r'/scale-to-width-down/\d+', '', thumb_url)

  def parse_card_rulings(self, response):
    logging.debug('GET %s | %s', response.status, response.url)

    meta = response.meta
    card_num = meta.get('card_num')
    set_id = meta.get('set_id')

    ruling_items = response.css('.ruling')
    assert len(ruling_items) > 0, f"no rulings: {response.url}"

    rulings = []
    for item in ruling_items:
      question = ''.join(item.css('.question-body ::text').getall())
      answer = ''.join(item.css('.answer-body ::text').getall())
      ref = ''.join(item.css('sup ::text').getall())

      rulings.append({
          'question': question,
          'answer': answer,
          'reference': ref,
      })

    references = []
    reference_items = response.css('ol.references li')
    for i, item in enumerate(reference_items):
      ref_body = item.css('.reference-text')
      ref_number = i + 1  # not 0-based index
      ref_text = ''.join(ref_body.css('::text').getall())
      ref_link = ref_body.css('a::attr(href)').get()
      references.append({
          'num': ref_number,
          'text': ref_text,
          'link': wiki_url(ref_link),
      })

    data = {'rulings': rulings, 'references': references}
    yield JSONItem(data=data, subpath=[set_id, card_num, 'rulings.json'])

  def parse_card_errata(self, response):
    logging.debug('GET %s | %s', response.status, response.url)

    meta = response.meta
    card_num = meta.get('card_num')
    set_id = meta.get('set_id')

    tables = response.css('.errata-table')

    if len(tables) == 0:
      # we only expect this for a couple exceptional pages.
      # these pages are weird enough that we can just ignore them.
      if response.url in KNOWN_ERRATA_WITHOUT_TABLES:
        return

      assert False, f"no errata tables found for {response.url}"

    data = []

    for table in tables:
      before_text = ''.join(table.css('.before-text ::text').getall())
      after_text = ''.join(table.css('.after-text ::text').getall())

      before_thumb_url = table.css('.before-image img').xpath('@src').get()
      after_thumb_url = table.css('.after-image img').xpath('@src').get()

      item = {
          'before_text': before_text,
          'after_text': after_text,
          'after_image_url': self.full_img_for_thumb(after_thumb_url),
      }

      if before_thumb_url:
        item['before_image_url'] = self.full_img_for_thumb(before_thumb_url)

      data.append(item)

    # FIXME: store this in a main json file instead
    yield JSONItem(data=data, subpath=[set_id, card_num, 'errata.json'])
