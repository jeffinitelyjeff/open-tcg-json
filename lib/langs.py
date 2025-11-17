import enum


class Lang(enum.Enum):

  def full_name(lang):
    return lang.value['full_name']

  def abbr(lang):
    return lang.value['abbreviation']

  EN = {'full_name': 'English', 'abbreviation': 'EN'}

  JP = {'full_name': 'Japanese', 'abbreviation': 'JP'}

  FR = {'full_name': 'French', 'abbreviation': 'FR'}
