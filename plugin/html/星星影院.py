# -*- coding: utf-8 -*-
# by @嗷呜
import re
import sys
import json
from urllib.parse import quote
from pyquery import PyQuery as pq
sys.path.append("..")
from base.spider import Spider


class Spider(Spider):

    def init(self, extend=""):
        pass

    def getName(self):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def action(self, action):
        pass

    def destroy(self):
        pass

    host = 'https://www.cdgdp.com'

    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
        'Referer': 'https://www.cdgdp.com/',
    }

    def homeContent(self, filter):
        data = self.getpq(self.fetch(self.host, headers=self.headers).text)
        result = {}
        classes = []
        for k in data('.myui-header__menu.nav-menu li a').items():
            href = k.attr('href')
            if href and '/xingtp/' in href:
                classes.append({
                    'type_name': k.text(),
                    'type_id': re.search(r'\d+', href).group(0)
                })
        result['class'] = classes
        result['list'] = self.getlist(data('.myui-vodlist__box'))
        return result

    def homeVideoContent(self):
        pass

    def categoryContent(self, tid, pg, filter, extend):
        url = f"{self.host}/xingtp/{tid}.html" if pg == '1' else f"{self.host}/xingtp/{tid}-{pg}.html"
        data = self.getpq(self.fetch(url, headers=self.headers).text)
        result = {}
        result['list'] = self.getlist(data('.myui-vodlist__box'))
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        return result

    def detailContent(self, ids):
        data = self.getpq(self.fetch(f"{self.host}/xingdt/{ids[0]}.html", headers=self.headers).text)

        # 封面图片
        thumb_style = data('.myui-content__thumb .myui-vodlist__thumb').attr('style') or ''
        pic_m = re.search(r'url\(([^)]+)\)', thumb_style)
        pic = pic_m.group(1).strip("'\"") if pic_m else ''
        if pic and pic.startswith('/'):
            pic = self.host + pic

        # 基础信息
        vod_name = data('.myui-content__detail h1.title').text()
        remarks = data('.myui-content__thumb .pic-text.text-right').text()
        actor, director, year, area = '', '', '', ''
        desc = data('.content .sketch').text().strip()

        for p in data('.myui-content__detail .data').items():
            t = p.text()
            if '主演' in t:
                actor = re.sub(r'^.*?主演：', '', t).strip()
            elif '导演' in t:
                director = re.sub(r'^.*?导演：', '', t).strip()
            elif '年份' in t:
                m = re.search(r'年份：(\d{4})', t)
                year = m.group(1) if m else ''
            elif '地区' in t:
                m = re.search(r'地区：(.+?)(?:\s|$)', t)
                area = m.group(1).strip() if m else ''

        vod = {
            'vod_name': vod_name,
            'vod_pic': pic,
            'vod_remarks': remarks,
            'vod_actor': actor,
            'vod_director': director,
            'vod_year': year,
            'vod_area': area,
            'vod_content': desc,
        }

        # 播放源与剧集列表
        names, plays = [], []
        for tab in data('.nav.nav-tabs li a').items():
            href = tab.attr('href') or ''
            if not href.startswith('#playlist'):
                continue
            pid = href.lstrip('#')
            eps = []
            for ep in data(f'#{pid} .myui-content__list li a').items():
                ep_href = ep.attr('href') or ''
                if '/xingpy/' in ep_href:
                    eps.append(f"{ep.text()}${ep_href}")
            if eps:
                names.append(tab.text())
                plays.append('#'.join(eps))

        vod['vod_play_from'] = '$$$'.join(names)
        vod['vod_play_url'] = '$$$'.join(plays)
        return {'list': [vod]}

    def searchContent(self, key, quick, pg="1"):
        url = f"{self.host}/xingsc/{quote(key)}-------------.html"
        data = self.getpq(self.fetch(url, headers=self.headers).text)
        videos = []
        for i in data('.myui-vodlist__media li').items():
            a = i('a.myui-vodlist__thumb')
            href = a.attr('href') or ''
            if '/xingdt/' not in href:
                continue
            img = a.attr('data-original') or ''
            if img and img.startswith('/'):
                img = self.host + img
            videos.append({
                'vod_id': re.search(r'\d+', href).group(0),
                'vod_name': a.attr('title') or i('h4.title a').text(),
                'vod_pic': img,
                'vod_remarks': i('.pic-text.text-right').text()
            })
        return {'list': videos, 'page': pg}

    def playerContent(self, flag, id, vipFlags):
        data = self.getpq(self.fetch(f"{self.host}{id}", headers=self.headers).text)
        try:
            sc = data('.myui-player__video script').eq(0).text()
            jdata = json.loads(sc.split('=', 1)[-1])
            url = jdata.get('url', '')
            if not url:
                raise Exception('未找到播放地址')
            p = 0 if re.search(r'\.m3u8|\.mp4', url) else 1
        except Exception as e:
            print('错误：', e)
            p, url = 1, f"{self.host}{id}"
        return {'parse': p, 'url': url, 'header': self.headers}

    def localProxy(self, param):
        pass

    def getlist(self, data):
        videos = []
        for i in data.items():
            a = i('a.myui-vodlist__thumb')
            href = a.attr('href') or ''
            if '/xingdt/' not in href:
                continue
            style = a.attr('style') or ''
            pic_m = re.search(r'url\(([^)]+)\)', style)
            img = pic_m.group(1).strip("'\"") if pic_m else (a.attr('data-original') or '')
            if img and img.startswith('/'):
                img = self.host + img
            videos.append({
                'vod_id': re.search(r'\d+', href).group(0),
                'vod_name': a.attr('title'),
                'vod_pic': img,
                'vod_remarks': i('.pic-text.text-right').text()
            })
        return videos

    def getpq(self, data):
        try:
            return pq(data)
        except Exception as e:
            print(f"{str(e)}")
            return pq(data.encode('utf-8'))

if __name__ == "__main__":
    sp = Spider()
    formatJo = sp.init([]) # 初始化
    #formatJo = sp.homeContent(False) # 筛选分类(首页 可选)
    #formatJo = sp.homeVideoContent() # (首页 可选)
    # formatJo = sp.searchContent("斗罗",False,'1') # 搜索
    # formatJo = sp.categoryContent('', '1', False, {}) # 分类
    # formatJo = sp.detailContent(['247560']) # 详情
    formatJo = sp.playerContent("", "/xingpy/262128-1-1.html", {}) # 播放
    # formatJo = sp.localProxy({"":""}) # 代理
    print(formatJo)