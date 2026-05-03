# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html

from itertools import cycle

from scrapy import signals
from scrapy.exceptions import CloseSpider, IgnoreRequest

# useful for handling different item types with a single interface
from itemadapter import is_item, ItemAdapter


class OTCGJSpiderMiddleware:
  # Not all methods need to be defined. If a method is not defined,
  # scrapy acts as if the spider middleware does not modify the
  # passed objects.

  @classmethod
  def from_crawler(cls, crawler):
    # This method is used by Scrapy to create your spiders.
    s = cls()
    crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
    return s

  def process_spider_input(self, response, spider):
    # Called for each response that goes through the spider
    # middleware and into the spider.

    # Should return None or raise an exception.
    return None

  def process_spider_output(self, response, result, spider):
    # Called with the results returned from the Spider, after
    # it has processed the response.

    # Must return an iterable of Request, or item objects.
    for i in result:
      yield i

  def process_spider_exception(self, response, exception, spider):
    # Called when a spider or process_spider_input() method
    # (from other spider middleware) raises an exception.

    # Should return either None or an iterable of Request or item objects.
    pass

  def process_start_requests(self, start_requests, spider):
    # Called with the start requests of the spider, and works
    # similarly to the process_spider_output() method, except
    # that it doesn’t have a response associated.

    # Must return only requests (not items).
    for r in start_requests:
      yield r

  def spider_opened(self, spider):
    spider.logger.info("Spider opened: %s" % spider.name)


class OTCGJDownloaderMiddleware:
  # Not all methods need to be defined. If a method is not defined,
  # scrapy acts as if the downloader middleware does not modify the
  # passed objects.

  @classmethod
  def from_crawler(cls, crawler):
    # This method is used by Scrapy to create your spiders.
    s = cls()
    crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
    return s

  def process_request(self, request, spider):
    # Called for each request that goes through the downloader
    # middleware.

    # Must either:
    # - return None: continue processing this request
    # - or return a Response object
    # - or return a Request object
    # - or raise IgnoreRequest: process_exception() methods of
    #   installed downloader middleware will be called
    return None

  def process_response(self, request, response, spider):
    # Called with the response returned from the downloader.

    # Must either;
    # - return a Response object
    # - return a Request object
    # - or raise IgnoreRequest
    return response

  def process_exception(self, request, exception, spider):
    # Called when a download handler or a process_request()
    # (from other downloader middleware) raises an exception.

    # Must either:
    # - return None: continue processing this exception
    # - return a Response object: stops process_exception() chain
    # - return a Request object: stops process_exception() chain
    pass

  def spider_opened(self, spider):
    spider.logger.info("Spider opened: %s" % spider.name)


class RotateUserAgentMiddleware:
  """Cycle through USER_AGENTS for every outgoing request."""

  def __init__(self, user_agents: list[str]):
    self.user_agents_cycle = cycle(user_agents) if user_agents else None

  @classmethod
  def from_crawler(cls, crawler):
    agents = crawler.settings.get('USER_AGENTS') or []
    # Ensure values are strings and strip empties.
    agents = [str(agent).strip() for agent in agents if str(agent).strip()]
    return cls(agents)

  def process_request(self, request, spider):
    if not self.user_agents_cycle:
      return None
    request.headers['User-Agent'] = next(self.user_agents_cycle)
    return None


class StopOnForbiddenMiddleware:
  """Stop crawl immediately when final 403 response is seen."""

  def __init__(self, max_retry_times: int):
    self.max_retry_times = max_retry_times

  @classmethod
  def from_crawler(cls, crawler):
    # Defer to RETRY_TIMES so behavior matches RetryMiddleware.
    return cls(crawler.settings.getint('RETRY_TIMES', 2))

  def process_response(self, request, response, spider):
    if response.status == 403:
      retries = request.meta.get('retry_times', 0)
      if retries >= self.max_retry_times:
        spider.logger.error("403 retry exhausted at %s", response.url)
        raise CloseSpider("403 forbidden after retries")
    return response


class MaxRequestsMiddleware:
  """Close a spider once it has issued max_requests outgoing HTTP requests.

  The limit is tracked per spider instance, so each spider in a multi-spider
  run has its own independent counter.  Set spider.max_requests = 0 (default)
  to disable the limit.
  """

  def process_request(self, request, spider):
    limit = getattr(spider, 'max_requests', 0)
    if not limit:
      return None

    # Once close has been initiated, silently drop all further requests so
    # they don't show up as "Error downloading" in the logs.
    if getattr(spider, '_max_requests_closing', False):
      raise IgnoreRequest('max_requests_reached')

    count = getattr(spider, '_request_count', 0) + 1
    spider._request_count = count

    if count > limit:
      spider._max_requests_closing = True
      # Use engine.close_spider for a graceful close with the correct reason.
      # IgnoreRequest drops this over-limit request silently.
      spider.crawler.engine.close_spider(spider, 'max_requests_reached')
      raise IgnoreRequest('max_requests_reached')

    return None
