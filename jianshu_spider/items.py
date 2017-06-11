# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class JianshuUserBaseInfoItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    nickname = scrapy.Field()
    slug = scrapy.Field()
    head_pic = scrapy.Field()
    gender = scrapy.Field()
    is_contract = scrapy.Field()
    following_num = scrapy.Field()
    followers_num = scrapy.Field()
    articles_num = scrapy.Field()
    words_num = scrapy.Field()
    be_liked_num = scrapy.Field()
    pass

# class JianshuUserTimelineItem(scrapy.Item):
#
#     comment_notes = scrapy.Field()
#     like_notes = scrapy.Field()
#     reward_notes = scrapy.Field()
#     share_notes = scrapy.Field()
#     like_users = scrapy.Field()
#     like_colls = scrapy.Field()
#     like_comments = scrapy.Field()
#     like_notebooks = scrapy.Field()
#     join_time = scrapy.Field()
#     pass