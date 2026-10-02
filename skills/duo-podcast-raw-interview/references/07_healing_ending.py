# -*- coding: utf-8 -*-
"""步7 · 合成「疗愈结尾」环境音（独立生成版）。
柔和 pad（5 泛音 + 慢速 LFO 呼吸感）+ 极低通噪声气声，缓入 4s、缓出 5s，无歌词。
输出：pod_疗愈结尾.wav（16k mono）。若想直接内联进成片，06_cut_assemble.py 已含同一函数。
"""
import os, numpy as np, soundfile as sf

DR = os.environ.get("PODCAST_DIR", "/path/to/工程目录")
PREFIX = "pod_"
sr = 16000
dur = 62.0
t = np.linspace(0, dur, int(sr * dur), dtype=np.float64)

freqs = [110.0, 164.81, 220.0, 277.18, 329.63]   # A2/E3/A3/C#4/E4 温暖小调挂留
pad = np.zeros_like(t)
for k, f in enumerate(freqs):
    detune = 1.0 + 0.0015 * np.sin(2 * np.pi * 0.05 * t + k)
    lfo = 0.6 + 0.4 * np.sin(2 * np.pi * (0.03 + 0.01 * k) * t + k * 1.3)
    partial = np.sin(2 * np.pi * f * detune * t) * lfo
    partial += 0.25 * np.sin(2 * np.pi * 2 * f * detune * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.07 * t))
    pad += partial * (0.5 ** (k * 0.6))
pad /= np.max(np.abs(pad)) + 1e-9

rng = np.random.default_rng(42)
noise = rng.standard_normal(t.shape) * 0.02
b = np.exp(-1.0 / (sr * 0.05))
z = 0.0
lp = np.empty_like(noise)
for n in range(len(noise)):
    z = b * z + (1 - b) * noise[n]
    lp[n] = z
lp *= 0.5

sig = pad * 0.8 + lp * 0.4
env = np.ones_like(t)
fin, fout = int(4 * sr), int(5 * sr)
env[:fin] = np.linspace(0, 1, fin)
env[-fout:] = np.linspace(1, 0, fout)
sig *= env * 0.32
sig = sig.astype(np.float32)
sf.write(os.path.join(DR, PREFIX + "疗愈结尾.wav"), sig, sr)
print("疗愈结尾已生成:", round(len(sig) / sr, 1), "s, RMS", round(float(np.sqrt(np.mean(sig ** 2))), 4))
