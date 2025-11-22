import logging

import scrapy

from . import base_spider
from .. import scrapy_util

WIKI_DOMAIN = "https://digimoncardgame.fandom.com"

SET_LIST_PATHS = [
    "/wiki/Booster_Packs",
    "/wiki/Starter_Decks",
]

CARD_LIST_PATHS = [
    "/wiki/Category:Promo",
]


class DCGWikiSpider(base_spider.BaseSpider):
  # scrapy properties
  name = "DCG Wiki Spider"

  # custom properties
  output_dir = scrapy_util.ROOT_DIR / 'dataSources' / 'dcgWiki'
  clear_output_dir = True

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

    self.seen_cards: set[str] = set()

  async def start(self):
    for path in CARD_LIST_PATHS:
      yield self.card_list_item(path)
      yield self.card_list_request(path)

    for path in SET_LIST_PATHS:
      yield self.set_list_request(path)

  def card_list_request(self, path):
    return scrapy.Request(
        WIKI_DOMAIN + path,
        callback=self.parse_card_list,
    )

  def card_list_item(self, path):
    return {
        'jsonl_subpath': ['[cardListPages].jsonl'],
        'jsonl_data': path,
        'jsonl_sort': self.card_list_sort(path),
    }

  def card_list_sort(self, path):
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

  def set_list_request(self, path):
    return scrapy.Request(
        WIKI_DOMAIN + path,
        callback=self.parse_set_list,
    )

  def parse_set_list(self, response):
    # Parses a page that has a list OF sets.
    # NOT a page that has a list of cards in a set.
    logging.info('GET %s | %s', response.status, response.url)

    paths = response.css('.NavFrame .setLink a::attr(href)').getall()

    for path in paths:
      yield self.card_list_item(path)
      yield self.card_list_request(path)

  def parse_card_list(self, response):
    # Parses a page that has a list of cards.
    logging.info('GET %s | %s', response.status, response.url)

    paths = response.css('.cardlist th a::attr(href)').getall()

    for path in paths:
      card_num = path.split('/')[-1]
      set_id = card_num.split('-')[0]

      if '-' not in card_num:
        set_id = 'tokens'

      if (card_num in self.seen_cards):
        # duplicates will be encountered whenever an older card gets a new
        # alt art alongside a new set (as a box topper, etc).
        continue

      # FIXME: any reason to actually store these lists?
      yield {
          'jsonl_subpath': [set_id, '[cardPages].jsonl'],
          'jsonl_data': path,
          'jsonl_sort': card_num,
      }

      self.seen_cards.add(card_num)

      # yield scrapy.Request(
      #     full_url,
      #     callback=self.parse_card_page,
      # )

  def parse_card_page(self, response):
    logging.debug('GET %s | %s', response.status, response.url)

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
