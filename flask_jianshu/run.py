import re
from flask import Flask
from flask_jianshu.user_analysis import anlysis_timeline,config
from flask import request
from flask import render_template, redirect,url_for
from pyecharts import WordCloud

app = Flask(__name__)

@app.route('/',methods=['POST','GET'])
def geturl():
    if request.method == 'POST':
        form_value = request.form['url']
        match_result = re.match(r'(http://)?(www.jianshu.com/u/)?(\w{6}|\w{12})$',form_value)
        if match_result:
            user_slug = match_result.groups()[-1]
            return redirect(url_for('jianshu_timeline',slug=user_slug))
        else:
            return render_template('index.html',error_msg='输入的用户主页有问题！请重新输入！')
    return render_template('index.html')

@app.route('/timeline')
def jianshu_timeline():
    slug = request.args.get('slug')
    args = config.TIMELINE_TYPES
    user =anlysis_timeline.AnalysisUser(slug,*args)
    baseinfo = user.get_baseinfo()
    first_tag_time = user.get_first_tag_time()
    tags_data = user.tags_data()
    all_month_data = user.all_tags_data(time_period='month')
    all_day_data = user.all_tags_data(time_period='day')
    all_hour_data = user.all_tags_data(time_period='hour')
    all_week_data = user.all_tags_data(time_period='week')
    share_month_data = user.one_tag_data('share_notes','month')

    week_hour = {}
    for each in args[:5]:
        if baseinfo[each+'_num']>100:
            week_hour[each] = user.tag_week_hour_data(each)
        else:
            week_hour[each] = []
    # share_week_hour_data = user.tag_week_hour_data('share_notes')
    # like_note_week_hour_data = user.tag_week_hour_data('like_notes')
    # comment_note_week_hour_data = user.tag_week_hour_data('comment_notes')
    # reward_note_week_hour_data = user.tag_week_hour_data('reward_notes')
    # like_user_week_hour_data = user.tag_week_hour_data('like_users')
    comments = user.get_comment()
    return render_template('timeline.html',
                           baseinfo = baseinfo,
                           first_tag_time = first_tag_time,
                           tags_data=tags_data,
                           month_data = all_month_data,
                           day_data = all_day_data,
                           hour_data = all_hour_data,
                           week_data = all_week_data,
                           share_month_data=share_month_data[1],
                           week_hour = week_hour,
                           comments_num=comments[0],
                           wordcloud_chart=make_wordcloud(comments[1]),
                           )


def make_wordcloud(comm_data):
    '''
    由于echarts绘制词云图出现问题，用pyecharts绘制词云图
    :param comm_data:
    :return:
    '''
    name = comm_data.keys()
    value = comm_data.values()
    wordcloud = WordCloud(width='100%', height=600)
    wordcloud.add("", name, value, shape="diamond", word_size_range=[15, 120])
    return wordcloud.render_embed()

if __name__ == '__main__':
    app.run(debug=True)

    # app.run(
    #     host = '0.0.0.0',
    #     port = 5000,
    #     debug = True
    # )