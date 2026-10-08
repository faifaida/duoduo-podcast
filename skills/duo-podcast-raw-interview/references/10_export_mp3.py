# -*- coding: utf-8 -*-
"""把成片 wav 导出为 mp3，并强制校验时长对齐（防止静默截断）。
用法: PODCAST_DIR=<工程目录> python3 10_export_mp3.py
默认输入 pod_成片.wav -> 输出 pod_成片.mp3 (192k, mono)。
若 mp3 时长与 wav 相差 > 2s，直接报错并删除半截 mp3（绝不静默交付）。
"""
import os, subprocess, sys

DR = os.environ.get("PODCAST_DIR", ".")
WAV = os.path.join(DR, "pod_成片.wav")
MP3 = os.path.join(DR, "pod_成片.mp3")


def dur(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                          "format=duration", "-of",
                          "default=noprint_wrappers=1:nokey=1", path],
                         capture_output=True, text=True).stdout.strip()
    return float(out)


if not os.path.exists(WAV):
    sys.exit("WAV 不存在: " + WAV)

r = subprocess.run(["ffmpeg", "-y", "-i", WAV, "-codec:a", "libmp3lame",
                    "-b:a", "192k", "-ac", "1", MP3],
                   capture_output=True, text=True)
if r.returncode != 0:
    sys.exit("ffmpeg 失败:\n" + r.stderr[-800:])

dw = dur(WAV)
dm = dur(MP3)
print("wav=%.1fs  mp3=%.1fs" % (dw, dm))
if abs(dw - dm) > 2.0:
    os.remove(MP3)
    sys.exit("❌ 时长不匹配(差 %.1fs)，mp3 已删除，请重导出" % (dw - dm))
print("✅ mp3 时长对齐, %.1f min, %.1f MB" % (dm / 60, os.path.getsize(MP3) / 1e6))
