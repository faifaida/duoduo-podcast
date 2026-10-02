# -*- coding: utf-8 -*-
"""步9 · 按成片时间等间隔采样，打印该时刻在说什么（用于编排详细时间轴 / shownotes）。
拼接顺序与 06 一致；文本取自用户可编辑逐字稿（已含删改）。
"""
import os, json, re

DR = os.environ.get("PODCAST_DIR", "/path/to/工程目录")
PREFIX = "pod_"
SR = 44100
CF = 0.03
DROP = set()
OPEN_LO, OPEN_HI = 0.0, 0.0


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

items = []
cum = 0.0
for k, (i, s) in enumerate(order):
    dur = s["end"] - s["start"]
    items.append((cum, cum + dur, s["start"], k < len(opening)))
    cum += dur - (0 if k == 0 else CF)
TOTAL = cum
print("成片语音总长 %.1f s = %.1f min\n" % (TOTAL, TOTAL / 60))

texts = []
for ln in md:
    m = re.match(r'^\s*\[(\d+(?:\.\d+)?)s\]\s*(.*)$', ln)
    if m:
        texts.append((float(m.group(1)), m.group(2)))
texts.sort()


def near_text(t0, t1):
    return " ".join(tx for t, tx in texts if t0 <= t <= t1)


STEP = 150.0
t = 0.0
while t < TOTAL:
    cand = None
    for (fs, fe, ss, is_open) in items:
        if fs <= t < fe and not is_open:
            cand = (fs, fe, ss)
            break
    if cand is None:
        for (fs, fe, ss, is_open) in items:
            if fs <= t < fe:
                cand = (fs, fe, ss)
                break
    if cand:
        fs, fe, ss = cand
        src_t = ss + (t - fs)
        txt = near_text(src_t, src_t + 12)
        clean = re.sub(r'⟦[^⟧]*⟧', '', txt)
        print("%3d:%02d | %s" % (int(t // 60), int(t % 60), clean[:78]))
    t += STEP
