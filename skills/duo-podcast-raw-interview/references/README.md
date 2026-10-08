# duo-podcast-raw-interview · 脚本索引

> 真人对谈播客剪辑全流程的可复用脚本。汇总自《可持续流浪》Lex 对谈一期（69 分钟双人对谈）。
> 与 `duo-podcast-studio`（AI/TTS 生成播客）**完全分开**——本目录只处理真实录音。

## 配置（每个新项目改这两处）
每个脚本顶部都有：
```python
DR = os.environ.get("PODCAST_DIR", "/path/to/工程目录")   # 也可直接写死路径
PREFIX = "pod_"                                            # 文件名前缀，避免多期混淆
```
建议用环境变量：`export PODCAST_DIR="/path/to/lex对谈"` 然后跑脚本。

## 跑批顺序

| 顺序 | 脚本 | 输入 → 输出 |
|------|------|------|
| 0 | `01_prep_source.py` | `原始录音(任意格式)` → `pod_src.wav`（ffmpeg 统一转 44.1k mono，回读校验非静音）|
| 1 | `02_separate_vocals.md` | （可选）UVR/Demucs 抽人声 → `pod_speech_44k.wav` |
| 2 | `03_transcribe.py` | `pod_src.wav` → `pod_segments.json`（词级）+ `pod_transcript.txt` |
| 3 | `04_detect_cuts.py` | `pod_segments.json` → `pod_标注稿.md` + `pod_cuts.json`（候选切点）|
| 4 | `05_gen_editable.py` | `pod_segments.json` + `pod_cuts.json` → `pod_可编辑逐字稿.md`（交用户删留）|
| 5 | `06_cut_assemble.py` | 用户改后的 `pod_可编辑逐字稿.md` → `pod_成片.wav`（裁剪+AGC+疗愈+写盘校验）|
| 6 | `07_healing_ending.py` | （独立生成版）`pod_疗愈结尾.wav`；06 已内联同函数，可不单独跑 |
| 7 | `08_timeline_map.py` | 拼接顺序 → 源/成片时间映射 + Part 锚点（抄进发布文案时间轴）|
| 8 | `09_sample_timeline.py` | 成片等间隔采样内容，辅助编排详细时间轴 |
| 9 | `10_export_mp3.py` | `pod_成片.wav` → `pod_成片.mp3`（192k mono，ffprobe 校验时长对齐，差 >2s 删半截文件，绝不静默交付）|

## 关键坑（别重蹈）
1. **写盘用 `wave`，不用 `soundfile`**：本期本机 soundfile 写 wav 损坏过（重装环境恢复）。读可用 soundfile，写一律 `wave` 模块 int16。
2. **交叉淡化要拆 head**：`head + overlap(out[-cf:]*cos + seg[:cf]*sin) + tail`。直接 `a[:-cf]*cos + b[:cf]*sin` 会广播 shape 不匹配崩溃。
3. **别用 tanh 软压缩**：曾制造句尾回音，废弃。只用乘法线性增益。
4. **保真优先**：默认 `USE_SEPARATED=False` 走 `pod_src.wav` 工程母带；AI 分离会改音色。
5. **绝不盲切**：只切用户点名/标注确认的；候选切点先列清单交确认。

## 依赖
`numpy` `soundfile`(读) `wave`(写) `mlx-audio`(Apple Silicon 转写最快) `ffmpeg`(格式转)。AI 分离用 UVR/Demucs（独立装）。
