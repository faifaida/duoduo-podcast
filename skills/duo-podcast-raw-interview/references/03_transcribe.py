# -*- coding: utf-8 -*-
"""步2 · 转写：词级时间戳 -> pod_segments.json。

Apple Silicon 用 mlx-audio 最快；其他环境换成 openai-whisper / faster-whisper，
只要保证产出 [{start,end,text,words:[{word,start,end,probability}]}] 即可。
"""
import os, json, time
from mlx_audio.stt.generate import generate_transcription, load_model

DR = os.environ.get("PODCAST_DIR", "/path/to/工程目录")
PREFIX = "pod_"

WAV = os.path.join(DR, PREFIX + "src.wav")          # 工程母带（01 预处理统一转码产出）
TXT = os.path.join(DR, PREFIX + "transcript.txt")
JSON = os.path.join(DR, PREFIX + "segments.json")

print("load model...", flush=True)
m = load_model("mlx-community/whisper-large-v3-turbo-asr-fp16")
t0 = time.time()
print("transcribing (word_timestamps)...", flush=True)
r = generate_transcription(model=m, audio=WAV, language="zh", verbose=False,
                           condition_on_previous_text=False, word_timestamps=True)
print("done in %.1fs, segments=%d" % (time.time() - t0, len(r.segments)), flush=True)

open(TXT, "w", encoding="utf-8").write(r.text or "")
segs = [{"start": s.get("start"), "end": s.get("end"),
         "text": s.get("text", ""), "words": s.get("words") or []} for s in r.segments]
json.dump(segs, open(JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("wrote", JSON, "segments=", len(segs))
