# -*- coding: utf-8 -*-
"""步5+6+7 · 保真版成片构建（核心）。

流程：按用户编辑后的逐字稿，保序裁剪保留的 [Xs] 段 -> 等功率交叉淡化拼接 ->
AGC 平滑增益统一音量 -> 接合成疗愈结尾 -> wave 模块写盘（绕开本机 soundfile 写坏）。

配置（按项目改）：
- USE_SEPARATED=False -> 用工程母带 pod_src.wav（用户原始录音统一转码版；保真，音色100%原样）
- USE_SEPARATED=True  -> 用 pod_speech_44k.wav（AI 分离版，BGM 削弱但音色略变）
- DROP：用户点名要删的句子起始秒集合
- OPEN_LO/OPEN_HI：要提到开头当 hook 的开场段区间（不删，正文保留原位）
- AGC：True=中值目标平滑增益统一音量；False=仅整体线性增益（更保守）
"""
import os, json, re, numpy as np, wave

DR = os.environ.get("PODCAST_DIR", "/path/to/工程目录")
PREFIX = "pod_"
SR = 44100

USE_SEPARATED = False          # 默认保真；要降 BGM 再设 True（需先跑 02 分离）
AGC = True                     # 统一全程音量
DROP = set()                   # 例: {1312.3} 删「可能这就是唯一的规划」
OPEN_LO, OPEN_HI = 0.0, 0.0    # 例: 4904.0, 4946.0 把「全球化」开场提到最前


def rms(x):
    return float(np.sqrt(np.mean(np.asarray(x, dtype=np.float32) ** 2)))


def sf_safe(p):
    """读任意音频为 mono float32（soundfile 仅用于读；写盘用 wave）。"""
    import soundfile as _sf
    x, _sr = _sf.read(p)
    if x.ndim > 1:
        x = x.mean(axis=1)
    return x.astype(np.float32), _sr


# ---------- 1) 载入音源 ----------
# 用户每次给的原始录音格式不固定（wav/mp3/m4a/mov/pcm），已由 01 统一转成工程母带 pod_src.wav。
if USE_SEPARATED:
    src, sr = sf_safe(os.path.join(DR, PREFIX + "speech_44k.wav"))   # AI 分离版（BGM 削弱，音色略变）
else:
    src, sr = sf_safe(os.path.join(DR, PREFIX + "src.wav"))          # 工程母带（保真，音色100%原样）
print("音源: %.1fs 峰值 %.4f RMS %.4f" % (len(src) / SR, np.max(np.abs(src)), rms(src)))

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
before = len(kept)
kept = [(i, s) for i, s in kept if round(s["start"], 1) not in DROP]
print("逐字稿段 %d -> 删句后 %d" % (before, len(kept)))

opening = [(i, s) for i, s in kept if OPEN_LO <= s["start"] <= OPEN_HI]
print("开场段(开头插入): %d  正文段(全保留): %d" % (len(opening), len(kept)))


# ---------- 2) 切片 + 等功率交叉淡化拼接 ----------
def slice_of(s):
    a = int(max(0, s["start"]) * SR)
    b = int(min(len(src), s["end"]) * SR)
    return src[a:b].copy()


def xf_append(out, seg, cf=0.03):
    """等功率交叉淡化拼接。**正确写法**：先拆 head，再 overlap(out[-cf:]*cos + seg[:cf]*sin)，再 tail。
    坑：直接 sp[:-cf1]*cos + heal[:cf1]*sin 会广播 shape 不匹配崩溃。"""
    cf = int(cf * SR)
    if out is None or len(out) == 0:
        return seg.copy()
    if len(seg) == 0:
        return out
    cf = min(cf, len(out), len(seg))
    if cf <= 1:
        return np.concatenate([out, seg])
    head = out[:-cf]
    tail = seg[cf:]
    w = np.linspace(0, 1, cf)
    overlap = out[-cf:] * np.cos(w * np.pi / 2) + seg[:cf] * np.sin(w * np.pi / 2)
    return np.concatenate([head, overlap, tail])


parts = [slice_of(s) for _, s in (opening + kept)]
parts = [p for p in parts if len(p) > 0]
sp = None
for p in parts:
    sp = xf_append(sp, p)
print("语音拼接: %.1fs 峰值 %.4f" % (len(sp) / SR, np.max(np.abs(sp))))


# ---------- 3) AGC 平滑增益统一音量 ----------
if AGC:
    target = float(np.median([rms(src[int(s["start"] * SR):int(s["end"] * SR)]) for _, s in kept[::20]])) * 1.15
    wn, hn = int(4 * SR), int(SR // 2)
    posi = np.arange(0, max(1, len(sp) - wn), hn)
    env = np.array([rms(sp[i:i + wn]) for i in posi], dtype=np.float32)
    g = np.clip(target / (env + 1e-6), 0.35, 3.0)
    g = np.convolve(g, np.ones(9) / 9, mode="same")
    ts = posi + wn // 2
    gain_s = np.interp(np.arange(len(sp), dtype=np.float64), ts.astype(np.float64), g.astype(np.float64)).astype(np.float32)
    sp = sp * gain_s
    sp *= 0.97 / max(1e-9, np.max(np.abs(sp)))
    print("AGC: target RMS %.4f -> 成片 RMS %.4f 峰值 %.4f" % (target, rms(sp), np.max(np.abs(sp))))
else:
    peak = np.max(np.abs(sp))
    gain = min(0.97 / peak, 8.0) if peak > 0 else 1.0
    sp *= gain
    print("线性增益 x%.3f -> 峰值 %.4f RMS %.4f（音色=原录音，仅音量缩放）" % (gain, np.max(np.abs(sp)), rms(sp)))


# ---------- 4) 合成疗愈结尾 + 拼接 ----------
def gen_healing(dur=62.0):
    t = np.linspace(0, dur, int(SR * dur), dtype=np.float64)
    freqs = [110.0, 164.81, 220.0, 277.18, 329.63]
    pad = np.zeros_like(t)
    for kk, f in enumerate(freqs):
        det = 1.0 + 0.0015 * np.sin(2 * np.pi * 0.05 * t + kk)
        lfo = 0.6 + 0.4 * np.sin(2 * np.pi * (0.03 + 0.01 * kk) * t + kk * 1.3)
        p = np.sin(2 * np.pi * f * det * t) * lfo
        p += 0.25 * np.sin(2 * np.pi * 2 * f * det * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.07 * t))
        pad += p * (0.5 ** (kk * 0.6))
    pad /= np.max(np.abs(pad)) + 1e-9
    rng = np.random.default_rng(42)
    noise = rng.standard_normal(t.shape) * 0.02
    b = np.exp(-1.0 / (SR * 0.05))
    z = 0.0
    lp = np.empty_like(noise)
    for n in range(len(noise)):
        z = b * z + (1 - b) * noise[n]
        lp[n] = z
    lp *= 0.5
    sig = (pad * 0.8 + lp * 0.35).astype(np.float64)
    env2 = np.ones_like(t)
    fin, fout = int(4 * SR), int(5 * SR)
    env2[:fin] = np.linspace(0, 1, fin)
    env2[-fout:] = np.linspace(1, 0, fout)
    return (sig * env2 * 0.30).astype(np.float32)


final = xf_append(sp, gen_healing(), cf=1.0)


# ---------- 5) wave 模块写盘（绕开损坏的 soundfile 写） ----------
out_wav = os.path.join(DR, PREFIX + "成片.wav")
fi = np.clip(final, -1.0, 1.0)
w = wave.open(out_wav, 'wb')
w.setnchannels(1)
w.setsampwidth(2)
w.setframerate(SR)
w.writeframes((fi * 32767.0).astype(np.int16).tobytes())
w.close()
print("成片写出: %.1fs = %.1f min RMS %.4f" % (len(final) / SR, len(final) / SR / 60, rms(final)))


# ---------- 6) 回读校验（交付前必跑） ----------
r = wave.open(out_wav, 'rb')
fr_ = r.readframes(r.getnframes())
r.close()
chk = np.frombuffer(fr_, dtype=np.int16).astype(np.float32) / 32768.0
print("回读 MAX %.4f 开场0-45s %.4f 结尾60s %.4f" % (np.max(np.abs(chk)), rms(chk[0:45 * SR]), rms(chk[-60 * SR:])))
print("--- 每5分钟 RMS（应平坦，验证音量统一） ---")
for m in range(0, int(len(chk) / SR) // 300):
    a = m * 300 * SR
    b = min(len(chk), (m + 1) * 300 * SR)
    print("  %2d-%2d min: %.4f" % (m * 5, (m + 1) * 5, rms(chk[a:b])))
