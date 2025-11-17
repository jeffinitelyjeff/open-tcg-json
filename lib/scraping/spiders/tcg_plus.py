import logging
import os
import pathlib

import scrapy

from lib.games import Game
from lib.langs import Lang
from ... import util

# game_title_id => (game_title, language)
TCG_PLUS_GAME_TITLE_ID_MAPPING = {
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


class TCGPlusSpider(scrapy.Spider):
  """
  Note: For now, this only scans the `card/list` API to get an internal TCG+ ID
  for each card. The `card/list` endpoint only returns minimal metadata about
  each card, so the `card/[id]` endpoint will need to be used if we want to
  fetch the full TCG+ metadata for each card in the future.

  When does this data change? => only when a new set releases
  """

  # scrapy properties
  name = "TCG Plus Spider"

  # custom properties
  output_dir = util.ROOT_DIR / 'dataSources' / 'tcgPlus'
  clear_output_dir = True

  def start_requests(self):
    for game_id in TCG_PLUS_GAME_TITLE_ID_MAPPING:
      yield self.card_list_request(game_id, 0)

  def card_list_request(self, game_id, offset):
    url = CARD_LIST_URL.format(game_id=game_id, limit=LIMIT, offset=offset)
    return scrapy.Request(url,
                          callback=self.parse_card_list,
                          meta={
                              'game_id': game_id,
                              'offset': offset
                          })

  def parse_card_list(self, response):
    data = response.json().get('success', {})
    json_response_code = data.get('code')
    logging.debug('GET %s (%s) | %s', response.status, json_response_code,
                  response.url)

    game_id = response.meta['game_id']
    offset = response.meta['offset']

    region = TCG_PLUS_GAME_TITLE_ID_MAPPING[game_id][1].name
    print(f"Scraping TCG Plus cards for {region}...")

    cards = data.get('cards', [])
    if not cards:
      msg = f"no cards found for {region}"
      print(f"::error title=TCG Plus Scrape Error::{msg}")
      logging.error(msg)
      return None

    for card in cards:
      card_id = card.get('id')
      if not card_id:
        msg = f"card with no TCG Plus ID found for {region}: {card}"
        print(f"::error title=TCG Plus Scrape Error::{msg}")
        logging.error(msg)
        continue

      yield {'write_path': [region.lower(), f"{card_id}.json"], **card}

    total_count = int(data.get('total', 0))
    new_offset = offset + LIMIT
    if new_offset < total_count:
      yield self.card_list_request(region, new_offset)
