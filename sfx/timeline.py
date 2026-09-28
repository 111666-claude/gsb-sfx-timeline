"""音效事件时间线。

缺陷：同帧同音效不去重、没有优先级抢占、同时间戳直接按输入顺序播。
"""

VOICE_PRIORITY = 10


class Event:
    """一条音效事件。"""

    def __init__(self, at, name, volume, priority=1):
        self.at = at
        self.name = name
        self.volume = volume
        self.priority = priority


def play(events):
    """缺陷：原样按输入顺序播放，不做去重、排序与抢占。"""
    played = []
    for event in events:
        played.append(event)
    return played, 0


def sample():
    """同一帧里两条同名音效 + 一条语音；下一帧又是音效 + 语音。"""
    return [
        Event(0, "hit", 5),
        Event(0, "hit", 8),
        Event(0, "voice", 9, VOICE_PRIORITY),
        Event(10, "step", 3),
        Event(10, "voice", 9, VOICE_PRIORITY),
    ]
