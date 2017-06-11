# -*- coding: utf-8 -*-
import scrapy


class TimelineSpiderSpider(scrapy.Spider):
    name = "timeline_spider"
    start_urls = (
        'http://www.http://www.jianshu.com/',
    )

    def parse(self, response):
        pass
