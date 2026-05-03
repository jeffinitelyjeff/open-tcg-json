from collections import defaultdict
from datetime import datetime
import functools
import logging
import re
from urllib.parse import urlencode, urlparse, unquote

import scrapy
from scrapy.http import HtmlResponse
from scrapy.selector import Selector

from . import base_spider
from .. import scrapy_util
from ..pipelines import JSONItem, JSONLItem, TextItem
from ...langs import Lang

WIKI_DOMAIN = "https://digimoncardgame.fandom.com"
WIKI_API = f"{WIKI_DOMAIN}/api.php"

SET_LIST_PATHS = [
    "/wiki/Booster_Packs",
    "/wiki/Starter_Decks",
]

CARD_LIST_PATHS = [
    "/wiki/Category:Promo",
]

KNOWN_ERRATA_WITHOUT_TABLES = [
    'https://digimoncardgame.fandom.com/wiki/BT6-084/Errata',  # Sistermon Ciel
    'https://digimoncardgame.fandom.com/wiki/ST12-13/Errata',  # Sistermon Ciel
    'https://digimoncardgame.fandom.com/wiki/BT7-083/Errata',  # Sistermon Ciel (Awakened)
]

DEBUG_CARDS = set([
    'BT6-084',
    'EX10-074',
    'EX9-021',
    'Familiar_Token',
])
DEBUG_ON = False

MANUAL_FIELD_OVERRIDES = {
    'japanese': 'nameJapanese',
    'translated': 'nameTranslated',
    'colour': 'color',
    'card effect(s)': 'cardEffects',
    'alt. digivolution requirements': 'altDigivolutionRequirements',
}


def wiki_url(path: str | None) -> str | None:
  if not path:
    return None
  if path.startswith('/'):
    return WIKI_DOMAIN + path
  return path


def camel_case(s: str) -> str:
  override = MANUAL_FIELD_OVERRIDES.get(s.lower())
  if override is not None:
    return override

  parts = re.split(r'[\s_-]+', s)
  return parts[0].lower() + ''.join(p.title() for p in parts[1:])


get_text = scrapy_util.get_text


class DCGWikiSpider(base_spider.BaseSpider):
  # scrapy properties
  name = "DCG Wiki Spider"

  # custom properties
  output_dir = scrapy_util.ROOT_DIR / 'dataSources' / 'dcgWiki'
  clear_output_dir = True
  custom_settings = {'AUTOTHROTTLE_TARGET_CONCURRENCY': 1.0}

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

    self.seen_cards: set[str] = set()

  def request(self, path, callback, **kwargs):
    title = self._page_title_from_path(path)
    assert title, f"invalid wiki path: {path}"
    return self._api_parse_request(title, callback, **kwargs)

  def _api_parse_request(self, title: str, callback, **kwargs):
    params = {
        'action': 'parse',
        'format': 'json',
        'formatversion': '2',
        'prop': 'text',
        'page': title,
    }
    url = f"{WIKI_API}?{urlencode(params)}"
    wrapped_callback = self._wrap_parse_callback(callback)
    return scrapy.Request(url, callback=wrapped_callback, **kwargs)

  def _wrap_parse_callback(self, callback):

    @functools.wraps(callback)
    def handler(api_response, *args, **kwargs):
      data = api_response.json()
      parse_data = data.get('parse')
      assert parse_data, f"no parse data for {api_response.url}"
      html = parse_data.get('text') or ''
      if isinstance(html, dict):
        html = html.get('*', '')
      assert html, f"empty html for {api_response.url}"

      selector = Selector(text=html)
      redirect_href = selector.css(
          '.redirectMsg .redirectText a::attr(href)').get()
      if redirect_href:
        redirect_title = self._page_title_from_path(redirect_href)
        current_title = parse_data.get('title')
        if redirect_title and redirect_title != current_title:
          new_meta = dict(api_response.request.meta or {})
          chain = list(new_meta.get('_redirect_chain', []))
          if redirect_title in chain:
            raise RuntimeError(
                f"Redirect loop detected ({chain} -> {redirect_title})")
          chain.append(redirect_title)
          new_meta['_redirect_chain'] = chain
          return self._api_parse_request(redirect_title,
                                         callback,
                                         meta=new_meta)

      page_title = parse_data.get('title', '')
      page_url = wiki_url(f"/wiki/{page_title.replace(' ', '_')}")

      html_response = HtmlResponse(url=page_url or api_response.url,
                                   body=html.encode('utf-8'),
                                   encoding='utf-8',
                                   request=api_response.request,
                                   status=api_response.status)

      return callback(html_response, *args, **kwargs)

    return handler

  def _page_title_from_path(self, path: str | None) -> str | None:
    if not path:
      return None

    if path.startswith(WIKI_DOMAIN):
      parsed = urlparse(path)
      path = parsed.path

    path = path.split('?', 1)[0]
    path = path.split('#', 1)[0]

    if path.startswith('/wiki/'):
      path = path[len('/wiki/'):]
    path = path.lstrip('/')

    return unquote(path) if path else None

  async def start(self):
    for path in CARD_LIST_PATHS:
      yield self.card_list_item(path)
      yield self.request(path, self.parse_card_list)

    for path in SET_LIST_PATHS:
      yield self.request(path, self.parse_set_list)

  def card_list_item(self, path):
    sort = self.card_list_sort_value(path)
    yield JSONLItem(path, sort, subpath=['[cardListPages].jsonl'])

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

  @scrapy_util.log_response_INFO
  def parse_set_list(self, response):
    # Parses a page that has a list OF sets.
    # NOT a page that has a list of cards in a set.

    paths = response.css('.NavFrame .setLink a::attr(href)').getall()

    for path in paths:
      yield self.card_list_item(path)
      yield self.request(path, self.parse_card_list)

  @scrapy_util.log_response_INFO
  def parse_card_list(self, response):
    # Parses a page that has a list of cards.
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
      self.seen_cards.add(card_num)

      # yield JSONLItem(card_path,
      #                 card_num,
      #                 subpath=[set_id, '[cardPages].jsonl'])

      if DEBUG_ON and card_num not in DEBUG_CARDS:
        continue

      # ignore links for tokens that just go to the generic token page.
      if card_path.endswith('/wiki/Token'):
        continue

      yield self.request(card_path,
                         self.parse_card_page,
                         meta={
                             'card_num': card_num,
                             'set_id': set_id
                         })

  @scrapy_util.log_response_INFO
  def parse_card_page(self, response):
    response = response.replace(
        body=re.sub(r"<br\s*/?>", '\n', response.text).encode())

    meta = response.meta
    set_id = meta.get('set_id')

    card_tables = response.css('.ctable')
    assert len(card_tables) > 0, f"no ctable found"

    # TODO: handle special case with tabber (BT6-084, BT23-077)
    multi_tabs = len(card_tables) > 1
    card_table = card_tables[0]

    card_data = self.parse_key_value_table(card_table.css('.info-main'),
                                           ignore_header=True)

    image_url = card_table.css('.image img').xpath('@src').get()
    card_data['image'] = image_url

    # automatically append for key collisions
    for info_table in card_table.css('table')[1:]:
      new_data = self.parse_key_value_table(info_table)
      for key, val in new_data.items():
        old_val = card_data.get(key)
        if key in card_data:
          if isinstance(old_val, list):
            card_data[key].append(val)
          else:
            card_data[key] = [old_val, val]
        else:
          card_data[key] = val

    card_data['setData'] = {}
    if set_id != 'tokens':
      for lang in [Lang.EN, Lang.JP, Lang.CH, Lang.KR]:
        abbr = lang.abbr().lower()
        cls_name = f'.settable-{abbr}'
        tables = response.css(cls_name)
        if lang == Lang.EN or lang == Lang.JP:
          assert len(tables) > 0, f"missing {cls_name}"
        assert multi_tabs or len(tables) <= 1, f"multiple {cls_name}"
        if len(tables) == 1:
          data = self.parse_generic_col_table(tables[0])
          card_data['setData'][abbr] = data

    nav_paths = card_table.css('.info-navigation a::attr(href)').getall()
    pending_subpages = []
    for path in nav_paths:
      if '/gallery' in path.lower():
        pending_subpages.append(path)
      elif '/rulings' in path.lower():
        pending_subpages.append(path)
      elif '/errata' in path.lower():
        pending_subpages.append(path)

    meta['card_data'] = card_data
    meta['pending_subpages'] = pending_subpages
    yield self.request_or_result(meta)

  def request_or_result(self, meta):
    pending_subpages = meta.get('pending_subpages', [])
    card_data = meta.get('card_data')
    card_num = meta.get('card_num')
    set_id = meta.get('set_id')

    if pending_subpages:
      next_path = pending_subpages.pop()
      return self.request(next_path, self.parse_card_subpage, meta=meta)
    else:
      return JSONItem(card_data, subpath=[set_id, f'{card_num}.json'])

  @scrapy_util.log_response_INFO
  def parse_card_subpage(self, response):
    meta = response.meta
    card_data = meta.get('card_data')

    url = response.url

    if '/gallery' in url.lower():
      card_data['galleryImages'] = self.parse_card_gallery(response)
    elif '/rulings' in url.lower():
      card_data['rulings'] = self.parse_card_rulings(response)
    elif '/errata' in url.lower():
      card_data['errata'] = self.parse_card_errata(response)
    else:
      assert False, f"unexpected subpage url: {url}"

    yield self.request_or_result(meta)

  @staticmethod
  def parse_key_value_table(table,
                            ignore_header=False) -> tuple[str | None, dict]:
    data = defaultdict(dict)
    header_key = None

    rows = table.css('tr')
    for row in rows:
      header_cell = row.css('th')
      if header_cell and not row.css('td'):
        if not ignore_header:
          assert len(header_cell) == 1, f"expected 1 header cell per row"
          header_text = get_text(header_cell[0])
          header_key = camel_case(header_text)
        continue

      cells = row.css('th') + row.css('td')

      if len(cells) == 1 and header_key:
        data[header_key] = get_text(cells[0])
      elif len(cells) == 2:
        key_text = camel_case(get_text(cells[0]))
        val_text = get_text(cells[1])
        if header_key:
          data[header_key][key_text] = val_text
        else:
          data[key_text] = val_text
      else:
        assert False, f"unexpected table row: {row}"

    return dict(data)

  @staticmethod
  def parse_generic_col_table(table) -> list[dict]:
    data = []
    header_cells = table.css('tr th')
    headers = [camel_case(get_text(h)) for h in header_cells]

    rows = table.css('tr')[1:]  # skip header row
    for row in rows:
      item = {}
      cells = row.css('td')
      for i, cell in enumerate(cells):
        assert i < len(headers), "more table cells than headers"
        header = headers[i]

        cell_text = get_text(cell)
        cell_link = cell.css('a::attr(href)').get()
        if cell_link:
          item[header] = {'text': cell_text, 'link': wiki_url(cell_link)}
        else:
          item[header] = cell_text
      data.append(item)

    return data

  def parse_card_gallery(self, response):
    data = defaultdict(list)

    galleries = response.css('.wikia-gallery')

    for gallery in galleries:
      header = gallery.xpath('preceding-sibling::*[self::h2 or self::p][1]')
      if header:
        headline = header.css('.mw-headline')
        region_name = get_text(headline) if headline else get_text(header)
      else:
        region_name = ''
      region_name = (region_name or '').lower()
      region_abbr = (Lang.abbr_from_full(region_name) or "").lower()

      # ignore "other" gallery subsections
      if not region_abbr:
        continue

      items = gallery.css('.wikia-gallery-item')

      for item in items:
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
          upload_date = datetime.strptime(ts, '%Y%m%d%H%M%S').isoformat()

        data[region_abbr].append({
            'imgName': img_name,
            'imgURL': full_url,
            'filePage': wiki_url(wiki_file_path),
            'uploadDate': upload_date,
            'captionText': caption_text,
            'captionLink': wiki_url(caption_link)
        })

    return data

  @staticmethod
  def full_img_for_thumb(thumb_url: str) -> str:
    return re.sub(r'/scale-to-width-down/\d+', '', thumb_url)

  def parse_card_rulings(self, response):
    ruling_items = response.css('.ruling')
    assert len(ruling_items) > 0, f"no rulings"

    rulings = []
    for item in ruling_items:
      question = get_text(item.css('.question-body'))
      answer = get_text(item.css('.answer-body'))
      ref = get_text(item.css('sup'))

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
      ref_text = get_text(ref_body)
      ref_link = ref_body.css('a::attr(href)').get()
      references.append({
          'num': ref_number,
          'text': ref_text,
          'link': wiki_url(ref_link),
      })

    data = {'rulings': rulings, 'references': references}
    return data

  def parse_card_errata(self, response):
    tables = response.css('.errata-table')

    if len(tables) == 0:
      # we only expect this for a couple exceptional pages.
      # these pages are weird enough that we can just ignore them.
      if response.url in KNOWN_ERRATA_WITHOUT_TABLES:
        return

      assert False, f"no errata tables found"

    data = []

    for table in tables:
      before_text = get_text(table.css('.before-text'))
      after_text = get_text(table.css('.after-text'))

      before_thumb_url = table.css('.before-image img').xpath('@src').get()
      after_thumb_url = table.css('.after-image img').xpath('@src').get()

      item = {
          'beforeText': before_text,
          'afterText': after_text,
          'afterImageURL': self.full_img_for_thumb(after_thumb_url),
      }

      if before_thumb_url:
        item['beforeImageURL'] = self.full_img_for_thumb(before_thumb_url)
      data.append(item)

    return data
