from collections import defaultdict
import logging

import scrapy

from . import base_spider
from ...games import Game
from ...langs import Lang
from .. import scrapy_util
from ..pipelines import JSONItem

# game_title_id => (game_title, language)
GAME_ID_MAPPING = {
    1: (Game.DBS_MASTERS, Lang.EN),
    2: (Game.DIGIMON, Lang.EN),
    3: (Game.DBS_MASTERS, Lang.FR),
    4: (Game.ONE_PIECE, Lang.EN),
    5: (Game.BATTLE_SPIRITS_SAGA, Lang.EN),
    6: (Game.DIGIMON, Lang.JP),
    7: (Game.BATTLE_SPIRITS, Lang.JP),
    8: (Game.ONE_PIECE, Lang.JP),
    9: (Game.UNION_ARENA, Lang.JP),
    10: (Game.DBS_FUSION_WORLD, Lang.EN),
    11: (Game.DBS_FUSION_WORLD, Lang.JP),
    12: (Game.UNION_ARENA, Lang.EN),
    13: (Game.ONE_PIECE, Lang.FR),
    15: (Game.GUNDAM, Lang.JP),
    16: (Game.GUNDAM, Lang.EN),
    17: (Game.KAIUN_COLISEUM, Lang.JP),
}

CARD_LIST_URL = 'https://api.bandai-tcg-plus.com/api/user/card/list?game_title_id={game_id}&limit={limit}&offset={offset}'
CARD_DETAIL_URL = 'https://api.bandai-tcg-plus.com/api/user/card/{card_id}'

# supported values: 30, 60, 90, 120
LIMIT = 120


class Error(base_spider.Error):
  LIST_NO_CARDS = 1
  LIST_NO_TOTAL = 2
  LIST_NO_ID = 3
  LIST_NO_CARDNUM = 4
  LIST_NO_SET = 5
  DETAIL_NO_DATA = 6
  DETAIL_NO_ID = 7
  DETAIL_NO_SET = 8


class Notice(base_spider.Notice):
  pass


class TCGPlusSpider(base_spider.BaseSpider):

  # scrapy properties
  name = "TCG+ Spider"

  # custom properties
  output_dir = scrapy_util.ROOT_DIR / 'dataSources' / 'tcgPlus'
  clear_output_dir = True

  def __init__(self, poll_only: bool = False, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.poll_only = poll_only
    if self.poll_only:
      logging.info(
          "TCG+ spider running in poll-only mode; skipping card detail requests"
      )
      # Keep prior card detail files so git status only reflects list diffs
      self.clear_output_dir = False

  async def start(self):
    for game_id in GAME_ID_MAPPING:
      yield self.card_list_request(game_id)

  def card_list_request(self, game_id, offset=0, prior_results=None):
    url = CARD_LIST_URL.format(game_id=game_id, limit=LIMIT, offset=offset)
    meta = {
        'game_id': game_id,
        'offset': offset,
        'results': prior_results or {},
    }
    return scrapy.Request(url, callback=self.parse_card_list, meta=meta)

  def card_detail_request(self, card_id, game_id):
    url = CARD_DETAIL_URL.format(card_id=card_id)
    meta = {
        'game_id': game_id,
    }
    return scrapy.Request(url, callback=self.parse_card_detail, meta=meta)

  def parse_card_list(self, response):
    data = response.json().get('success', {})
    json_response_code = data.get('code')

    logging.debug('GET %s (%s) | %s', response.status, json_response_code,
                  response.url)

    game_id = response.meta['game_id']
    offset = response.meta['offset']
    results = response.meta['results']

    game, lang = GAME_ID_MAPPING[game_id]
    game_key = f"{game.abbr().lower()}_{lang.abbr().lower()}"
    prefix = [game.abbr(), lang.abbr()]

    cards = data.get('cards', [])
    if not cards:
      self.log_error(Error.LIST_NO_CARDS, f"no cards found for {game_key}")
      return None

    total_count = int(data.get('total', 0))
    if not total_count:
      self.log_error(Error.LIST_NO_TOTAL,
                     f"no total count found for {game_key}")
      return None

    logging.debug("found %s cards for %s", len(cards), game_key)

    for card in cards:
      card_id = card.get('id')

      if not card_id:
        self.log_error(Error.LIST_NO_ID,
                       f"card with no TCG+ ID found for {game_key}: {card}")
        continue

      results[card_id] = card
      if not self.poll_only:
        yield self.card_detail_request(card_id, game_id)

    new_offset = offset + LIMIT
    if new_offset < total_count:
      yield self.card_list_request(
          game_id,
          new_offset,
          results,
      )
    else:
      logging.info("finished fetching %s cards for %s", len(results), game_key)

      tcgplus_id_to_card_number = {}
      tcgplus_id_to_detail_path = {}
      card_number_to_tcgplus_ids = defaultdict(list)
      card_number_to_detail_paths = defaultdict(list)
      set_to_results = defaultdict(dict)

      for card in results.values():
        card_number = card.get('card_number')
        if not card_number:
          self.log_error(
              Error.LIST_NO_CARDNUM,
              f"card with no card number found for {game_key}: {card}")
          continue

        tcgplus_id = card.get('id')
        if not tcgplus_id:
          self.log_error(Error.LIST_NO_ID,
                         f"card with no TCG+ ID found for {game_key}: {card}")
          continue

        set_name = set_abbr(card.get('image_url', ''))
        if not set_name:
          self.log_error(Error.LIST_NO_SET,
                         f"card with no set name found for {game_key}: {card}")
          continue

        tcgplus_id_to_card_number[tcgplus_id] = card_number
        tcgplus_id_to_detail_path[tcgplus_id] = f"{set_name}/{tcgplus_id}.json"
        card_number_to_tcgplus_ids[card_number].append(str(tcgplus_id))
        card_number_to_detail_paths[card_number].append(
            f"{set_name}/{tcgplus_id}.json")
        set_to_results[set_name][tcgplus_id] = card

      for product_id_list in card_number_to_tcgplus_ids.values():
        product_id_list.sort()

      yield JSONItem(tcgplus_id_to_card_number,
                     subpath=prefix + ['_index', 'id_to_cardNum.json'])
      yield JSONItem(tcgplus_id_to_detail_path,
                     subpath=prefix + ['_index', 'id_to_detailPath.json'])
      yield JSONItem(card_number_to_tcgplus_ids,
                     subpath=prefix + ['_index', 'cardNum_to_ids.json'])
      yield JSONItem(card_number_to_detail_paths,
                     subpath=prefix + ['_index', 'cardNum_to_detailPaths.json'])
      for set, set_results in set_to_results.items():
        yield JSONItem(set_results, subpath=prefix + [set, 'cardList.json'])

  def parse_card_detail(self, response):
    game_id = response.meta['game_id']
    game, lang = GAME_ID_MAPPING[game_id]
    prefix = [game.abbr(), lang.abbr()]

    data = response.json().get('success', {})
    json_response_code = data.get('code')
    logging.debug('GET %s (%s) | %s', response.status, json_response_code,
                  response.url)

    card_data = data.get('card', {})
    if not card_data:
      self.log_error(Error.DETAIL_NO_DATA,
                     f"no card data found for URL: {response.url}")
      return None

    card_id = card_data.get('id')
    if not card_id:
      self.log_error(Error.DETAIL_NO_ID,
                     f"TCG+ ID not in output for URL: {response.url}")
      return None

    set_name = set_abbr(card_data.get('image_url', ''))
    if not set_name:
      self.log_error(Error.DETAIL_NO_SET,
                     f"set number not found for URL: {response.url}")
      return None

    yield JSONItem(card_data, subpath=prefix + [set_name, f"{card_id}.json"])


def set_abbr(image_url: str) -> str:
  # /card_image/DG-EN/BT22/e_BT22-001_D.png -> BT22
  # /card_image/BS-JA/X/020.JPG -> X
  return image_url.split('/')[-2]
