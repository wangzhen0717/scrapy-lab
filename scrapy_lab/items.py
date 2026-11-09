# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class IthomeItem(scrapy.Item):
    url = scrapy.Field()
    title = scrapy.Field()
    publish_time = scrapy.Field()
    source = scrapy.Field()
    author = scrapy.Field()
    content = scrapy.Field()
    images = scrapy.Field()
    videos = scrapy.Field()
    article_value = scrapy.Field()
    rating_count = scrapy.Field()
