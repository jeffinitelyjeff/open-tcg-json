import enum


class Game(enum.Enum):

  def abbr(game):
    return game.value['abbreviation']

  def short_name(game):
    return game.value['short_name']

  def full_name(game):
    return game.value['full_name']

  # --- Bandai Card Games

  DBS_MASTERS = {
      'full_name': 'Dragon Ball Super Card Game Masters',
      'short_name': 'DBS Masters',
      'abbreviation': 'DBS'
  }

  DIGIMON = {
      'full_name': 'Digimon Card Game',
      'short_name': 'Digimon',
      'abbreviation': 'DCG'
  }

  ONE_PIECE = {
      'full_name': 'One Piece Card Game',
      'short_name': 'One Piece',
      'abbreviation': 'OP'
  }

  BATTLE_SPIRITS_SAGA = {
      'full_name': 'Battle Spirits Saga',
      'short_name': 'Battle Spirits Saga',
      'abbreviation': 'BSS'
  }

  BATTLE_SPIRITS = {
      'full_name': 'Battle Spirits',
      'short_name': 'Battle Spirits',
      'abbreviation': 'BS'
  }

  UNION_ARENA = {
      'full_name': 'Union Arena',
      'short_name': 'Union Arena',
      'abbreviation': 'UA'
  }

  GUNDAM = {
      'full_name': 'Gundam Card Game',
      'short_name': 'Gundam',
      'abbreviation': 'GCG'
  }

  DBS_FUSION_WORLD = {
      'full_name': 'Dragon Ball Super Fusion World',
      'short_name': 'DBS Fusion World',
      'abbreviation': 'DBSFW'
  }

  KAIUN_COLISEUM = {
      'full_name': 'Kaiun Coliseum',
      'short_name': 'Kaiun Coliseum',
      'abbreviation': 'KC'
  }
