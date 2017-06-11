# -*- coding: utf-8 -*-
import json
import re
from fake_useragent import UserAgent
import scrapy
from scrapy import Request
from ..items import JianshuUserBaseInfoItem


class JianShuSpider(scrapy.Spider):
    name = "jian_spider"
    base_headers = {'Accept-Language': 'zh-CN,zh;q=0.8,en;q=0.6,zh-TW;q=0.4',
                    'Host': 'www.jianshu.com',
                    'Accept-Encoding': 'gzip, deflate, sdch',
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'text/html, */*; q=0.01',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36',
                    'Connection': 'keep-alive',
                    'Referer': 'http://www.jianshu.com'}
    # 只加载列表模块
    ajax_headers = dict(base_headers, **{"X-PJAX": "true", 'User-Agent': UserAgent().random})

    def start_requests(self):
        yield Request('http://www.jianshu.com/users/recommended?page=1&per_page=200',
                      headers=self.base_headers)

    def parse(self, response):
        print(response.text)
        data = json.loads(response.text)
        for user_data in data['users']:
            user_slug = user_data['slug']
            yield Request(url='http://www.jianshu.com/u/{slug}'.format(slug=user_slug),
                          headers=self.base_headers,
                          callback=self.parse_seeduser,
                          meta={'slug': user_slug})
            yield Request(url='http://www.jianshu.com/users/{slug}/followers'.format(slug=user_slug),
                          headers=self.ajax_headers,
                          callback=self.parse_followers,
                          meta={'slug': user_slug, 'page': 1}, )

    def parse_seeduser(self, response):
        base_info_item = JianshuUserBaseInfoItem()
        slug = response.meta['slug']
        div_main_top = response.xpath('//div[@class="main-top"]')
        nickname = div_main_top.xpath('.//div[@class="title"]//a/text()').extract_first()
        head_pic = div_main_top.xpath('.//a[@class="avatar"]//img/@src').extract_first()
        gender_tmp = div_main_top.xpath('.//div[@class="title"]//i/@class').extract()
        if gender_tmp:
            gender = gender_tmp[0].split('-')[-1]
        else:
            gender = 'No'
        is_contract_tmp = div_main_top.xpath('.//div[@class="title"]//span[@class="author-tag"]').extract()
        if is_contract_tmp:
            is_contract = '签约作者'
        else:
            is_contract = 'No'
        info = div_main_top.xpath('.//li//p//text()').extract()

        base_info_item['nickname'] = nickname
        base_info_item['slug'] = slug
        base_info_item['head_pic'] = head_pic
        base_info_item['gender'] = gender
        base_info_item['is_contract'] = is_contract
        base_info_item['following_num'] = int(info[0])
        base_info_item['followers_num'] = int(info[1])
        base_info_item['articles_num'] = int(info[2])
        base_info_item['words_num'] = int(info[3])
        base_info_item['be_liked_num'] = int(info[4])
        yield base_info_item

    def parse_followers(self, response):
        base_info_item = JianshuUserBaseInfoItem()
        slug = response.meta['slug']
        page = response.meta['page']
        user_li = response.xpath('//li')
        if user_li:
            page = page + 1
            yield Request(url='http://www.jianshu.com/users/{slug}/followers?page={page}'
                          .format(slug=slug, page=page),
                          headers=self.ajax_headers,
                          callback=self.parse_followers,
                          meta={'slug': slug, 'page': page})
            for user in user_li:
                base_info_item['nickname'] = user.xpath('.//a[@class="name"]/text()').extract_first()
                base_info_item['slug'] = user.xpath('.//a[@class="name"]/@href').extract_first().split('/')[-1]
                base_info_item['head_pic'] = user.xpath('.//img/@src').extract_first()
                span = user.xpath('.//span/text()').extract()
                base_info_item['following_num'] = int(re.search('\d+', span[0]).group())
                base_info_item['followers_num'] = int(re.search('\d+', span[1]).group())
                base_info_item['articles_num'] = int(re.search('\d+', span[2]).group())
                meta_text = user.xpath('.//div[@class="meta"]')[1].xpath('text()').extract_first()
                meta_num = re.findall('\d+', meta_text)
                base_info_item['words_num'] = int(meta_num[0])
                base_info_item['be_liked_num'] = int(meta_num[1])

                yield base_info_item
                # yield Request('http://www.jianshu.com/users/{slug}/followers'.format(slug=base_info_item['slug']),
                #               headers=self.ajax_headers,
                #               callback=self.parse_followers)
        else:
            pass




            #     yield Request('http://www.jianshu.com/users/{slug}/timeline'.format(slug=slug),
            #                   headers=self.ajax_headers,
            #                   callback=self.get_timeline,
            #                   meta={'slug': slug, 'page': 1})
            #
            # def get_timeline(self, response):
            #     if response.meta['page'] == 1:
            #         timeline_item = JianshuUserTimelineItem()
            #     else:
            #         timeline_item = response.meta['timeline']
            #         print(timeline_item)
            #     li_tags = response.xpath('//li')
            #     if li_tags:
            #         pertimeline = {
            #             'comment_notes': [],
            #             'like_notes': [],
            #             'reward_notes': [],
            #             'share_notes': [],
            #             'like_users': [],
            #             'like_colls': [],
            #             'like_comments': [],
            #             'like_notebooks': [],
            #         }
            #         for li in li_tags:
            #             if li.xpath('.//span[@data-type="comment_note"]'):
            #                 comment_note = {}
            #                 comment_note['comment_text'] = self.get_comment_text(li)
            #                 comment_note['time'] = self.get_mark_time(li)
            #                 # comment_note['note_title'] = self.get_obj_title(li)
            #                 comment_note['note_id'] = self.get_href_id(li)
            #                 print('发表评论', comment_note)
            #                 pertimeline['comment_notes'].append(comment_note)
            #             elif li.xpath('.//span[@data-type="like_note"]'):
            #                 like_note = {}
            #                 like_note['time'] = self.get_mark_time(li)
            #                 # like_note['note_title'] = self.get_obj_title(li)
            #                 like_note['note_id'] = self.get_href_id(li)
            #                 print('喜欢文章', like_note)
            #                 pertimeline['like_notes'].append(like_note)
            #             elif li.xpath('.//span[@data-type="reward_note"]'):
            #                 reward_note = {}
            #                 reward_note['time'] = self.get_mark_time(li)
            #                 # reward_note['note_title'] = self.get_obj_title(li)
            #                 reward_note['note_id'] = self.get_href_id(li)
            #                 print('赞赏文章', reward_note)
            #                 pertimeline['reward_notes'].append(reward_note)
            #             elif li.xpath('.//span[@data-type="share_note"]'):
            #                 share_note = {}
            #                 share_note['time'] = self.get_mark_time(li)
            #                 # share_note['note_title'] = self.get_obj_title(li)
            #                 share_note['note_id'] = self.get_href_id(li)
            #                 print('发表文章', share_note)
            #                 pertimeline['share_notes'].append(share_note)
            #             elif li.xpath('.//span[@data-type="like_user"]'):
            #                 like_user = {}
            #                 like_user['time'] = self.get_mark_time(li)
            #                 like_user['slug'] = self.get_href_id(li)
            #                 print('关注作者', like_user)
            #                 pertimeline['like_users'].append(like_user)
            #             elif li.xpath('.//span[@data-type="like_collection"]'):
            #                 like_coll = {}
            #                 like_coll['time'] = self.get_mark_time(li)
            #                 like_coll['coll_id'] = self.get_href_id(li)
            #                 print('关注专题', like_coll)
            #                 pertimeline['like_colls'].append(like_coll)
            #             elif li.xpath('.//span[@data-type="like_comment"]'):
            #                 like_comment = {}
            #                 like_comment['time'] = self.get_mark_time(li)
            #                 like_comment['comment_text'] = self.get_comment_text(li)
            #                 like_comment['slug'] = self.get_like_comment_slug(li)
            #                 like_comment['note_id'] = self.get_like_comment_note_id(li)
            #                 print('赞了评论', like_comment)
            #                 pertimeline['like_comments'].append(like_comment)
            #             elif li.xpath('.//span[@data-type="like_notebook"]'):
            #                 like_notebook = {}
            #                 like_notebook['time'] = self.get_mark_time(li)
            #                 like_notebook['notebook_id'] = self.get_href_id(li)
            #                 print('关注文集', like_notebook)
            #                 pertimeline['like_notebooks'].append(like_notebook)
            #             elif li.xpath('.//span[@data-type="join_jianshu"]'):
            #                 join_time = self.get_mark_time(li)
            #                 print('加入简书', join_time)
            #                 pertimeline['join_time'] = join_time
            #         last_li_id = li_tags[-1].xpath('@id').extract_first()
            #         next_first_id = int(last_li_id.split('-')[1]) - 1
            #         page = response.meta['page'] + 1
            #         yield Request(url='http://www.jianshu.com/users/{slug}/timeline?max_id={id}&page={page}' \
            #                       .format(slug=response.meta['slug'], id=next_first_id, page=page),
            #                       headers=self.ajax_headers,
            #                       callback=self.get_timeline,
            #                       meta={'timeline': timeline_item, 'page': page})
            #     else:
            #         yield timeline_item
            #
            # def get_mark_time(self, li):
            #     mark_time = li.xpath('.//@data-datetime').extract_first().split('+')[0].replace('T', ' ')
            #     return mark_time
            #
            # def get_obj_title(self, li):
            #     title = li.xpath('.//a[@class="title"]/text()').extract_first()
            #     return title
            #
            # def get_href_id(self, li):
            #     href_id = li.xpath('.//a[@class="title"]/@href').extract_first().split('/')[-1]
            #     return href_id
            #
            # def get_comment_text(self, li):
            #     like_comment_text = ''.join(li.xpath('.//p[@class="comment"]/text()').extract())
            #     return like_comment_text
            #
            # def get_like_comment_slug(self, li):
            #     like_comment_slug = li.xpath('.//div[@class="origin-author single-line"]//@href').extract_first().split('/')[-1]
            #     return like_comment_slug
            #
            # def get_like_comment_note_id(self, li):
            #     like_comment_note_id = li.xpath('.//div[@class="origin-author single-line"]//@href').extract()[1].split('/')[-1]
            #     return like_comment_note_id
