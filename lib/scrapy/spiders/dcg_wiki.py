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

DEBUG_CARD = 'EX10-074'
DEBUG_ON = True


def wiki_url(path: str | None) -> str | None:
  if not path:
    return None
  return WIKI_DOMAIN + path


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

    body = response.css('.page__main .mw-body-content').get()
    text = "\n".join([
        "<html>",
        body,
        "</html>",
    ])

    # yield TextItem(data=text, subpath=[set_id, card_num, 'gallery.html'])

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
      full_url = re.sub(r'/scale-to-width-down/\d+', '', thumb_url)
      caption_text = thumb_img.xpath('@alt').get()
      caption_link = item.css('.lightbox-caption a::attr(href)').get()
      if 'cb=' in full_url:
        ts = full_url.split('cb=')[-1]
        upload_date = datetime.datetime.strptime(ts, '%Y%m%d%H%M%S').isoformat()

      imgs.append({
          'img_name': img_name,
          'full_url': full_url,
          'file_page': wiki_url(wiki_file_path),
          'upload_date': upload_date,
          'caption_text': caption_text,
          'caption_link': wiki_url(caption_link)
      })

    yield JSONItem(data={'images': imgs},
                   subpath=[set_id, card_num, 'gallery_images.json'])

  def parse_card_rulings(self, response):
    logging.debug('GET %s | %s', response.status, response.url)

    meta = response.meta
    card_num = meta.get('card_num')
    set_id = meta.get('set_id')

    body = response.css('.page__main .mw-body-content').get()
    text = "\n".join([
        "<html>",
        body,
        "</html>",
    ])

    yield TextItem(data=text, subpath=[set_id, card_num, 'rulings.html'])

  def parse_card_errata(self, response):
    logging.debug('GET %s | %s', response.status, response.url)

    meta = response.meta
    card_num = meta.get('card_num')
    set_id = meta.get('set_id')

    body = response.css('.page__main .mw-body-content').get()
    text = "\n".join([
        "<html>",
        body,
        "</html>",
    ])

    yield TextItem(data=text, subpath=[set_id, card_num, 'errata.html'])
