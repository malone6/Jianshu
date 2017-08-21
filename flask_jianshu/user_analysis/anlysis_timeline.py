import pymongo
import jieba
from .jianshu_timeline import GetAllInfo
from . import config
from collections import Counter
from datetime import datetime


class AnalysisUser():

    def __init__(self, slug,*args):
        self.client = pymongo.MongoClient(config.MONGO_HOST, config.MONGO_PORT)
        self.db = self.client[config.MONGO_TABLE]
        self.slug = slug
        self.parent_tags = args
        self.zh_parent_tags = ['发表评论','喜欢文章','赞赏文章','发表文章','关注用户','关注专题','点赞评论','关注文集']

        user_data = self.db.user_timeline.find_one({'slug': self.slug})
        update = config.UPDATE
        if user_data and update==False:
            '''如果指定不更新数据且数据已经在mongodb中'''
            self.user_data = user_data
        else:
            '''获取或更新数据到mongodb中'''
            GetAllInfo().getallinfo(slug)
            '''从mongodb中取出该用户的数据'''
            self.user_data = self.db.user_timeline.find_one({'slug': self.slug})


    def get_baseinfo(self):
        baseinfo = {'head_pic':self.user_data['head_pic'],
                    'nickname':self.user_data['nickname'],
                    'update_time':self.user_data['update_time'],
                    'like_users_num':self.user_data['following_num'],
                    'followers_num':self.user_data['followers_num'],
                    'share_notes_num':self.user_data['articles_num'],
                    'words_num':self.user_data['words_num'],
                    'be_liked_num':self.user_data['be_liked_num'],
                    'like_notes_num':len(self.user_data['like_notes']),
                    'like_colls_num':len(self.user_data['like_colls']),
                    'like_nbs_num':len(self.user_data['like_notebooks']),
                    'comment_notes_num':len(self.user_data['comment_notes']),
                    'like_comments_num':len(self.user_data['like_comments']),
                    'reward_notes_num':len(self.user_data['reward_notes'])
                    }
        # print(baseinfo)
        return baseinfo

    def get_first_tag_time(self):
        first_tag_time = {
            'join_time': self.user_data['join_time'],
            'first_like_user': extract_first_tag_time(self.user_data['like_users']),
            'first_share_note': extract_first_tag_time(self.user_data['share_notes']),
            'first_like_note': extract_first_tag_time(self.user_data['like_notes']),
            'first_like_coll': extract_first_tag_time(self.user_data['like_colls']),
            'first_like_nb': extract_first_tag_time(self.user_data['like_notebooks']),
            'first_comment': extract_first_tag_time(self.user_data['comment_notes']),
            'first_like_comment': extract_first_tag_time(self.user_data['like_comments']),
            'first_reward_note': extract_first_tag_time(self.user_data['reward_notes']),
        }
        return first_tag_time


    def tags_data(self):
        tags_name = [{'name':name} for name in self.zh_parent_tags]
        tags_value = [{'value':len(self.user_data[tag])} for tag in self.parent_tags]
        tags_data = [dict(tags_name[i],**tags_value[i]) for i in range(len(tags_name))]
        # print(tags_data)
        return tags_data

    def all_tags_time(self):
        '''all_tags = ('comment_notes', 'like_notes', 'reward_notes','share_notes',
         'like_users', 'like_colls','like_comments', 'like_notebooks')'''
        all_time_list = []
        for tag in self.parent_tags:
            pertime = [each['time'] for each in self.user_data['%s'%tag]]
            all_time_list.extend(pertime)
        # 加入简书的时间
        join_time = self.user_data['join_time']
        if join_time==None:
            pass
        else:
            all_time_list.append(join_time)
        return all_time_list

    def per_tag_time(self, tag):
        '''
        :param tag: 标签，动态的类型
        :return: 子注册以来，发生该种类型动态的所有时间点
        '''
        per_tag_time = [each['time'] for each in self.user_data['%s' % tag]]
        return per_tag_time

    def all_tags_data(self,time_period):
        '''
        根据选择对的时间段，得出注册以来所有动态在时间段内的分布统计
        :param time_period: 时间段。可选'month','week','day','hour'四种类型，分别以月，周，天，小时分类
        :return:
        '''
        if time_period == 'month':
            all_tags_data = extract_month_data(self.all_tags_time())
        elif time_period == 'week':
            all_tags_data = extract_week_data(self.all_tags_time())
        elif time_period == 'day':
            all_tags_data = extract_day_data(self.all_tags_time())
        elif time_period == 'hour':
            all_tags_data = extract_hour_data(self.all_tags_time())
        else:
            all_tags_data = None
        # print(all_tags_data)
        return all_tags_data


    def get_comment(self):
        '''
        抽出所有评论，进行词频统计，得出该用户评论中最常用的词，并绘制词云
        :return:
        '''
        comments = self.user_data['comment_notes']
        text = [c['comment_text'] for c in comments]
        comm_text = ''.join(text)
        comm_text_tmp = jieba.cut(comm_text, 50)
        word_list = list(word for word in comm_text_tmp)
        freq = Counter(word_list).most_common(150)
        comm_word = {x[0]: x[1] for x in freq if len(x[0])>=2}
        # hot_comments = [{'name':list(comm_word.keys())[i],'value':list(comm_word.values())[i]}
        #                 for i in range(len(comm_word))]
        return [len(text),comm_word]


    def one_tag_data(self,tag,time_period):
        '''
        单种动态类型的情况统计
        :param tag: 需要的动态类型，tag可选值可在config.TIMELINE_TYPES中查看，分别对应中文self.zh_parent_tags
        :param time_period: 时间段。可选'month','week','day','hour'四种类型，分别以月，周，天，小时分类
        :return: 动态类型和统计情况组成的列表
        '''
        if time_period == 'month':
            one_tag_data = extract_month_data(self.per_tag_time(tag))
        elif time_period == 'week':
            one_tag_data = extract_week_data(self.per_tag_time(tag))
        elif time_period == 'day':
            one_tag_data = extract_day_data(self.per_tag_time(tag))
        elif time_period == 'hour':
            one_tag_data = extract_hour_data(self.per_tag_time(tag))
        else:
            one_tag_data = None

        zh_tag_type = self.zh_parent_tags[self.parent_tags.index(tag)]
        # print(zh_tag_type,one_tag_data)

        return [zh_tag_type,one_tag_data]

    def tag_week_hour_data(self,*args):
        tag_time_list = []
        for tag in args:
            per_time_list = self.per_tag_time(tag)
            tag_time_list.extend(per_time_list)
        week_hour_list = []
        for time_str in tag_time_list:
            week_hour = date_to_week(time_str)[0]+time_str[11:13]
            week_hour_list.append(week_hour)
        counter_week_hour = Counter(week_hour_list)
        # print(counter_week_hour)
        max_freq = counter_week_hour.most_common(1)[0][1]
        tag_week_hour_data = []
        for x in counter_week_hour.items():
            '''x = ('412',7) <calss 'tuple'>  转换成each=[周几，几点，频率]'''
            each = [int(x[0][0]),int(x[0][1:3]),x[1]]
            tag_week_hour_data.append(each)
        # print(tag_week_hour_data)
        return [max_freq,tag_week_hour_data]



'''以下为辅助函数，用来时间提取及统计'''
def extract_first_tag_time(data):
    '''
    根据给出的data，以时间对列表进行排序，返回列表的第一个值，即为数据列表中的第一次动态
    :param data: 用户某个类型的动态列表，如所有关注用户数据
                {'like_users':[{'slug': 'y3Dbcz', 'time': '2013-05-24 18:26:01'},
                                {'slug': '2f1c0190679d', 'time': '2014-02-11 13:02:03'}]}
    :return: 数据列表中的第一次动态
    '''
    if data:
        sorted_data = sorted(data,key=lambda each: each['time'])
        first_tag_time = sorted_data[0]
        return first_tag_time
    else:
        return None

def extract_time_func(time_list, start, end):
    '''
    根据给出的时间点列表，进行时间分片，和时间段统计
    :param time_list: 时间点列表
    :param start: 时间分片的起始点，例如1999-09-09 09:09:09，通过对此时间串分片得出月份：1999-09、小时：09时等
    :param end: 时间分片的起始点
    :return: 各时间段的动态频次
    '''
    if time_list:
        user_time_you_want = [time[start:end] for time in time_list]
        counter_you_want_f = Counter(user_time_you_want)
        sort_counter = sorted(counter_you_want_f.items(), key=lambda t: t[0])
        data = {'time_slot': [a[0] for a in sort_counter],
                'freqency': [a[1] for a in sort_counter]}
        return data
    else:
        return None

def extract_month_data(time_list):
    '''
    根据给出的得时间列表，以月为时间段，统计每月动态频次
    :param time_list: 时间列表
    :return:
    '''
    if time_list:
        data = extract_time_func(time_list, 0, 7)
        month_data = {'month_line': data['time_slot'], 'month_freqency': data['freqency']}
        # print(month_data)
        return month_data
    else:
        return None

def extract_day_data(time_list):
    '''函数功能同上'''
    if time_list:
        data = extract_time_func(time_list, 0, 10)
        day_data = {'day_line': data['time_slot'], 'day_freqency': data['freqency']}
        # print(day_data)
        return day_data
    else:
        return None

def extract_week_data(time_list):
    if time_list:
        '''函数功能同上'''
        user_week_you_want = [date_to_week(x) for x in time_list]
        counter_you_want_f = Counter(user_week_you_want)
        sort_counter = sorted(counter_you_want_f.items(), key=lambda t: t[0])
        week_data = {'week_line': [a[0][1:] for a in sort_counter],
                'week_freqency': [a[1] for a in sort_counter]}
        # print(data)
        return week_data
    else:
        return None

def date_to_week(string_date):
    '''
    通过datetime模块，将时间串转化为周
    :param string_date: 时间串列表
    :return: 周列表
    '''
    time = datetime.strptime(string_date, '%Y-%m-%d %H:%M:%S')
    week_day = time.weekday()
    week_day_dict = {0: '0周一', 1: '1周二', 2: '2周三', 3: '3周四',
                     4: '4周五', 5: '5周六', 6: '6周日', }
    return week_day_dict[week_day]


def extract_hour_data(time_list):
    '''函数功能同上'''
    data = extract_time_func(time_list, 11, 13)
    hour_data = {'hour_line': [x + ':00' for x in data['time_slot']], 'hour_freqency': data['freqency']}
    # print(hour_data)
    return hour_data


if __name__ == '__main__':
    slug = 'yZq3ZV'
    args = config.TIMELINE_TYPES
    user = AnalysisUser(slug, *args)

    # tags_data = user.tags_data()
    # all_month_data = user.all_tags_data(time_period='month')
    # all_day_data = user.all_tags_data(time_period='day')
    # all_hour_data = user.all_tags_data(time_period='hour')
    # all_week_data = user.all_tags_data(time_period='week')
    # comments = user.get_comment()
    # share_month_data = user.one_tag_data(tag='like_notes',time_period='month')
    # share_week_hour = user.tag_week_hour_data(tag='share_notes')
    # baseinfo  = user.get_baseinfo()
    first_tag_time = user.get_first_tag_time()


