#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
云端构建 rss.xml（小宇宙公开页 -> RSS），无需登录。
专为 GitHub Actions (ubuntu-latest) 设计：检出仓库后运行本脚本，
生成仓库根目录的 rss.xml，由 Action 提交；GitHub Pages 自动重建，
Apple Podcasts / 网易云 / Spotify 自动抓取。

本地调试：python build_rss.py  （会在当前目录写出 rss.xml）
"""
import json
import re
import sys
import time
import urllib.request
from datetime import datetime

PID = "6a5a306305d4bfbabc3ea16b"
PODCAST_URL = f"https://www.xiaoyuzhoufm.com/podcast/{PID}"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
RAW_URL = "https://faifaida.github.io/duoduo-podcast/rss.xml"
COVER = "https://faifaida.github.io/duoduo-podcast/cover.jpg"
SHOW_TITLE = "可持续流浪"
SHOW_LINK = PODCAST_URL
SHOW_DESC = "可持续流浪 —— 一档关于用 AI 重新设计人生的播客。"

_AUDIO_RE = re.compile(r"https://media\.xyzcdn\.net/[^\"'\\ ]+?\.m4a")
_DATE_KEYS = ("pubDate", "updatedAt", "createdAt", "publishedAt", "releaseDate", "displayDate")


def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def next_data(html):
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
                  html, re.S)
    if not m:
        raise RuntimeError("__NEXT_DATA__ not found on 小宇宙页面")
    return json.loads(m.group(1))


def collect(obj, acc):
    if isinstance(obj, dict):
        title = obj.get("title")
        audio = None
        if isinstance(obj.get("url"), str) and _AUDIO_RE.search(obj["url"]):
            audio = _AUDIO_RE.search(obj["url"]).group(0)
        else:
            mm = _AUDIO_RE.search(json.dumps(obj, ensure_ascii=False))
            if mm:
                audio = mm.group(0)
        if audio and title and isinstance(title, str) and title:
            eid = obj.get("eid") or obj.get("id") or obj.get("episodeId")
            if eid:
                acc.setdefault(eid, {
                    "id": eid,
                    "title": title,
                    "audio_url": audio,
                    "shownotes": obj.get("shownotes") or obj.get("description") or "",
                    "published_iso": first_date(obj),
                    "duration": obj.get("duration") or "",
                })
        for v in obj.values():
            collect(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            collect(v, acc)


def first_date(obj):
    for k in _DATE_KEYS:
        v = obj.get(k)
        if isinstance(v, str) and v.strip():
            return v
    return ""


def get_episodes():
    html = fetch(PODCAST_URL)
    data = next_data(html)
    acc = {}
    collect(data, acc)
    eps = list(acc.values())
    if not eps:
        raise RuntimeError("未从小宇宙页面解析到任何单集")
    eps.sort(key=lambda e: (
        -datetime.fromisoformat(e["published_iso"].replace("Z", "+00:00")).timestamp()
        if e.get("published_iso") else 0))
    return eps


def rfc822(iso):
    if not iso:
        return time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime())
    try:
        dt = time.strptime(iso[:19], "%Y-%m-%dT%H:%M:%S")
        return time.strftime("%a, %d %b %Y %H:%M:%S +0000", dt)
    except Exception:
        return time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime())


def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def guid_of(eid):
    return f"https://www.xiaoyuzhoufm.com/episode/{eid}"


def build(eps):
    items = []
    for e in eps:
        items.append(f"""  <item>
    <title>{esc(e['title'])}</title>
    <description><![CDATA[{e.get('shownotes', '')}]]></description>
    <enclosure url="{e['audio_url']}" type="audio/x-m4a"/>
    <guid isPermaLink="false">{guid_of(e['id'])}</guid>
    <pubDate>{rfc822(e.get('published_iso', ''))}</pubDate>
  </item>""")
    items_xml = "\n".join(items)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{SHOW_TITLE}</title>
    <link>{SHOW_LINK}</link>
    <atom:link href="{RAW_URL}" rel="self" type="application/rss+xml"/>
    <description>{esc(SHOW_DESC)}</description>
    <language>zh-CN</language>
    <itunes:author>多多</itunes:author>
    <itunes:owner>
      <itunes:name>多多</itunes:name>
      <itunes:email>fayezang28@gmail.com</itunes:email>
    </itunes:owner>
    <itunes:explicit>false</itunes:explicit>
    <image href="{COVER}"/>
    <itunes:image href="{COVER}"/>
{items_xml}
  </channel>
</rss>
"""


if __name__ == "__main__":
    eps = get_episodes()
    rss = build(eps)
    with open("rss.xml", "w", encoding="utf-8") as f:
        f.write(rss)
    # 校验
    assert rss.count("<item>") == len(eps), "item 数不匹配"
    print(f"OK 集数={len(eps)} 已写出 rss.xml")
