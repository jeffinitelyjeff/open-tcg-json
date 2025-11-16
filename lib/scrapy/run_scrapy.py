from spiders.tcg_plus import TCGPlusSpider

spiders = [
    TCGPlusSpider,
]

process = CrawlerProcess(settings)
for spider in spiders:
  process.crawl(spider, card_nums=card_nums, disable_upload=args.disable_upload)
process.start()
