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
    """同帧同名音效合并为一条，音量与优先级取最大值。"""
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
    return list(merged.values())


def play(events):
    """按 (时间升序, 优先级降序, 名字升序) 播放，语音抢占低优先级音效。

    返回 (played, cut)：played 为实际播放的事件序列，cut 为被中断/压制的事件数。
    不变量：len(played) + cut 等于去重后的事件数。
    """
    timeline = _dedupe(events)
    timeline.sort(key=lambda event: (event.at, -event.priority, event.name))
    played = []
    cut = 0
    current = None
    for event in timeline:
        if current is not None and current.priority >= VOICE_PRIORITY:
            if event.priority < VOICE_PRIORITY:
                # 语音播放中，低优先级事件被压制，记为 cut。
                cut += 1
                continue
        elif current is not None and event.priority >= VOICE_PRIORITY:
            # 语音到达，打断正在播的低优先级音效：它不算播放，记为 cut。
            played.pop()
            cut += 1
        played.append(event)
        current = event
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
