# -*- coding: utf-8 -*-
"""步0 · 录音源预处理（通用，支持任意格式）。

用户每次给的原始录音格式不固定：可能是 wav / mp3 / m4a / mov / 甚至裸 pcm。
本脚本把"任意原始录音"统一转成工程母带 pod_src.wav（44.1k / mono / int16）。

之后所有脚本（03 转写、06 裁剪）都只认 pod_src.wav，不再碰原始格式 ——
这样本 skill 可通用于每一期对谈，不绑定某一期的特定文件名。

用法：
  python3 01_prep_source.py <原始录音路径> [pcm采样率] [pcm位深]
  - 普通格式（wav/mp3/m4a/mov...）：ffmpeg 直接转
  - 裸 pcm（无 header）：必须给采样率与位深，例如
      python3 01_prep_source.py rec.pcm 44100 16
  工程目录用环境变量 PODCAST_DIR 指定（产物写那里）；否则写原始文件同级目录。
"""
import os, sys, subprocess, wave, numpy as np

DR = os.environ.get("PODCAST_DIR")
PREFIX = "pod_"
SR = 44100

if len(sys.argv) < 2:
    print("用法: python3 01_prep_source.py <原始录音> [pcm_sr] [pcm_depth]")
    sys.exit(1)

src = sys.argv[1]
if DR is None:
    DR = os.path.dirname(os.path.abspath(src)) or "."
os.makedirs(DR, exist_ok=True)

out_wav = os.path.join(DR, PREFIX + "src.wav")
ext = os.path.splitext(src)[1].lower()

if ext == ".pcm":
    # 裸 pcm：无 header，必须显式给采样率与位深
    pcm_sr = int(sys.argv[2]) if len(sys.argv) > 2 else 44100
    pcm_depth = int(sys.argv[3]) if len(sys.argv) > 3 else 16
    fmt = "s16le" if pcm_depth <= 16 else "s32le"
    cmd = ["ffmpeg", "-y", "-f", fmt, "-ar", str(pcm_sr), "-ac", "1",
           "-i", src, "-ar", str(SR), "-ac", "1", "-c:a", "pcm_s16le", out_wav]
    print("裸 pcm 模式: sr=%d depth=%d fmt=%s" % (pcm_sr, pcm_depth, fmt))
else:
    # 任何带 header 的格式：ffmpeg 自动识别容器与编码
    cmd = ["ffmpeg", "-y", "-i", src, "-ar", str(SR), "-ac", "1", "-c:a", "pcm_s16le", out_wav]
    print("常规格式模式: %s" % ext)

r = subprocess.run(cmd, capture_output=True, text=True)
if r.returncode != 0:
    print("FFMPEG 失败:\n", r.stderr[-2000:])
    sys.exit(1)

# 回读校验非静音（避免转码损坏 / 输出静音）——用 wave 模块读，绕开本机 soundfile 写坏风险
wf = wave.open(out_wav, 'rb')
nf = wf.readframes(wf.getnframes())
wf.close()
xf = np.frombuffer(nf, dtype=np.int16).astype(np.float32) / 32768.0
dur = len(xf) / SR
print("母带写出: %s | %.1fs | SR %d | 峰值 %.4f" % (out_wav, dur, SR, np.max(np.abs(xf))))
# 多点 RMS 抽查，确认转码后真的有声音
for t in [0, 30, 60, 300, 600, max(0, int(dur) - 5)]:
    if t < 0:
        continue
    a = int(t * SR)
    b = int(min(len(xf), (t + 2) * SR))
    print("  %4ds RMS %.4f" % (t, np.sqrt(np.mean(xf[a:b] ** 2))))
