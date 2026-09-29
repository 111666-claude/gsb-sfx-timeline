"""口径测试：同帧去重、优先级抢占、时序稳定与规模。"""

import random
import time
import unittest

from sfx.timeline import VOICE_PRIORITY, Event, play, sample


def reference_play(events):
    """参考实现：按时间分帧、组内去重排序、再按优先级抢占。"""
    merged = {}
    for event in events:
        key = (event.at, event.name)
        existing = merged.get(key)
        if existing is None:
            merged[key] = [event.volume, event.priority]
        else:
            existing[0] = max(existing[0], event.volume)
            existing[1] = max(existing[1], event.priority)
    frames = {}
    for (at, name), (volume, priority) in merged.items():
        frames.setdefault(at, []).append((name, volume, priority))
    played = []
    cut = 0
    current = None
    for at in sorted(frames):
        group = sorted(frames[at], key=lambda item: (-item[2], item[0]))
        for name, volume, priority in group:
            if priority >= VOICE_PRIORITY:
                if current is not None:
                    if current[3] < VOICE_PRIORITY:
                        cut += 1
                    else:
                        played.append(current)
                current = (name, at, volume, priority)
            else:
                if current is not None and current[3] >= VOICE_PRIORITY:
                    cut += 1
                    continue
                if current is not None:
                    played.append(current)
                current = (name, at, volume, priority)
    if current is not None:
        played.append(current)
    return played, cut


def as_tuples(played):
    return [(event.name, event.at, event.volume, event.priority) for event in played]


class DedupeTest(unittest.TestCase):
    def test_same_frame_same_name_merges_to_max_volume(self):
        played, cut = play([Event(0, "hit", 5), Event(0, "hit", 8)])
        self.assertEqual(cut, 0)
        self.assertEqual(len(played), 1)
        self.assertEqual(played[0].volume, 8)

    def test_same_name_different_frames_not_merged(self):
        played, _ = play([Event(0, "hit", 5), Event(10, "hit", 8)])
        self.assertEqual(len(played), 2)

    def test_input_events_not_mutated(self):
        quiet, loud = Event(0, "hit", 5), Event(0, "hit", 8)
        play([quiet, loud])
        self.assertEqual((quiet.volume, loud.volume), (5, 8))


class PreemptionTest(unittest.TestCase):
    def test_voice_cuts_playing_low_priority(self):
        played, cut = play([Event(0, "step", 3), Event(10, "voice", 9, VOICE_PRIORITY)])
        self.assertEqual(cut, 1)
        self.assertEqual([event.name for event in played], ["voice"])

    def test_low_priority_arriving_during_voice_is_cut(self):
        played, cut = play([Event(0, "voice", 9, VOICE_PRIORITY), Event(10, "step", 3)])
        self.assertEqual(cut, 1)
        self.assertEqual([event.name for event in played], ["voice"])

    def test_voice_never_cut_by_low_priority(self):
        events = [
            Event(0, "voice", 9, VOICE_PRIORITY),
            Event(1, "a", 5), Event(2, "b", 5), Event(3, "c", 5),
        ]
        played, cut = play(events)
        self.assertEqual(cut, 3)
        self.assertEqual([event.name for event in played], ["voice"])

    def test_preemption_keys_on_priority_not_name(self):
        played, cut = play([Event(0, "voice", 3, 1), Event(10, "alarm", 9, VOICE_PRIORITY)])
        self.assertEqual(cut, 1)
        self.assertEqual([event.name for event in played], ["alarm"])

    def test_sample_matches_readme(self):
        played, cut = play(sample())
        self.assertEqual((len(played), cut), (2, 2))
        self.assertEqual([event.name for event in played], ["voice", "voice"])


class OrderingTest(unittest.TestCase):
    def test_same_timestamp_sorted_by_priority_desc_then_name(self):
        events = [
            Event(0, "b", 1),
            Event(0, "a", 1),
            Event(0, "voice", 9, VOICE_PRIORITY),
        ]
        played, cut = play(events)
        self.assertEqual([event.name for event in played], ["voice"])
        self.assertEqual(cut, 2)

    def test_same_priority_same_timestamp_sorted_by_name(self):
        events = [Event(0, "c", 1), Event(0, "a", 1), Event(0, "b", 1)]
        played, _ = play(events)
        self.assertEqual([event.name for event in played], ["a", "b", "c"])

    def test_input_order_does_not_change_result(self):
        base = sample()
        shuffled = list(base)
        random.Random(7).shuffle(shuffled)
        self.assertEqual(as_tuples(play(base)[0]), as_tuples(play(shuffled)[0]))
        self.assertEqual(play(base)[1], play(shuffled)[1])


class InvariantTest(unittest.TestCase):
    def test_played_plus_cut_equals_deduped_count(self):
        rng = random.Random(11)
        for _ in range(50):
            events = [
                Event(rng.randrange(5), rng.choice("abc"), rng.randrange(1, 10),
                      rng.choice([1, 1, 5, VOICE_PRIORITY]))
                for _ in range(rng.randrange(30))
            ]
            played, cut = play(events)
            deduped = len({(event.at, event.name) for event in events})
            self.assertEqual(len(played) + cut, deduped)

    def test_same_frame_same_sound_never_played_twice(self):
        played, _ = play([Event(0, "hit", 5), Event(0, "hit", 8), Event(0, "hit", 6)])
        self.assertEqual([event.name for event in played].count("hit"), 1)


class DifferentialTest(unittest.TestCase):
    def test_matches_reference_on_200_random_streams(self):
        names = ["hit", "step", "voice", "ui", "bgm"]
        priorities = [1, 1, 3, 5, VOICE_PRIORITY, VOICE_PRIORITY, 12]
        for seed in range(200):
            rng = random.Random(seed)
            events = [
                Event(rng.randrange(8), rng.choice(names),
                      rng.randrange(1, 10), rng.choice(priorities))
                for _ in range(rng.randrange(60))
            ]
            played, cut = play(events)
            ref_played, ref_cut = reference_play(events)
            self.assertEqual(as_tuples(played), ref_played, "seed=%d" % seed)
            self.assertEqual(cut, ref_cut, "seed=%d" % seed)


class ScaleTest(unittest.TestCase):
    def test_100k_events_single_frame_under_half_second(self):
        events = [Event(0, "sfx%d" % index, index % 10, index % 12)
                  for index in range(100000)]
        start = time.perf_counter()
        played, cut = play(events)
        elapsed = time.perf_counter() - start
        self.assertEqual(len(played) + cut, 100000)
        self.assertLess(elapsed, 0.5)


if __name__ == "__main__":
    unittest.main()
