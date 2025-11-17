import logging
import os
import pathlib

import scrapy

from ...games import Game
from ...langs import Lang
from .. import scrapy_util

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

# supported values: 30, 60, 90, 120
LIMIT = 120


class TCGPlusCardListSpider(scrapy.Spider):
  """
  When does this data change? => only when a new set releases
  """

  # scrapy properties
  name = "TCG+ Card List Spider"

  # custom properties
  output_dir = scrapy_util.ROOT_DIR / 'dataSources' / 'tcgPlus' / 'cardList'
  clear_output_dir = True
  poll_threshold = 24 * 60 * 60  # 24 hours

  async def start(self):
    for game_id in GAME_ID_MAPPING:
      yield self.card_list_request(game_id)

  def card_list_request(self, game_id, offset=0, results=None):
    url = CARD_LIST_URL.format(game_id=game_id, limit=LIMIT, offset=offset)
    meta = {
        'game_id': game_id,
        'offset': offset,
        'results': results or {},
    }
    return scrapy.Request(url, callback=self.parse_card_list, meta=meta)

  def parse_card_list(self, response):
    data = response.json().get('success', {})
    json_response_code = data.get('code')
    logging.debug('GET %s (%s) | %s', response.status, json_response_code,
                  response.url)

    game_id = response.meta['game_id']
    offset = response.meta['offset']
    results = response.meta['results']

    game, lang = GAME_ID_MAPPING[game_id]

    cards = data.get('cards', [])
    if not cards:
      msg = f"no cards found for {lang} {game}"
      print(f"::error title=TCG+ Scrape Error::{msg}")
      logging.error(msg)
      return None

    total_count = int(data.get('total', 0))
    if not total_count:
      msg = f"no total count found for {lang} {game}"
      print(f"::error title=TCG+ Scrape Error::{msg}")
      logging.error(msg)
      return None

    logging.debug("found %s cards for %s %s", len(cards), lang, game)

    for card in cards:
      card_id = card.get('id')

      if not card_id:
        msg = f"card with no TCG+ ID found for {lang} {game}: {card}"
        print(f"::error title=TCG+ Scrape Error::{msg}")
        logging.error(msg)
        continue

      # logging.info("saving card %s for %s %s", card_id, lang, game)  # FIXME
      results[card_id] = card

    new_offset = offset + LIMIT
    if new_offset < total_count:
      yield self.card_list_request(
          game_id,
          new_offset,
          results,
      )
    else:
      logging.info("finished fetching %s cards for %s %s", len(results), lang,
                   game)
      yield {
          'write_subpath': [game.abbr(), f"{lang.abbr()}.json"],
          **results,
      }


class TCGPlusCardDetailSpider(scrapy.Spider):
  """
  When does this data change? => in theory, only when a new set releases. 
                                 in practice, maybe at any point?
  """

  # scrapy properties
  name = "TCG+ Card Detail Spider"

  # custom properties
  output_dir = scrapy_util.ROOT_DIR / 'dataSources' / 'tcgPlus' / 'cardDetail'
  clear_output_dir = False  # we eventually want per-game scheduling, so definitely don't clear the entire dir

  # TODO: implement
