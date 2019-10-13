"""
    百度贴吧帖子分类不同
    不同分类下帖子链接的获取需要不同的xpath
"""

xpath_list = [
    # 普通贴 thread    --> 匹配结果 /p/6294650116
    '//li[@class=" j_thread_list clearfix"]//div[@class="threadlist_lz '
    'clearfix"]//a[@class="j_th_tit "]/@href',
    # 置顶贴 thread_top    --> 匹配结果 /p/6285539829
    '//ul[@id="thread_top_list"]//div[@class="threadlist_lz clearfix"]//a['
    '@class="j_th_tit "]/@href',
    # 今日话题贴 thread_live     --> 匹配结果 //tieba.baidu.com/p/6292645951
    '//dl[@id="threadListGroupCnt"]/dt[@class="listTitleCnt clearfix"]//a['
    '@class="word_live_title"]/@href',
]



















