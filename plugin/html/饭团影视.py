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

    host = 'https://fantuansjz.com'

    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
        'Referer': 'https://fantuansjz.com/',
    }

    def homeContent(self, filter):
        data = self.getpq(self.fetch(self.host, headers=self.headers).text)
        result = {}
        classes = []
        for k in data('.fed-navs-title a').items():
            href = k.attr('href') or ''
            if '/sjvodtype/' in href:
                m = re.search(r'/sjvodtype/(\d+)', href)
                if m:
                    classes.append({
                        'type_name': k.text().strip(),
                        'type_id': m.group(1)
                    })
        result['class'] = classes
        result['list'] = self.getlist(data('.fed-list-item'))
        return result

    def homeVideoContent(self):
        pass

    def categoryContent(self, tid, pg, filter, extend):
        url = f"{self.host}/sjvodtype/{tid}.html" if pg == '1' else f"{self.host}/sjvodtype/{tid}---------{pg}.html"
        data = self.getpq(self.fetch(url, headers=self.headers).text)
        result = {}
        result['list'] = self.getlist(data('.fed-list-item'))
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        return result

    def detailContent(self, ids):
        data = self.getpq(self.fetch(f"{self.host}/sjvoddetail/{ids[0]}.html", headers=self.headers).text)

        # 封面图片
        pic = data('.fed-deta-content .fed-list-pics').attr('data-original') or \
              data('.fed-deta-content .fed-list-pics img').attr('src') or ''
        if pic and pic.startswith('/'):
            pic = self.host + pic

        # 基础信息
        vod_name = data('.fed-deta-content h1').text().strip() or \
                   data('.fed-deta-content h3').text().strip()
        remarks = data('.fed-deta-content .fed-list-remarks').text().strip()
        actor, director, year, area = '', '', '', ''
        desc = data('.fed-conv-text').text().strip()

        for li in data('.fed-deta-content ul li').items():
            t = li.text()
            if '主演' in t:
                actor = re.sub(r'^.*?主演[：:]', '', t).strip()
            elif '导演' in t:
                director = re.sub(r'^.*?导演[：:]', '', t).strip()
            elif '年份' in t or '年代' in t:
                m = re.search(r'(\d{4})', t)
                year = m.group(1) if m else ''
            elif '地区' in t or '地址' in t:
                m = re.search(r'[地区址][：:]\s*(.+?)(?:\s|$)', t)
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
        tabs_boxes = data('.fed-tabs-info .fed-tabs-boxs')
        names_box = tabs_boxes.eq(0)
        eps_box = tabs_boxes.eq(1)

        names, plays = [], []
        name_items = list(names_box('.fed-tabs-btn').items())
        ep_lists = list(eps_box('ul.fed-tabs-btm').items())

        for i, n in enumerate(name_items):
            n('span').remove()
            name_text = n.text().strip()
            eps = []
            if i < len(ep_lists):
                for ep in ep_lists[i]('li a').items():
                    ep_href = ep.attr('href') or ''
                    if '/sjvodplay/' in ep_href:
                        eps.append(f"{ep.text().strip()}${ep_href}")
            if eps:
                names.append(name_text)
                plays.append('#'.join(eps))

        vod['vod_play_from'] = '$$$'.join(names)
        vod['vod_play_url'] = '$$$'.join(plays)
        return {'list': [vod]}

    def searchContent(self, key, quick, pg="1"):
        url = f"{self.host}/sjvodsearch/{quote(key)}-------------.html"
        data = self.getpq(self.fetch(url, headers=self.headers).text)
        videos = []
        for i in data('dl .fed-deta-images').items():
            a = i('a.fed-list-pics')
            href = a.attr('href') or ''
            if '/sjvoddetail/' not in href:
                continue
            m = re.search(r'/sjvoddetail/(\d+)', href)
            if not m:
                continue
            img = a.attr('data-original') or ''
            if img and img.startswith('/'):
                img = self.host + img
            videos.append({
                'vod_id': m.group(1),
                'vod_name': a.attr('title') or i('.fed-deta-content h3').text().strip(),
                'vod_pic': img,
                'vod_remarks': i('.fed-list-remarks').text().strip()
            })
        return {'list': videos, 'page': pg}

    def playerContent(self, flag, id, vipFlags):
        data = self.getpq(self.fetch(f"{self.host}{id}", headers=self.headers).text)
        try:
            sc = ''
            for s in data('script').items():
                t = s.text()
                if 'player_aaaa' in t:
                    sc = t
                    break
            if not sc:
                raise Exception('未找到 player_aaaa')
            m = re.search(r'var\s+player_aaaa\s*=\s*(\{.*?\})\s*(?:;|$)', sc, re.DOTALL)
            if not m:
                raise Exception('player_aaaa 解析失败')
            jdata = json.loads(m.group(1))
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
            a = i('a.fed-list-pics')
            href = a.attr('href') or ''
            if '/sjvoddetail/' not in href:
                continue
            m = re.search(r'/sjvoddetail/(\d+)', href)
            if not m:
                continue
            img = a.attr('data-original') or ''
            if img and img.startswith('/'):
                img = self.host + img
            name = a.attr('title') or i('a.fed-list-title').text().strip()
            videos.append({
                'vod_id': m.group(1),
                'vod_name': name,
                'vod_pic': img,
                'vod_remarks': i('span.fed-list-remarks').text().strip()
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
    formatJo = sp.init([])  # 初始化
    # formatJo = sp.homeContent(False)  # 筛选分类(首页 可选)
    # formatJo = sp.homeVideoContent()  # (首页 可选)
    # formatJo = sp.searchContent("斗罗", False, '1')  # 搜索
    # formatJo = sp.categoryContent('1', '1', False, {})  # 分类
    # formatJo = sp.detailContent(['12345'])  # 详情
    formatJo = sp.playerContent("", "/sjvodplay/12345-1-1.html", {})  # 播放
    # formatJo = sp.localProxy({"": ""})  # 代理
    print(formatJo)
