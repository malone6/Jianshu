# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html
import pymongo

class JianshuSpiderPipeline(object):
    def process_item(self, item, spider):
        return item

class UserMongoPipeline(object):
    collection_name = 'user'

    def __init__(self, mongo_host, mongo_db):
        self.mongo_host = mongo_host
        self.mongo_db = mongo_db

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            mongo_host=crawler.settings.get('MONGO_HOST'),
            mongo_db=crawler.settings.get('MONGO_DATABASE')
        )

    def open_spider(self, spider):
        self.client = pymongo.MongoClient(self.mongo_host)
        self.db = self.client[self.mongo_db]

    def close_spider(self, spider):
        self.client.close()

    def process_item(self, item, spider):
        # 发现则不插入
        self.db[self.collection_name].update({'slug': item['slug']}, {'$setOnInsert': item}, upsert=True)
        # 插入更新
        # self.db[self.collection_name].update({'slug': item['slug']}, item, upsert=True)
        return item
