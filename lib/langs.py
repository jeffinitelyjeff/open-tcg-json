import enum


class Lang(enum.Enum):

  def full_name(lang):
    return lang.value['full_name']

  def abbr(lang):
    return lang.value['abbreviation']

  @staticmethod
  def abbr_from_full(full_name: str) -> str | None:
    for lang in Lang:
      if lang.value['full_name'].lower() == full_name.lower():
        return lang.value['abbreviation']
    return None

  EN = {'full_name': 'English', 'abbreviation': 'EN'}
  JP = {'full_name': 'Japanese', 'abbreviation': 'JP'}
  FR = {'full_name': 'French', 'abbreviation': 'FR'}
  CH = {'full_name': 'Chinese', 'abbreviation': 'CH'}
  KR = {'full_name': 'Korean', 'abbreviation': 'KR'}
