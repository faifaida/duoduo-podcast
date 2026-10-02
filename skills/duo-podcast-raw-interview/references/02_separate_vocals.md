# 步1 · AI 人声分离（可选）

> 目标：从录音里抽出人声轨（Vocals），削弱 BGM / 环境噪音约 38%，让人声更突出。

## 何时做
- 默认**不做**（保真优先，AI 分离会轻微改音色）。
- 仅当 BGM / 环境音实在盖话、且用户接受音色微调时才做。

## 工具（独立安装，不在本 skill 内）
- **UVR (Ultimate Vocal Remover)** + 模型 `UVR-MDX-NET-Voc_FT`：本期实测有效，抽出的 `(Vocals)_UVR-MDX-NET-Voc_FT.wav` 即人声轨。
- 或 **Demucs** (`demucs -n htdemucs 录音.wav`)，产出 `vocals.wav`。

## 输出约定
- 抽出的人声轨命名为 `pod_speech_44k.wav`，供 `06_cut_assemble.py` 在 `USE_SEPARATED=True` 时读取。
- 分离产物体积大（本期 1.8GB），成片定稿后移入废纸篓，不要留工程目录。

## 实测结论
- 有音高 BGM 用「频谱减法」无效（会产生 musical noise，SNR 反而恶化）→ 别自己写谱减法，直接用 UVR/Demucs 的神经网络模型。
- 分离后人声 RMS 几乎不变，间隙噪音 RMS 下降约 38%。
