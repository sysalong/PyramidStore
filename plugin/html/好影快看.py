# -*- coding: utf-8 -*-
# by @嗷呜
import re
import sys
import json
from base64 import b64decode
from urllib.parse import quote, unquote
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

    host = 'https://www.hitv.app'

    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
        'Referer': 'https://www.hitv.app/',
    }

    def homeContent(self, filter):
        data = self.getpq(self.fetch(self.host, headers=self.headers).text)
        result = {}
        classes = []
        for k in data('.navbar-item a').items():
            href = k.attr('href') or ''
            if '/tv/' in href:
                m = re.search(r'/tv/(\d+)', href)
                if m:
                    classes.append({
                        'type_name': k.find('span').text().strip(),
                        'type_id': m.group(1)
                    })
        result['class'] = classes
        result['list'] = self.getlist(data('.module-poster-item.module-item'))
        return result

    def homeVideoContent(self):
        pass

    def categoryContent(self, tid, pg, filter, extend):
        url = f"{self.host}/tv/{tid}.html"
        data = self.getpq(self.fetch(url, headers=self.headers).text)
        result = {}
        result['list'] = self.getlist(data('.module-poster-item.module-item'))
        result['page'] = pg
        result['pagecount'] = 1
        result['limit'] = 90
        result['total'] = 999999
        return result

    def detailContent(self, ids):
        data = self.getpq(self.fetch(f"{self.host}/video/{ids[0]}.html", headers=self.headers).text)

        # 标题与封面
        vod_name = data('h1').eq(0).text().strip()
        pic = data('meta[property="og:image"]').attr('content') or ''

        # 年份与地区（来自标签列）
        tag_links = list(data('.module-info-tag .module-info-tag-link').items())
        year = tag_links[0].text().strip() if len(tag_links) > 0 else ''
        area = tag_links[1].text().strip() if len(tag_links) > 1 else ''

        actor, director, remarks, desc = '', '', '', ''
        for item in data('.module-info-item').items():
            label = item('.module-info-item-title').text()
            if '语言' in label:
                # 最后一个 .module-info-item-content 是集数状态
                contents = item('.module-info-item-content')
                if len(contents) > 0:
                    remarks = contents.eq(len(contents) - 1).text().strip()
            elif '导演' in label:
                director = '、'.join(
                    a.text().strip() for a in item('.module-info-item-content a').items() if a.text().strip()
                )
            elif '主演' in label:
                actor = '、'.join(
                    a.text().strip() for a in item('.module-info-item-content a').items() if a.text().strip()
                )
            elif '剧情简介' in item.text():
                raw = item.text()
                desc = re.sub(r'^.*?剧情简介[：:]', '', raw).strip()

        vod = {
            'vod_name': vod_name,
            'vod_pic': pic,
            'vod_year': year,
            'vod_area': area,
            'vod_actor': actor,
            'vod_director': director,
            'vod_remarks': remarks,
            'vod_content': desc,
        }

        # 播放源与剧集列表
        tabs = data('#y-playList .tab-item')
        ep_lists = data('.module-list.sort-list.tab-list.his-tab-list')
        names, plays = [], []

        for i in range(len(tabs)):
            name = tabs.eq(i).find('span').text().strip()
            eps = []
            for ep in ep_lists.eq(i).find('a.module-play-list-link').items():
                href = ep.attr('href') or ''
                if not href.startswith('/play/'):
                    continue
                ep_name = ep.find('span').text().strip()
                if not ep_name:
                    ep_name = f'第{len(eps) + 1}集'
                eps.append(f"{ep_name}${href}")
            if eps:
                names.append(name)
                plays.append('#'.join(eps))

        vod['vod_play_from'] = '$$$'.join(names)
        vod['vod_play_url'] = '$$$'.join(plays)
        return {'list': [vod]}

    def searchContent(self, key, quick, pg="1"):
        url = f"{self.host}/search/{quote(key)}-------------.html"
        data = self.getpq(self.fetch(url, headers=self.headers).text)
        videos = []
        for i in data('.module-card-item.module-item').items():
            a = i('a.module-card-item-poster')
            href = a.attr('href') or ''
            m = re.search(r'/video/(\d+)', href)
            if not m:
                continue
            img = i('.module-item-pic img').attr('src') or ''
            title = i('.module-card-item-title a').text().strip()
            rem = i('.module-item-note').text().strip()
            videos.append({
                'vod_id': m.group(1),
                'vod_name': title,
                'vod_pic': img,
                'vod_remarks': rem
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
            jdata = json.loads(sc.split('player_aaaa=', 1)[-1].strip().rstrip(';'))
            url = jdata.get('url', '')
            encrypt = int(jdata.get('encrypt', 0))
            if encrypt == 2:
                url = unquote(b64decode(url + '==').decode('utf-8'))
            elif encrypt == 1:
                url = unquote(url)
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
            href = i.attr('href') or ''
            m = re.search(r'/video/(\d+)', href)
            if not m:
                continue
            img = i.find('.module-item-pic img').attr('src') or ''
            name = i.attr('title') or i.find('.module-poster-item-title').text().strip()
            rem = i.find('.module-item-note').text().strip()
            videos.append({
                'vod_id': m.group(1),
                'vod_name': name,
                'vod_pic': img,
                'vod_remarks': rem
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
    # formatJo = sp.categoryContent('1', '1', False, {})  # 分类(电影)
    # formatJo = sp.detailContent(['176673'])  # 详情
    formatJo = sp.playerContent("", "/play/176673-2-1.html", {})  # 播放
    # formatJo = sp.localProxy({"": ""})  # 代理
    print(formatJo)
