"""音效事件时间线：同帧去重、优先级抢占与时序稳定。"""

VOICE_PRIORITY = 10


class Event:
    """一条音效事件。"""

    def __init__(self, at, name, volume, priority=1):
        self.at = at
        self.name = name
        self.volume = volume
        self.priority = priority


def _dedupe(events):
    """同帧同名合并为一条，音量与优先级取最大；不改动入参事件。"""
    merged = {}
    for event in events:
        key = (event.at, event.name)
        existing = merged.get(key)
        if existing is None:
            merged[key] = Event(event.at, event.name, event.volume, event.priority)
        else:
            if event.volume > existing.volume:
                existing.volume = event.volume
            if event.priority > existing.priority:
                existing.priority = event.priority
    return merged


def play(events):
    """去重、排序、抢占后播放，返回 (played, cut)。

    - 同帧同名只播一次，合并取最大音量；
    - 按 (时间升序, 优先级降序, 名字升序) 排序，结果与输入顺序无关；
    - 单通道：priority >= VOICE_PRIORITY 的事件到达时打断正在播的低优先级
      音效（记 cut）；语音在播时到达的低优先级事件播不出来（记 cut）；
      played + cut 恒等于去重后的事件数。
    """
    ordered = sorted(
        _dedupe(events).values(),
        key=lambda event: (event.at, -event.priority, event.name),
    )
    played = []
    cut = 0
    current = None  # 通道上正在播、尚未结算的事件
    for event in ordered:
        if event.priority >= VOICE_PRIORITY:
            if current is not None:
                if current.priority < VOICE_PRIORITY:
                    cut += 1  # 低优先级被语音打断
                else:
                    played.append(current)  # 语音被新语音接替，已正常播出
            current = event
        else:
            if current is not None and current.priority >= VOICE_PRIORITY:
                cut += 1  # 语音在播，低优先级事件播不出来
                continue
            if current is not None:
                played.append(current)  # 低优先级接替低优先级
            current = event
    if current is not None:
        played.append(current)
    return played, cut


def sample():
    """同一帧里两条同名音效 + 一条语音；下一帧又是音效 + 语音。"""
    return [
        Event(0, "hit", 5),
        Event(0, "hit", 8),
        Event(0, "voice", 9, VOICE_PRIORITY),
        Event(10, "step", 3),
        Event(10, "voice", 9, VOICE_PRIORITY),
    ]
