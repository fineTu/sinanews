# coding: UTF-8

from scrapy.spider import Spider
from scrapy.selector import Selector
from scrapy import log
from scrapy.http import Request
import hashlib
import simplejson as json
import time

from sinanews.items import SinanewsItem

import MySQLdb
import sys

# reload(sys)
# sys.setdefaultencoding("utf-8")
class SinanewsSpider(Spider):
    target_list = []
    name = u'getNews'
    allowed_domains = []
    start_urls = []
    def nextTarget(self):
        try:
            self.conn = MySQLdb.connect(host="localhost", user="root", passwd="root", db="newsmetro", port=3306, charset="utf8")
        except MySQLdb.Error,e:
            print "Mysql Error %d: %s" % (e.args[0], e.args[1])

        cur = self.conn.cursor()
        cur.execute('select * from target_point where isRss=false;')
        self.conn.commit()
        for t in cur:
            print t[2]
            yield {'id': t[0], 'url': t[3], 'xpath': t[5], 'regex': t[6],'md5': t[7], 'status': t[9]}
        cur.close()
    def __init__(self):
        self.target_list = self.nextTarget()
        self.current_target = ''
        return

    def start_requests(self):
        self.current_target = self.target_list.next()
        start_url = self.current_target['url']
        yield Request(start_url, dont_filter=True)

    def parse(self, response):
        res_body = response._get_body()
        #print "--------------------->"+res_body
        md5 = hashlib.md5(res_body).hexdigest()
        #md5 = ''
        sel = Selector(response)
        news_list = sel.xpath(self.current_target['xpath']+'//a')
        items = []

        for news in news_list:
            item = SinanewsItem()

            name = news.xpath('text()').extract()[0]
            link = news.xpath('@href').extract()[0]
            print name.encode('utf-8')
            item['title'] = name.encode('utf-8')
            item['link'] = link

            items.append(item)
            log.msg("Appending item...", level='INFO')

        log.msg("Appending done.", level='INFO')
        self.updateInfo(md5, self.current_target, items)
        yield items

        self.current_target = self.target_list.next()
        yield Request(self.current_target['url'], dont_filter=True)


    def updateInfo(self, md5, current_target,items):
        pValue = (md5, self.current_target['id'])
        cur = self.conn.cursor()
        cur.execute('update target_point set md5 = %s where id=%s', pValue)
        self.conn.commit()

        cur = self.conn.cursor()
        cur.execute('select count(*) from target_mapping as tm where tm.target_id=%s', current_target['id'])
        count = cur.fetchone()[0]

        if count == 1:
            jsonStr = self.transJson(items)
            mValue = (jsonStr , time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())), current_target['id'])
            print '----------->>>> update!'+mValue.__str__()
            cur.execute('update target_mapping set items = %s , update_time=%s where target_id=%s', mValue)

        elif count==0:
            jsonStr = self.transJson(items)
            mValue = (current_target['id'], jsonStr , time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())))
            # print '----------->>>> insert!'+mValue.__str__()
            cur.execute('insert into target_mapping(target_id,items,update_time) values(%s,%s,%s)', mValue)

        self.conn.commit()
        return

    def transJson(self,items):
        str = '['
        for i in items:
            str += '{\"title\":\"'+i['title']+'\",\"link\":\"'+i['link']+'\"},'
        str = str[0:-1]
        str += ']'
        # print '----------------->>>>> items String:'+str
        return str
