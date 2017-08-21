import requests
from lxml import etree
from fake_useragent import UserAgent
import pymongo
import time
import sys
from .config import *

# 未做其他版本兼容。检查python版本，python3.5以上可用
PY35 = sys.version_info.major == 3 and sys.version_info.minor >= 5
if not PY35:
    raise Exception('请使用 Python3.5 及其以上的版本！')


# 遇到递归深度过大导致栈溢出，坑。直接修改最大递归深度
sys.setrecursionlimit(3000)
# 修改python的最大递归深度，默认是998，超过后会栈溢出，由于需要，这里暂时把递归深度改成3000。
# 另外，5000都不行，试了下，最大是3927，超过这个值，我的机器上的python就会停止工作。


'''
# 抓取大量用户动态时，开启多线程，线程数在config中配置
import concurrent.futures
threadpool = concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREAD)
'''

client = pymongo.MongoClient(MONGO_HOST, MONGO_PORT)
db = client['JianShu']

def retry(attempt):
    '''
    函数重试装饰器
    :param attempt:  函数重试次数，
    将该装饰器装饰于任何目标函数，目标函数执行时会进行给定次数的重试
    '''
    def decorator(func):
        def wrapper(*args, **kw):
            att = 0
            while att < attempt:
                try:
                    time.sleep(5)
                    return func(*args, **kw)
                except Exception as e:
                    att += 1
                    print('第%s次出现了错误' % att, e)
        return wrapper
    return decorator


BASE_HEADERS = {
    'Accept-Language': 'zh-CN,zh;q=0.8,en;q=0.6,zh-TW;q=0.4',
    'Host': 'www.jianshu.com',
    'Accept-Encoding': 'gzip, deflate, sdch',
    'X-Requested-With': 'XMLHttpRequest',
    'Accept': 'text/html, */*; q=0.01',
    'User-Agent': UserAgent().random,
    'Connection': 'keep-alive',
    'Referer': 'http://www.jianshu.com',
}


class GetUserInfo():
    def __init__(self, slug):
        self.headers = BASE_HEADERS
        self.slug = slug

    @retry(5)
    def get_base_info(self):
        url = 'http://www.jianshu.com/u/{slug}'.format(slug=self.slug)
        response = requests.get(url, headers=self.headers)
        if response.status_code == 404:
            '''经测试，出现404时都是因为用户被封禁或注销，即显示：
            您要找的页面不存在.可能是因为您的链接地址有误、该文章已经被作者删除或转为私密状态。'''
            return None
        else:
            tree = etree.HTML(response.text)

            div_main_top = tree.xpath('//div[@class="main-top"]')[0]
            nickname = div_main_top.xpath('.//div[@class="title"]//a/text()')[0]
            head_pic = div_main_top.xpath('.//a[@class="avatar"]//img/@src')[0]
            div_main_top.xpath('.//div[@class="title"]//i/@class')

            # 检查用户填写的性别信息。1：男  -1：女  0：性别未填写
            if div_main_top.xpath('.//i[@class="iconfont ic-man"]'): gender = 1
            elif div_main_top.xpath('.//i[@class="iconfont ic-woman"]'): gender = -1
            else: gender = 0

            # 判断该用户是否为签约作者。is_contract为1是简书签约作者，为0则是普通用户
            if div_main_top.xpath('.//i[@class="iconfont ic-write"]'): is_contract = 1
            else: is_contract = 0

            # 取出用户文章及关注量
            info = div_main_top.xpath('.//li//p//text()')

            item = {'nickname': nickname,
                    'slug': self.slug,
                    'head_pic': head_pic,
                    'gender': gender,
                    'is_contract': is_contract,
                    'following_num': int(info[0]),
                    'followers_num': int(info[1]),
                    'articles_num': int(info[2]),
                    'words_num': int(info[3]),
                    'be_liked_num': int(info[4]),
                    'update_time': time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))
                    }
            # 取当前抓取时间，为用户信息更新时间。添加update_time字段
            return item


class GetUerTimeline():
    def __init__(self, slug, update=False):
        '''
        :param slug: 目标用户的slug(用户的唯一标识)，如：我的是5a7aa9b0cf9e
        :param update: 默认update=False，是指该次调用是首次抓取。
                       当传参update=True时，表明该次调用是更新信息的抓取
        '''
        self.slug = slug

        # 抓取动态采用不同headers，带"X-PJAX": "true"返回动态加载片段，加Referer反盗链。
        AJAX_HEADERS = {"Referer": "http//:www.jianshu.com/u/{slug}".format(slug=self.slug),
                        "X-PJAX": "true"}
        self.headers = dict(BASE_HEADERS, **AJAX_HEADERS)

        # 初始化盛数据的容器：timeline
        self.timeline = {
            'comment_notes': [],
            'like_notes': [],
            'reward_notes': [],
            'share_notes': [],
            'like_users': [],
            'like_colls': [],
            'like_comments': [],
            'like_notebooks': [],
        }

        if update:
            # 如果要更新动态，取出数据库中的最新动态时间mongo_latest_time，以便与真实最新动态作对比
            self.mongo_latest_time = \
                db.user_timeline.find_one({'slug': slug}, {'latest_time': 1}).get('latest_time')
        self.update = update

    def get_timeline(self, id=None, page=1):
        '''
        :param id: 用户动态翻页时，后一页的请求需要id值。为：前一页的最后一条动态的class节点的id-1
        :param page: 翻页
        :return: 返回加入数据之后的self.timeline
        '''
        if id == None:
            # 动态第一页
            url = 'http://www.jianshu.com/users/{slug}/timeline'.format(slug=self.slug)
        else:
            # 动态第二页之后需要依赖值id，可从前一页中取数据
            url = 'http://www.jianshu.com/users/{slug}/timeline?max_id={id}&page={page}' \
                .format(slug=self.slug, id=id, page=page)
        print(url)

        response = requests.get(url, headers=self.headers)
        tree = etree.HTML(response.text)
        li_tags = tree.xpath('//li')
        if li_tags:
            # 抽取出最新动态时间
            latest_time = li_tags[0].xpath('//@data-datetime')[0].split('+')[0].replace('T', ' ')
            if self.update == True:
                if latest_time == self.mongo_latest_time:
                    # 如果经检查，数据库中就是最新动态。则不用继续抓取
                    return self.timeline

            if page == 1:
                # 无论是否更新（避免多余判断），取出最新动态时间，更新到数据库
                self.timeline['latest_time'] = latest_time
                print(latest_time)

            # 遍历页面中所有动态，进行逐条解析
            for li in li_tags:
                # 该条动态时间点
                mark_time = self.get_mark_time(li)
                if self.update == True:
                    # 更新动态时，如果解析到数据库已存的时间点时则停止解析，否则继续
                    if mark_time == self.mongo_latest_time:
                        return self.timeline
                    else:
                        self.parse_li(li, mark_time)
                else:
                    self.parse_li(li, mark_time)
            # 抽取并计算得到下一页动态依赖的id
            last_li_id = li_tags[-1].xpath('@id')[0]
            next_first_id = int(last_li_id.split('-')[1]) - 1
            return self.get_timeline(next_first_id, page + 1)
        else:
            # 页面为空，没更多的动态了
            return self.timeline

    def parse_li(self, li, mark_time):
        '''
        :param li: 要解析的li标签
        :param mark_time: 前面已经解析出该条动态的时间点
        '''
        if li.xpath('.//span[@data-type="comment_note"]'):
            comment_note = {}
            comment_note['comment_text'] = self.get_comment_text(li)
            comment_note['time'] = mark_time
            # comment_note['note_title'] = self.get_obj_title(li)
            comment_note['note_id'] = self.get_href_id(li)
            print('发表评论', comment_note)
            self.timeline['comment_notes'].append(comment_note)
        elif li.xpath('.//span[@data-type="like_note"]'):
            like_note = {}
            like_note['time'] = mark_time
            # like_note['note_title'] = self.get_obj_title(li)
            like_note['note_id'] = self.get_href_id(li)
            print('喜欢文章', like_note)
            self.timeline['like_notes'].append(like_note)
        elif li.xpath('.//span[@data-type="reward_note"]'):
            reward_note = {}
            reward_note['time'] = mark_time
            # reward_note['note_title'] = self.get_obj_title(li)
            reward_note['note_id'] = self.get_href_id(li)
            print('赞赏文章', reward_note)
            self.timeline['reward_notes'].append(reward_note)
        elif li.xpath('.//span[@data-type="share_note"]'):
            share_note = {}
            share_note['time'] = mark_time
            # share_note['note_title'] = self.get_obj_title(li)
            share_note['note_id'] = self.get_href_id(li)
            print('发表文章', share_note)
            self.timeline['share_notes'].append(share_note)
        elif li.xpath('.//span[@data-type="like_user"]'):
            like_user = {}
            like_user['time'] = mark_time
            like_user['slug'] = self.get_href_id(li)
            print('关注作者', like_user)
            self.timeline['like_users'].append(like_user)
        elif li.xpath('.//span[@data-type="like_collection"]'):
            like_coll = {}
            like_coll['time'] = mark_time
            like_coll['coll_id'] = self.get_href_id(li)
            print('关注专题', like_coll)
            self.timeline['like_colls'].append(like_coll)
        elif li.xpath('.//span[@data-type="like_comment"]'):
            like_comment = {}
            like_comment['time'] = mark_time
            like_comment['comment_text'] = self.get_comment_text(li)
            like_comment['slug'] = self.get_like_comment_slug(li)
            like_comment['note_id'] = self.get_like_comment_note_id(li)
            print('赞了评论', like_comment)
            self.timeline['like_comments'].append(like_comment)
        elif li.xpath('.//span[@data-type="like_notebook"]'):
            like_notebook = {}
            like_notebook['time'] = mark_time
            like_notebook['notebook_id'] = self.get_href_id(li)
            print('关注文集', like_notebook)
            self.timeline['like_notebooks'].append(like_notebook)
        elif li.xpath('.//span[@data-type="join_jianshu"]'):
            join_time = mark_time
            print('加入简书', join_time)
            self.timeline['join_time'] = join_time

    def get_mark_time(self, li):
        '''获取动态产生的时间'''
        mark_time = li.xpath('.//@data-datetime')[0].split('+')[0].replace('T', ' ')
        return mark_time

    def get_obj_title(self, li):
        '''获取文章标题'''
        title = li.xpath('.//a[@class="title"]/text()')[0]
        return title

    def get_href_id(self, li):
        '''获取文章id'''
        href_id = li.xpath('.//a[@class="title"]/@href')[0].split('/')[-1]
        return href_id

    def get_comment_text(self, li):
        '''获取发表评论的内容'''
        like_comment_text = ''.join(li.xpath('.//p[@class="comment"]/text()'))
        return like_comment_text

    def get_like_comment_slug(self, li):
        '''获取赞了用户评论的slug'''
        like_comment_slug = li.xpath('.//div[@class="origin-author single-line"]//@href')[0].split('/')[-1]
        return like_comment_slug

    def get_like_comment_note_id(self, li):
        '''获取评论文章的id'''
        like_comment_note_id = li.xpath('.//div[@class="origin-author single-line"]//@href')[1].split('/')[-1]
        return like_comment_note_id


class GetAllInfo():

    # getallinfo() 分别处理首次抓取用户动态和更新用户动态
    def getallinfo(self, slug):
        if db['user_timeline'].find_one({'slug': slug}):
            print('该用户数据已经在数据库中', '\n', '正在更新数据……')
            # 更新用户信息
            baseinfo = GetUserInfo(slug).get_base_info()
            if baseinfo:
                self.save_to_mongo(baseinfo, update=True)
                print('更新用户信息成功')
                timeline = GetUerTimeline(slug, update=True).get_timeline()
                if len(timeline) != 8:
                    # 如果timeline不为空
                    self.save_update_timeline(slug, timeline)
                    print('更新用户动态成功')
                else:
                    print('数据库中已是最新动态')
            else:
                error_info = '404,可能是因为您的链接地址有误、该文章已经被作者删除或转为私密状态。'
                self.save_error_txt(slug, error_info)
        else:
            info = GetUserInfo(slug)
            baseinfo = info.get_base_info()
            if baseinfo:
                timeline = GetUerTimeline(slug).get_timeline()
                all_info = dict(baseinfo, **timeline)
                # print(all_info)
                self.save_to_mongo(all_info)
                print('存储用户信息成功')
            else:
                error_info = '404,可能是因为您的链接地址有误、该文章已经被作者删除或转为私密状态。'
                self.save_error_txt(slug, error_info)

    # 存储用户信息
    def save_to_mongo(self, all_info, update=False):
        if not update:
            db['user_timeline'].update({'slug': all_info['slug']}, {'$setOnInsert': all_info}, upsert=True)
        else:
            db['user_timeline'].update({'slug': all_info['slug']}, {'$set': all_info}, upsert=True)

    # 处理不存在的用户（被封禁等）的错误信息
    def save_error_txt(self, slug, error_info):
        with open('error.txt', 'a', encoding='utf-8') as f:
            f.write('http://www.jianshu.com/u/{0}'.format(slug) + ' ' + error_info + '\n')
            f.close()

    # 处理更新动态时的数据库操作(有$push操作，需单独写)
    def save_update_timeline(self, slug, timeline):
        db['user_timeline'].update({'slug': slug}, {'$set': {'latest_time': timeline['latest_time']}}, upsert=True)
        all_time = ['comment_notes', 'like_notes', 'reward_notes', 'share_notes',
                    'like_users', 'like_colls', 'like_comments', 'like_notebooks']
        for each_tag in all_time:
            if timeline[each_tag]:
                db['user_timeline'].update({'slug': slug}, {'$push': {each_tag: {'$each': timeline[each_tag]}}})


if __name__ == '__main__':
    getinfo = GetAllInfo()
    allinfo = getinfo.getallinfo('5a7aa9b0cf9e')

    '''
    # 多线程抓取(or更新)用户的基本信息及动态。使用时将代码首部的thredpool线程池打开
    getinfo = GetAllInfo()
    all_mongo_user = [user['slug'] for user in db.user_timeline.find({"followers_num": {'$gte': 100}}, 
                                                                     {'_id': 0, 'slug': 1},
                                                                     no_cursor_timeout=True)]
    threadpool.map(getinfo.getallinfo, all_mongo_user) 
    '''
