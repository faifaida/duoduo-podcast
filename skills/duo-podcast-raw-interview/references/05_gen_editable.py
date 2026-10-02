# -*- coding: utf-8 -*-
"""步4 · 生成「可编辑逐字稿」：把口语词/停顿内联标注到原文，供用户直接编辑删改。
依赖：pod_segments.json（词级时间戳）、pod_cuts.json（标注候选）。
输出：pod_可编辑逐字稿.md

读法（写进文件顶部给用户看）：
- `⟦词⟧` = 口语词/连接词（啊/哦/这个/那个/然后…），是否删由用户决定；删时把 `⟦⟧` 和里面的词一起删，原句就留住。
- `⏸Ns`  = 长停顿（静默 N 秒），可删可留。
- `※词※` = 疑似口误。
- 改完把这份文件发回，06 按用户的删改**保序**剪 + 音量统一 + 结尾接疗愈。绝不盲切。
"""
import os, json
from collections import Counter

DR = os.environ.get("PODCAST_DIR", "/path/to/工程目录")
PREFIX = "pod_"

segs = json.load(open(os.path.join(DR, PREFIX + "segments.json")))
cuts = json.load(open(os.path.join(DR, PREFIX + "cuts.json")))

tc = Counter(c.get("type") for c in cuts)
fillers = [c for c in cuts if c.get("type") == "filler"]
pauses = [c for c in cuts if c.get("type") == "pause"]
slips = [c for c in cuts if c.get("type") == "slip"]


def find_filler(w):
    for f in fillers:
        if f.get("text") == w["word"] and not (w["end"] < f["start"] - 0.06 or w["start"] > f["end"] + 0.06):
            return f
    return None


lines = []
lines.append("# 对谈 · 可编辑逐字稿（AI 已标注，删留由你定）")
lines.append("")
lines.append("> **读法**：`⟦词⟧` = 口语词/连接词（啊/哦/这个/那个/然后…），是否删由你决定；删时把 `⟦⟧` 和里面的词一起删，原句就留住了。")
lines.append("> `⏸Ns` = 长停顿（静默 N 秒），可删可留。`※词※` = 疑似口误。")
lines.append("> 改完把这份文件发我，我按你的删改**保序**剪 + 音量统一 + 结尾接疗愈。绝不盲切。")
lines.append("")
lines.append(f"> 全文共 {len(segs)} 段，标注口语词 {len(fillers)} 处、长停顿 {len(pauses)} 处、口误 {len(slips)} 处。")
lines.append("")

for i, s in enumerate(segs):
    if i > 0:
        gap = s["start"] - segs[i - 1]["end"]
        matched = None
        for p in pauses:
            if p["start"] >= segs[i - 1]["end"] - 0.15 and p["end"] <= s["start"] + 0.15:
                matched = p
                break
        if matched:
            lines.append(f"⏸{round(matched['end']-matched['start'],1)}s")
        elif gap > 1.2:
            lines.append(f"⏸{round(gap,1)}s")
    line = ""
    for w in s.get("words", []):
        if find_filler(w):
            line += f"⟦{w['word']}⟧"
        else:
            line += w["word"]
    lines.append(f"[{round(s['start'],1)}s] {line}")

out_path = os.path.join(DR, PREFIX + "可编辑逐字稿.md")
open(out_path, "w").write("\n".join(lines))
print("已写出:", out_path, "行数:", len(lines))
