import logging

import scrapy

from . import base_spider
from .. import scrapy_util
from ..pipelines import JSONLItem

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
                         meta={'card_num': card_num})

  def parse_card_page(self, response):
    logging.debug('GET %s | %s', response.status, response.url)

    card_num = response.meta.get('card_num')

    header_categories = response.css('.page-header__categories').get()
    header_title = response.css('.page-header__title').get()
    body = response.css('.page__main .mw-body-content').get()

    pass  # FIXME

  def parse_card_wikitext(self, response):
    logging.debug('GET %s | %s', response.status, response.url)

    pass  # FIXME

  def parse_card_gallery(self, response):
    logging.debug('GET %s | %s', response.status, response.url)

    pass  # FIXME

  def parse_card_rulings(self, response):
    logging.debug('GET %s | %s', response.status, response.url)

    pass  # FIXME
