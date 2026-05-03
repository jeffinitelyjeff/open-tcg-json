# Scrapy settings for otcgjson project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html

BOT_NAME = "otcgjson"

SPIDER_MODULES = ["lib.scrapy.spiders"]
NEWSPIDER_MODULE = "lib.scrapy.spiders"

# Crawl responsibly by identifying yourself (and your website) on the user-agent
#USER_AGENT = "otcgjson (+http://www.yourdomain.com)"
USER_AGENT = ('Mozilla/5.0 (X11; Linux x86_64) '
              'AppleWebKit/537.36 (KHTML, like Gecko) '
              'Chrome/57.0.2987.110 '
              'Safari/537.36')

USER_AGENTS = [
    ('Mozilla/5.0 (X11; Linux x86_64) '
     'AppleWebKit/537.36 (KHTML, like Gecko) '
     'Chrome/57.0.2987.110 '
     'Safari/537.36'),  # chrome
    ('Mozilla/5.0 (X11; Linux x86_64) '
     'AppleWebKit/537.36 (KHTML, like Gecko) '
     'Chrome/61.0.3163.79 '
     'Safari/537.36'),  # chrome
    ('Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:55.0) '
     'Gecko/20100101 '
     'Firefox/55.0')  # firefox
]

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Configure maximum concurrent requests performed by Scrapy (default: 16)
#CONCURRENT_REQUESTS = 32

# Configure a delay for requests for the same website (default: 0)
# See https://docs.scrapy.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
#DOWNLOAD_DELAY = 3
# The download delay setting will honor only one of:
#CONCURRENT_REQUESTS_PER_DOMAIN = 16
#CONCURRENT_REQUESTS_PER_IP = 16

# Disable cookies (enabled by default)
COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
#TELNETCONSOLE_ENABLED = False

# Override the default request headers:
DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en",
    "Referer": "https://www.google.com/"
}

# Enable or disable spider middlewares
# See https://docs.scrapy.org/en/latest/topics/spider-middleware.html
#SPIDER_MIDDLEWARES = {
#    "middlewares.otcgjsonSpiderMiddleware": 543,
#}

# Enable or disable downloader middlewares
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
DOWNLOADER_MIDDLEWARES = {
    'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
    'lib.scrapy.middlewares.RotateUserAgentMiddleware': 500,
    # Run after RetryMiddleware (550) so we see final 403 responses.
    'lib.scrapy.middlewares.StopOnForbiddenMiddleware': 560,
    # Counts every outgoing request (including retries) per spider.
    'lib.scrapy.middlewares.MaxRequestsMiddleware': 450,
    # Tracks per-URL retry depth and emits a histogram on spider close.
    'lib.scrapy.middlewares.RetryHistogramMiddleware': 100,
}

# Enable or disable extensions
# See https://docs.scrapy.org/en/latest/topics/extensions.html
EXTENSIONS = {
    # "scrapy.extensions.closespider.CloseSpider": 100,
}
CLOSESPIDER_ERRORCOUNT = 1

# Configure item pipelines
# See https://docs.scrapy.org/en/latest/topics/item-pipeline.html
ITEM_PIPELINES = {
    "lib.scrapy.pipelines.OTCGJPipeline": 1000,
}

# Enable and configure the AutoThrottle extension (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/autothrottle.html
#AUTOTHROTTLE_ENABLED = True
# The initial download delay
#AUTOTHROTTLE_START_DELAY = 5
# The maximum download delay to be set in case of high latencies
#AUTOTHROTTLE_MAX_DELAY = 60
# The average number of requests Scrapy should be sending in parallel to
# each remote server
#AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
# Enable showing throttling stats for every response received:
#AUTOTHROTTLE_DEBUG = False

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 5
AUTOTHROTTLE_MAX_DELAY = 60
AUTOTHROTTLE_TARGET_CONCURRENCY = 3.0
RANDOMIZE_DOWNLOAD_DELAY = True
RETRY_ENABLED = True
RETRY_HTTP_CODES = [500, 502, 503, 504, 522, 524, 408, 429, 403]
RETRY_TIMES = 10

# AUTOTHROTTLE_DEBUG adds lines like this, which are very verbose and don't add
# much actionable info:
# [INFO] slot: api.bandai-tcg-plus.com | conc: 1 | delay:  145 ms (-72) | latency:  217 ms | size: 48790 bytes
AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
#HTTPCACHE_ENABLED = True
#HTTPCACHE_EXPIRATION_SECS = 0
#HTTPCACHE_DIR = "httpcache"
#HTTPCACHE_IGNORE_HTTP_CODES = []
#HTTPCACHE_STORAGE = "scrapy.extensions.httpcache.FilesystemCacheStorage"

# Set settings whose default value is deprecated to a future-proof value
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"
