---
name: duo-podcast-raw-interview
summary: 真人对谈播客剪辑 SOP（AI 人声分离 + 转写标注 + 可编辑逐字稿 + 保序裁剪 + 音量统一 + 疗愈结尾 + 时间轴映射）
description: |
  针对真人录音（口播/对谈/访谈）的后期剪辑全流程：去背景噪音/BGM、去口癖气口、统一音量、
  接疗愈结尾、生成实测时间轴与发布文案。
  与 duo-podcast-studio（AI/TTS 生成播客）完全分开——本 skill 只处理真实录音素材，不做 TTS 生成。
type: workflow
disable-model-invocation: false
---

# 真人对谈播客剪辑 SOP（raw interview edit）

> 本 skill 汇总自《可持续流浪》Lex 对谈一期的真实剪辑流程（69 分钟双人对谈）。
> 所有可复用脚本在 `references/`，按编号顺序跑即可。每个脚本顶部都有 `DR`（工程目录）和 `PREFIX`（文件名前缀），新一期改这两个变量即可。

## 0. 什么时候用本 skill

- 输入是**真实录音文件**（wav / mp3 / m4a / mov / 甚至裸 pcm 都行），单人口播或双人对谈，需要剪成播客成片。每次给的音频格式不固定，第 0 步会统一转成工程母带。
- 需要：去 BGM/环境噪音、去口癖和长停顿、统一全程音量、接一段疗愈结尾、出可点击时间轴与发布文案。
- **不做** TTS voice 生成（那是 `duo-podcast-studio` 的事）。两类 skill 各管各的，不要混用。

## 1. 总流程（10 步）

| 步 | 做的事 | 脚本 |
|----|--------|------|
| 0 | 源预处理：任意原始录音（wav/mp3/m4a/mov/pcm）→ 44.1k mono wav 工程母带 `pod_src.wav` | `references/01_prep_source.py` |
| 1 | （可选）AI 人声分离：抽 Vocals，削弱 BGM/环境音 ~38% | `references/02_separate_vocals.md`（外部工具 UVR/Demucs） |
| 2 | 转写：whisper / mlx-audio，词级时间戳 → `pod_segments.json` | `references/03_transcribe.py` |
| 3 | 标注：口癖/长停顿/口误检测 → 标注稿 + 候选切点 `pod_cuts.json` | `references/04_detect_cuts.py` |
| 4 | 可编辑逐字稿：标注内联进原文（`⟦词⟧`/`⏸Ns`/`※词※`），交用户删留 | `references/05_gen_editable.py` |
| 5 | 保序裁剪 + 等功率交叉淡化拼接（只留用户留下的 `[Xs]` 段） | `references/06_cut_assemble.py` |
| 6 | AGC 平滑增益：4s 窗 RMS 中值目标，统一全程音量（修"某段变低"） | 同上脚本 §AGC |
| 7 | 合成疗愈结尾（60s pad）+ 1s 交叉淡化拼接 | `references/07_healing_ending.py` |
| 8 | 时间轴映射：源时间 → 成片时间，按关键词定位 Part 锚点 | `references/08_timeline_map.py` |
| 9 | 发布包：文案/封面/校验 → 交给 `duoduo-podcast-release-package` | `references/09_sample_timeline.py` 辅助采样 |
| 10 | 导出 mp3 并校验时长对齐：mp3 时长须与 wav 差 <2s，否则报错删除半截文件，绝不静默交付 | `references/10_export_mp3.py` |

## 2. 关键决策（本期实测结论，别重蹈覆辙）

- **保真 vs AI 分离**：AI 抽人声能削弱 BGM ~38%，但会**轻微改变音色**。**默认走保真**——直接用工程母带 `pod_src.wav`（即你把原始录音交给 01 预处理统一转码后的版本）裁剪，不做分离；只有 BGM 实在盖话、且你接受音色微调时，才用分离版（先跑 `02_separate_vocals.md` 抽人声，再在 06 设 `USE_SEPARATED=True`）。
- **不用 tanh / 软压缩**：曾用 tanh 做句尾回音抑制，结果制造句尾回音 → 废弃。全程只用**乘法线性增益**，零音色改变。
- **写盘用 `wave` 模块，不用 soundfile**：本机 soundfile 写 wav 曾损坏（重装环境后恢复）。保底一律 `wave` 模块写出 int16；soundfile 仅用于读。
- **交叉淡化 0.03s 等功率**：`head + overlap(out[-cf:]*cos + seg[:cf]*sin) + tail`。**经典坑**：忘了拆 head 直接 `sp[:-cf1]*cos + heal[:cf1]*sin` → 广播 shape 不匹配崩溃。正确写法见 `06_cut_assemble.py` 的 `xf_append`。
- **开场段处理**：把"钩子"开场段整体复制到最前（开头插入），正文原位置保留，制造 hook。本期把 4904–4946s 的"全球化"段提到开头。

## 3. 铁律（真人录音剪辑专属）

- **绝不盲切**：只切用户逐条点名 / 标注确认的；自动检测的候选（口癖、长停顿）先列清单交确认再动手（参考 EP18 翻车：自动检测器必误删真实词）。
- **交付前实测**：回读 RMS、每 5 分钟音量曲线、峰值、以及"某段变低"类异常点（本期 20:33）确认已拉平。不看脚本返回就报 done = 违规。
- **保真优先**：用户要原声就走原音源路径，不为降噪牺牲音色。
- **mp3 导出必须带时长校验（见 10_export_mp3.py）**：曾发生 ffmpeg 静默截断成片到一半（68min→32min）还误报成功——永远用 ffprobe 比对 wav/mp3 时长。

## 4. 输入文件约定（新项目改 `DR` + `PREFIX`）

每个脚本顶部：
```python
DR = "/path/to/工程目录"      # 录音 + 中间产物都放这
PREFIX = "pod_"               # 文件名前缀，避免多期混淆
SR = 44100
```
统一约定产物名（脚本自动读写）：
- `pod_src.wav`：工程母带（你给的原始录音经 01 统一转码；所有脚本后续只读它）
- `pod_speech_44k.wav`：AI 分离版人声（可选，仅分离流程产出）
- `pod_segments.json`：词级转写
- `pod_cuts.json`：候选切点
- `pod_标注稿.md` / `pod_可编辑逐字稿.md`：给用户编辑
- `pod_成片.wav`：定稿（保真版，不加 BGM）

## 5. 依赖

- Python：`numpy`、`soundfile`（读）、`wave`（写）、`mlx-audio`（Apple Silicon 转写最快）、`ffmpeg`（格式转）。
- AI 分离：UVR / Demucs（独立装，不在本 skill 内；本期实测 UVR-MDX-NET-Voc_FT 抽人声有效）。

## 6. 与发布衔接

成片定稿后，用 `duoduo-podcast-release-package` 出发布包：时间轴用本 skill `08_timeline_map.py` 的**实测映射**（不是估算），封面按节目视觉规范，文案按 EP32 叙事风格（详见该 skill）。
