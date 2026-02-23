import hashlib
import logging
from pathlib import Path
import re

import scrapy

from . import base_spider
from .. import scrapy_util
from ..pipelines import JSONItem, TextItem
from ...langs import Lang

REGIONS = {
    Lang.EN.abbr(): {
        'name': 'English',
        'domain': 'world.digimoncard.com',
        'card_list_url': 'https://world.digimoncard.com/cards',
    },
    f"{Lang.EN.abbr()}_asia": {
        'name': 'English (Asia)',
        'domain': 'en.digimoncard.com',
        'card_list_url': 'https://en.digimoncard.com/cardlist',
    },
    Lang.JP.abbr(): {
        'name': 'Japanese',
        'domain': 'digimoncard.com',
        'card_list_url': 'https://digimoncard.com/cards',
    }
}

# still using the old site layout as of 2026-02-23
LEGACY_REGIONS = [
    f"{Lang.EN.abbr()}_asia",
]

RARITIES = [
    'C',
    'U',
    'R',
    'SR',
    'SEC',
    'P',
    'UR',
]

get_text = scrapy_util.get_text


class DCGMainSiteSpider(base_spider.BaseSpider):
  # scrapy properties
  name = "DCG Main Site Spider"

  # custom properties
  output_dir = scrapy_util.ROOT_DIR / 'dataSources' / 'mainSite' / 'DCG'
  clear_output_dir = True

  def __init__(self, poll_only: bool = False, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.poll_only = poll_only
    if self.poll_only:
      logging.info("dcg_main spider running in poll-only mode")
      self.clear_output_dir = False

  async def start(self):
    for region, region_info in REGIONS.items():
      url = region_info['card_list_url']
      meta = {
          'region': region,
      }
      yield scrapy.Request(url, callback=self.parse_main_page, meta=meta)

  @scrapy_util.log_response_INFO
  def parse_main_page(self, response):
    region = response.meta['region']
    digest = hashlib.sha256(response.body).hexdigest()
    subpath = [region, 'card_list_hash']
    yield TextItem(digest, subpath=subpath)

    if self.poll_only:
      logging.info("Poll-only mode: stopping after hash")
      return

    product_links = response.css('#snaviList a')

    if not product_links:
      logging.error("No product links found on main page %s", response.url)
      return

    for link in product_links:
      url = response.urljoin(link.attrib['href'])
      yield scrapy.Request(url,
                           callback=self.parse_cards_page,
                           meta=response.meta)

  @scrapy_util.log_response_INFO
  def parse_cards_page(self, response):
    meta = response.meta

    set_name = scrapy_util.descendent_text(response.css('#maintitle'))
    if not set_name:
      logging.error("No set name found for %s", response.url)
      set_name = "unknown_set"

    short_code_re = r'[\[【]([A-Z0-9\-]+)[\]】]'
    short_code_match = re.search(short_code_re, set_name, re.IGNORECASE)
    if short_code_match:
      set_name = short_code_match.group(1)

    logging.info("Parsing %s %s card list (%s)", meta['region'], set_name,
                 response.url)

    for card in response.css('.image_lists_item'):
      card_id, data = card_data(card)

      if not card_id:
        logging.error("No card ID found for card in %s, card HTML:\n%s",
                      response.url, card)
        continue

      yield JSONItem(data,
                     subpath=[meta['region'], set_name, f'{card_id}.json'])


def card_data(card_html):
  data = {}

  # warning: alt arts are listed as separate cards, so we can't rely on
  # cardnum (eg EX11-018) as a unique id.

  # TODO (once asia-en moves to new site layout): clean up
  card_id = (card_html.css('.popupCol').attrib.get('id', '') or
             Path(card_html.css('.card_img img')[0].attrib['src']).stem)

  if not card_id:
    return None, None

  # TODO (once asia-en moves to new site layout): clean up
  title_fields = (card_html.css('.cardTitleList li') or
                  card_html.css('.cardinfo_head li'))
  for title_field in title_fields:
    key = title_field.attrib.get('class', '').split(' ')[0]
    val = get_text(title_field)
    if not key and val.upper() in RARITIES:
      key = 'rarity'
    data[key] = val

  for dl in card_html.css('dl'):
    dt = dl.css('dt')
    dd = dl.css('dd')

    key = normalize_key(get_text(dt))
    val = scrapy_util.get_texts_or_text(dd)

    if key and val:
      if dl.css('.cardFaqQuestion'):
        continue

      data[key] = val

      links = dd.css('ul a')
      if links:
        text = dl.css('dd::text').get().strip()
        urls = [link.attrib['href'] for link in links if 'href' in link.attrib]
        data[key] = [text, *urls]

  for info_box in card_html.css('.cardInfoBox'):
    if not info_box.css('.cardFaqListItem'):
      continue
    title = get_text(info_box.css('.cardInfoTit'))
    data[title] = [{
        'num': get_text(q.css('.cardFaqNum')),
        'date': get_text(q.css('.cardFaqDate')),
        'q': scrapy_util.get_texts_or_text(q.css('.cardFaqQuestion')),
        'a': scrapy_util.get_texts_or_text(q.css('.cardFaqAnswer'))
    } for q in info_box.css('.cardFaqListItem')]

  basic_fields = ['cardTitle', 'card_name']
  for field in basic_fields:
    elem = card_html.css(f'.{field}')
    if elem:
      data[field] = get_text(elem)

  # TODO (once asia-en moves to new site layout): clean up
  card_images = (card_html.css('.cardImgInner img') or
                 card_html.css('.card_img img'))
  data['imgSrc'] = card_images[0].attrib['src']

  return card_id, data


def normalize_key(key):
  key = key.replace('[', '').replace(']', '')

  return key
