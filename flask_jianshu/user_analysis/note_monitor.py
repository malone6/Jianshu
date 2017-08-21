'''用户发表的文章状态监测：'阅读', '评论', '喜欢', '赞赏', '发布时间']'''
from datetime import datetime
import requests
from lxml import etree

headers = { "Accept": "text/html, */*; q=0.01",
            "Accept-Encoding": "gzip, deflate, sdch",
            "Accept-Language": "zh-CN,zh;q=0.8,en;q=0.6,zh-TW;q=0.4",
            "Connection": "keep-alive",
            "Host": "www.jianshu.com",
            "Referer": "http://www.jianshu.com",
            "User-Agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36',
            "X-Requested-With": "XMLHttpRequest",
            "X-PJAX": 'true'}
data = []

def get_notes(slug,page=1):
    keys = ['阅读', '评论', '喜欢', '赞赏', '发布时间', '采集时间', '文章id', '文章标题']
    # if page==1:
        # self.write_to_csv(keys,type='wb')
    url='http://www.jianshu.com/u/{slug}?order_by=shared_at&page={page}'.format(slug=slug,page=page)
    response = requests.get(url,headers=headers)
    tree = etree.HTML(response.text)
    all_li = tree.xpath('//ul[@class="note-list"]//li')
    if all_li:
        for article in all_li:
            note_title = article.xpath('.//a[@class="title"]/text()')[0]
            note_id = article.xpath('.//a[@class="title"]/@href')[0].split('/')[-1]
            push_time = article.xpath('.//span[@class="time"]/@data-shared-at')[0].split('+')[0].replace('T', ' ')
            crawl_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            views_num = int(article.xpath('.//i[@class="iconfont ic-list-read"]/following-sibling::text()')[0].strip())
            if article.xpath('.//i[@class="iconfont ic-list-comments"]'):
                comments_num = int(article.xpath('.//i[@class="iconfont ic-list-comments"]/following-sibling::text()')[0].strip())
            else:
                comments_num = 0

            if article.xpath('.//i[@class="iconfont ic-list-like"]'):
                likes_num = int(article.xpath('.//i[@class="iconfont ic-list-like"]/following-sibling::text()')[0].strip())
            else:
                likes_num = 0

            if article.xpath('.//i[@class="iconfont ic-list-money"]'):
                rewards_num = int(article.xpath('.//i[@class="iconfont ic-list-money"]/following-sibling::text()')[0].strip())
            else:
                rewards_num = 0
            detail = [note_title,note_id,views_num,comments_num,likes_num,rewards_num,push_time,crawl_time]
            print(detail)
            data.append(detail)
        return get_notes(slug,page+1)
    else:
        print(data)
        return data

def anlaysis_notes(data):
    push_time = reversed([note[-2] for note in data])
    views_num = reversed([note[2] for note in data])
    print(push_time,views_num)

if __name__ == '__main__':
    notes_data = get_notes('yZq3ZV')
    anlaysis_notes(notes_data)


