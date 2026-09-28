# sfx-timeline

音效事件时间线：同帧去重、优先级抢占与时序稳定，只用 Python 标准库。

```
python3 -m sfx.cli --script sample
python3 -m unittest discover -s tests -v
```

## 口径（README 为准）

- **同一帧同名音效只播一次**：合并时取最大音量（`hit` 5 与 8 合成一条 8）。
- **语音要抢占**：`priority >= VOICE_PRIORITY`（10）的事件到达时，要打断同通道上正在播的低优先级音效，
  被中断的那条记为 `cut`。
- **同时间戳顺序稳定**：按 (时间升序, 优先级降序, 名字升序) 排序后播放。
  `--script sample` 按口径是 `played=2 cut=2`（只剩两条语音），现在原样播放 5 条，给 `played=5 cut=0`。
- 不变量：`played + cut` 等于输入事件数（去重后）；同一批事件重复播放结果相同；
  语音永远不会被低优先级事件打断。
- 规模：单帧 10 万条事件 0.5 秒内处理完，内存 O(事件数)；不许每条事件都重扫整条时间线。

## 现在的行为

- `play` 直接按输入顺序把事件全放一遍：不去重、不排序、也不做抢占。
- 因此两条 `hit` 会叠着播、`voice` 也盖不住 `step`。

## 计划新增的能力

```
--script sample
```

## 输出

```
played=2 cut=2
event name=voice at=0 volume=9 priority=10
event name=voice at=10 volume=9 priority=10
```

## 目录

```
sfx/timeline.py   去重、排序与抢占
sfx/cli.py        命令行入口
tests/            unittest 用例
```
