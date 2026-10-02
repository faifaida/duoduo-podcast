# -*- coding: utf-8 -*-
"""步3 · 标注：检测口语词/口误/停顿，产出标注稿 + 候选切点。
不删除任何音频，只标注，供用户确认。

检测策略（经实测校准）：
- 口语词：词级精确匹配（强填充建议删 / 弱填充仅标记）
- 口误：段级正则匹配明确自纠正短语（词级误命中率极高，已弃用）
- 停顿：词级时间间隔（≥1s 标记 / ≥2s 长停顿候选删）
- 静音：音频能量交叉验证
"""
import os, json, re
import numpy as np, soundfile as sf

DR = os.environ.get("PODCAST_DIR", "/path/to/工程目录")
PREFIX = "pod_"
SEG = os.path.join(DR, PREFIX + "segments.json")
OUT_MD = os.path.join(DR, PREFIX + "标注稿.md")
OUT_CUTS = os.path.join(DR, PREFIX + "cuts.json")

# 强填充（通常可删，自动候选）
FILLER_STRONG = {"呃", "嗯", "额", "诶", "哦", "啊", "那个", "这个", "对吧", "对不",
                 "你知道吧", "怎么说呢", "我的天", "天哪", "咱", "咱们"}
# 弱填充/连接词（保留，仅标记）
FILLER_WEAK = {"然后", "但是", "所以", "因为", "不过", "其实", "可能", "好像", "我觉得",
               "这样", "那样", "的话", "就是说", "就是的"}
# 段级明确自纠正短语（可靠，口误候选·仅标记供确认）
SLIP_PHRASE = re.compile(r"我的意思是|我是说|更正一下|更正|搞错了|说错了|口误|"
                         r"不对不对|不是不是|刚才说错了|等一下.*?说错了|重新说")

segs = json.load(open(SEG, encoding="utf-8"))
words = []
for s in segs:
    for w in s.get("words") or []:
        words.append((w["start"], w["end"], w["word"], w.get("probability", 1.0)))

filler_hits = []
for (st, en, txt, pr) in words:
    if txt in FILLER_STRONG:
        filler_hits.append((st, en, txt, True))
    elif txt in FILLER_WEAK:
        filler_hits.append((st, en, txt, False))

slip_hits = []
for s in segs:
    txt = s.get("text", "") or ""
    for m in SLIP_PHRASE.finditer(txt):
        slip_hits.append((s.get("start", 0.0), s.get("start", 0.0) + 0.1, m.group()))

PAUSE_SHORT, PAUSE_LONG = 1.0, 2.0
pauses = []
for i in range(1, len(words)):
    gap = words[i][0] - words[i - 1][1]
    if gap >= PAUSE_SHORT:
        pauses.append((words[i - 1][1], words[i][0], gap, gap >= PAUSE_LONG))

# 音频静音交叉验证
silence = []
try:
    audio, sr = sf.read(os.path.join(DR, PREFIX + "16k_mono.wav"))
    if audio.ndim > 1:
        audio = audio[:, 0]
    win = int(0.05 * sr)
    audio = audio[:len(audio) // win * win]
    rms = np.sqrt(np.mean(audio.reshape(-1, win) ** 2, axis=1))
    thr = 0.01
    silent = rms < thr
    i = 0
    n = len(silent)
    while i < n:
        if silent[i]:
            j = i
            while j < n and silent[j]:
                j += 1
            dur = (j - i) * win / sr
            if dur >= PAUSE_SHORT:
                silence.append((i * win / sr, j * win / sr, dur))
            i = j
        else:
            i += 1
except Exception as e:
    print("silence analysis skipped:", e)

md = ["# 对谈 · 转写标注稿\n",
      "> 图例：【强填】口语词建议删  【弱】连接词仅标记  【误】疑似口误(段级)  ⏸n.s=停顿 n 秒(长停顿候选删)\n",
      "---\n"]
for s in segs:
    md.append(f"[{s.get('start'):.1f}s] {s.get('text','')}\n")
md.append("\n## 一、口语词（共 %d 处；强填充 %d / 弱填充 %d）\n" % (
    len(filler_hits), sum(1 for x in filler_hits if x[3]), sum(1 for x in filler_hits if not x[3])))
for st, en, txt, strong in filler_hits:
    md.append(f"- {st:.2f}–{en:.2f}s 【{'强填' if strong else '弱'}】{txt}\n")
md.append("\n## 二、疑似口误（段级自纠正，共 %d 处·仅标记供确认）\n" % len(slip_hits))
for st, en, txt in slip_hits:
    md.append(f"- {st:.1f}s 【误】{txt}\n")
md.append("\n## 三、停顿（词间隔，共 %d 处；长停顿≥2s %d 处·候选删）\n" % (
    len(pauses), sum(1 for p in pauses if p[3])))
for a, b, gap, long in pauses:
    md.append(f"- {a:.2f}–{b:.2f}s ⏸{gap:.1f}s {'（长·候选删）' if long else ''}\n")
md.append("\n## 四、音频静音段（交叉验证，共 %d 处）\n" % len(silence))
for a, b, dur in silence[:200]:
    md.append(f"- {a:.2f}–{b:.2f}s 静音 {dur:.1f}s\n")

open(OUT_MD, "w", encoding="utf-8").write("".join(md))

cuts = []
for st, en, txt, strong in filler_hits:
    if strong:
        cuts.append({"type": "filler", "start": st, "end": en, "text": txt})
for a, b, gap, long in pauses:
    if long:
        cuts.append({"type": "pause", "start": a, "end": b, "dur": round(gap, 2)})
json.dump(cuts, open(OUT_CUTS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("标注稿:", OUT_MD, "| 候选删除:", OUT_CUTS, "共", len(cuts))
print("  口语词=%d(强%d/弱%d) 口误=%d 停顿=%d(长%d) 静音=%d" % (
    len(filler_hits), sum(1 for x in filler_hits if x[3]), sum(1 for x in filler_hits if not x[3]),
    len(slip_hits), len(pauses), sum(1 for p in pauses if p[3]), len(silence)))
