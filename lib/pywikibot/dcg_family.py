from __future__ import absolute_import, division, unicode_literals

from pywikibot import family
from pywikibot.tools import deprecated


class Family(family.Family):

  name = 'dcg'
  langs = {'en': 'digimoncardgame.fandom.com'}

  def scriptpath(self, code):
    return {
        'en': '',
        'es': '/es',
        'fr': '/fr',
        'ptbr': '/pt-br',
    }[code]

  @deprecated('APISite.version()')
  def version(self, code):
    return '1.31.2'

  def protocol(self, code):
    return 'HTTPS'
