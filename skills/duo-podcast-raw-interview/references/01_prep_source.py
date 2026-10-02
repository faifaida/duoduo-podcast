# -*- coding: utf-8 -*-
"""步0 · 录音源预处理。
把原始录音整理成标准音源：raw pcm(16bit, 44.1k, mono) -> 44.1k mono wav。
- 用 soundfile 写盘（读可靠）。若本机 soundfile 写 wav 损坏（本期实踩过），改用 wave 模块（见 06_cut_assemble.py 末尾）。
- 若原始是 m4a/mp4，先 `ffmpeg -i in.m4a -ar 44100 -ac 1 raw.pcm` 抽裸 pcm，再跑本脚本。
"""
import os, numpy as np, soundfile as sf

DR = os.environ.get("PODCAST_DIR", "/path/to/工程目录")
PREFIX = "pod_"
SR = 44100

pcm = os.path.join(DR, PREFIX + "raw.pcm")
wav = os.path.join(DR, PREFIX + "44k_mono.wav")

raw = np.fromfile(pcm, dtype=np.int16)
print("pcm 采样数", len(raw), "时长 %.1fs" % (len(raw) / SR))
sf.write(wav, raw, SR)

# 回读验证非静音（防止写盘损坏 / 静音）
x, sr = sf.read(wav)
xf = x.astype(np.float32) / 32768.0
print("回读 wav: SR", sr, "形状", x.shape, "MAX %.4f" % np.max(np.abs(xf)))
for t in [0, 30, 60, 300, 600, int(len(raw) / SR) - 5]:
    if t < 0:
        continue
    a = int(t * sr)
    b = int(min(len(xf), (t + 2) * sr))
    print("  %4ds RMS %.4f" % (t, np.sqrt(np.mean(xf[a:b] ** 2))))
