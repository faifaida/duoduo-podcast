# -*- coding: utf-8 -*-
"""步8 · 构建 源录音时间 -> 成片时间 映射，并从逐字稿按关键词定位各 Part 锚点。
拼接顺序必须与 06_cut_assemble.py 一致（opening 提到最前 + kept 保序），否则映射错位。

用法：跑完 06 后跑本脚本，把打印出的锚点抄进发布文案 `## 时间轴`（实测，不是估算）。
"""
import os, json, re, numpy as np

DR = os.environ.get("PODCAST_DIR", "/path/to/工程目录")
PREFIX = "pod_"
SR = 44100
CF = 0.03
DROP = set()                      # 与 06 保持一致
OPEN_LO, OPEN_HI = 0.0, 0.0       # 与 06 保持一致（hook 开场段区间）


def rms(x):
    return float(np.sqrt(np.mean(np.asarray(x, dtype=np.float32) ** 2)))


segs = json.load(open(os.path.join(DR, PREFIX + "segments.json"), encoding="utf-8"))
md = open(os.path.join(DR, PREFIX + "可编辑逐字稿.md"), encoding="utf-8").read().splitlines()

kept_starts = set()
for line in md:
    m = re.match(r'^\s*\[(\d+(?:\.\d+)?)s\]', line)
    if m:
        kept_starts.add(round(float(m.group(1)), 1))


def find_idx(st):
    for i, s in enumerate(segs):
        if abs(round(s["start"], 1) - st) < 0.15:
            return i
    return None


kept = []
for st in kept_starts:
    i = find_idx(st)
    if i is not None:
        kept.append((i, segs[i]))
kept.sort(key=lambda x: x[0])
kept = [(i, s) for i, s in kept if round(s["start"], 1) not in DROP]
opening = [(i, s) for i, s in kept if OPEN_LO <= s["start"] <= OPEN_HI]
order = opening + kept

mapping = []
cum = 0.0
for k, (i, s) in enumerate(order):
    dur = s["end"] - s["start"]
    mapping.append((s["start"], s["end"], cum, cum + dur, k < len(opening)))
    cum += dur - (0 if k == 0 else CF)
print("成片总时长(语音+疗愈前): %.1f s = %.1f min" % (cum, cum / 60))
print("段数: %d (其中开头插入开场段 %d)" % (len(order), len(opening)))


def src_to_film(t, prefer_body=True):
    cands = []
    for (ss, se, fs, fe, is_open) in mapping:
        if ss - 0.05 <= t <= se + 0.05:
            cands.append((fs + (t - ss), is_open))
    if not cands:
        return None
    if prefer_body:
        body = [c for c in cands if not c[1]]
        if body:
            return body[0][0]
    return cands[0][0]


# ---------- 从逐字稿定位各 Part 锚点 ----------
TOPICS = {
    "Part1 回国":      ["回国", "回来", "不适应", "回来以后"],
    "Part2 变洋了":    ["个人主义", "开放", "边界感", "人情", "效率"],
    "Part3 高中同学":  ["高中同学", "同学", "合伙", "朋友一起"],
    "Part4 出海":      ["出海", "海外", "国外市场", "本地化"],
    "Part5 AI":        ["AI", "人工智能", "翻译"],
    "Part6 流浪/扎根": ["扎根", "羡慕", "流浪", "移动"],
}
lines = []
for ln in md:
    m = re.match(r'^\s*\[(\d+(?:\.\d+)?)s\]\s*(.*)$', ln)
    if m:
        lines.append((float(m.group(1)), m.group(2)))

for topic, kws in TOPICS.items():
    print("\n=== %s ===" % topic)
    shown = 0
    for t, txt in lines:
        if any(kw in txt for kw in kws):
            ft = src_to_film(t)
            if ft is None:
                continue
            print("  源%7.1fs -> 成片 %6.1fs (%2d:%02d)  | %s" % (t, ft, int(ft // 60), int(ft % 60), txt[:46]))
            shown += 1
            if shown >= 8:
                break
