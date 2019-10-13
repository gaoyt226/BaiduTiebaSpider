"""
    文件创建时间: Sun Oct 13 16:26:45 2019

    抓取指定贴吧中所有帖子里的图片

    ===图片爬取===
    1. 一级页面（贴吧页面）：

        * url:
            第一页： https://tieba.baidu.com/f?kw=%E4%B8%9C%E5%AE%AB&pn=0
            第二页： https://tieba.baidu.com/f?kw=%E4%B8%9C%E5%AE%AB&pn=50
            第n页： https://tieba.baidu.com/f?kw=%E4%B8%9C%E5%AE%AB&pn={(n-1)*50}

            获取n

        * 解析一级页面获取该页所有的帖子链接

    2. 二级页面（帖子页面）：

        * url:
            第一页： 帖子url + ?pn=1
            第n页： 帖子url + ?pn={n}

            获取n

        * 解析二级页面获取该页所有的图片链接
            图片分为该贴相关图片和广告图片（去除）

    3. 三级页面（图片页面）:

        * url:
            从二级页面中直接得出

        * 保存图片

    ==增量爬取==
    1. 将指纹存入数据库中
        create database tiebadb default charset utf8;
        use tiebadb;
        create table fingers (
            finger char(32)
        )charset=utf8;

"""
import requests
from fake_useragent import UserAgent
from lxml import etree
import time, random
from urllib import parse
from thread_category import xpath_list
import re
import os, sys
import pymysql
from hashlib import md5

class TieBaSpider:

    def __init__(self):
        self.url = 'https://tieba.baidu.com/f?kw={}&pn={}'
        self.count = 0

        self.db = pymysql.connect(
            host='127.0.0.1',
            user='root',
            password='123456',
            database='tiebadb',
            port=3306,
            charset='utf8'
        )
        self.cursor = self.db.cursor()

    def get_html(self, url, html=True):
        res = requests.get(url, {'User-Agent': UserAgent().random})
        if html:
            html = res.text
        else:
            html = res.content
        time.sleep(random.randint(1, 3))

        return html

    def parse_html(self, html, pattern):
        parse_html = etree.HTML(html)
        r_list = parse_html.xpath(pattern)

        return r_list

    def close(self):
        self.cursor.close()
        self.db.close()

    def save_finger(self, finger):
        ins = 'insert into fingers values (%s)'
        try:
            self.cursor.execute(ins, [finger])
            self.db.commit()
        except Exception as e:
            print('---mysql insert finger error---', e)
            self.db.rollback()

    def is_saved(self, finger):
        sel = 'select finger from fingers where finger=%s'
        row = self.cursor.execute(sel, [finger])
        if row:
            return True
        return False

    def handle_main(self, links, front):
        # 处理非普通帖
        for link in links:
            thread_link = front + link
            m = md5()
            m.update(thread_link.encode())
            finger = m.hexdigest()
            if self.is_saved(finger):
                break
            self.second_page(thread_link)
            self.save_finger(finger)

    def first_main_page(self, main_url):
        # 帖子首页
        main_html = self.get_html(main_url)

        # 今日话题
        live_pattern = xpath_list[2]
        thread_live_links = self.parse_html(main_html, live_pattern)
        # link: //tieba.baidu.com/p/6292645951
        self.handle_main(thread_live_links, 'http:')

        # 置顶贴
        top_pattern = xpath_list[1]
        thread_top_links = self.parse_html(main_html, top_pattern)
        # link: /p/6294650116
        self.handle_main(thread_top_links, 'http://tieba.baidu.com')

    def first_page(self, first_url):
        # 处理普通帖子
        first_html = self.get_html(first_url)
        pattern = xpath_list[0]
        second_links = self.parse_html(first_html, pattern)

        for link in second_links:
            thread_link = 'http://tieba.baidu.com' + link
            m = md5()
            m.update(thread_link.encode())
            finger = m.hexdigest()

            if self.is_saved(finger):
                return 'done'
            # 处理二级页面
            self.second_page(thread_link)

            self.save_finger(finger)

    def second_page(self, second_url):


        # 帖子id
        thread_id = second_url.split('/')[-1]
        # 存放图片的文件夹
        tieba_directory = 'images/' + self.tieba_name + '/'
        thread_directory = 'thread_' + thread_id + '/'
        directory = tieba_directory + thread_directory

        # 二级页面共有多少页
        second_html = self.get_html(second_url)
        pages_pattern = '//div[@id="thread_theme_7"]' \
                        '//li[@class="l_reply_num"]/span[2]/text()'
        pages_num = int(self.parse_html(second_html, pages_pattern)[0])

        for i in range(pages_num):
            page_url = second_url + '?pn=%s' % (i + 1)

            page_html = self.get_html(page_url)
            pattern = '//div[contains(@class, "p_content  ")]' \
                      '/cc//img[@class="BDE_Image"]/@src'
            image_links = self.parse_html(page_html, pattern)

            # 如果有图片，则创建images/tieba/tiezi/文件夹
            if image_links:
                if not os.path.exists(directory):
                    os.makedirs(directory)

            for link in image_links:
                self.save_image(link, directory)

    def save_image(self, link, directory):
        img = self.get_html(link, html=False)
        file_name = directory + link[-15:]
        with open(file_name, 'wb') as file:
            file.write(img)
        self.count += 1
        print(file_name + ' -- 保存成功 ')
        # time.sleep(random.randint(1, 3))

    def run(self):
        print('=============')
        name = input('请输入贴吧名： ')
        if not name:
            sys.exit('已退出')
        if '吧' in name:
            self.tieba_name = name
        else:
            self.tieba_name = name + '吧'

        kw = parse.quote(self.tieba_name[:-1])
        index_url = self.url.format(kw, 0)
        index_html = self.get_html(index_url)
        pg_num_pattern = '//a[@class="last pagination-item "]/@href'
        href = self.parse_html(index_html, pg_num_pattern)[0]
        if not href:
            print('---**%s** 没有帖子---' % self.tieba_name)
            return
        pg_num = int(href.split('=')[-1]) // 50 + 1

        # 首页非普通帖子
        print('开始增量保存 **%s** 非普通贴中的图片' % self.tieba_name)
        self.first_main_page(self.url.format(kw, 0))
        print('===========**%s** 非普通贴中的图片增量保存完毕=================' % self.tieba_name)

        # 所有普通帖子
        for i in range(pg_num):
            first_url = self.url.format(kw, i * 50)
            print('开始增量保存 **%s** 第--%s--页普通贴中的图片' % (self.tieba_name, i + 1))
            result = self.first_page(first_url)
            print('===========**%s** 第--%s--页普通贴中的图片增量保存完毕=================' %
                  (self.tieba_name, i + 1))
            if result == 'done':
                break
        print('本次增量更新完成, 共更新%s张图片' % self.count)

        self.close()

if __name__ == '__main__':
    # 先测试一下fake_useragent
    if not UserAgent().random:
        print('---fake_useragent error---')

    while True:
        begin = time.time()
        spider = TieBaSpider()
        spider.run()
        end = time.time()
        print('本次保存耗时%s分' % ((end-begin) // 60))





















