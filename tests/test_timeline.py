import unittest

from sfx.timeline import VOICE_PRIORITY, Event, play, sample


class PlayTest(unittest.TestCase):
    def test_empty(self):
        played, cut = play([])
        self.assertEqual((played, cut), ([], 0))

    def test_single_event(self):
        played, _ = play([Event(0, "hit", 5)])
        self.assertEqual(len(played), 1)

    def test_sample_returns_pair(self):
        result = play(sample())
        self.assertEqual(len(result), 2)

    def test_voice_priority_constant(self):
        self.assertEqual(VOICE_PRIORITY, 10)

    def test_events_keep_input_order(self):
        played, _ = play([Event(0, "a", 1), Event(0, "b", 1)])
        self.assertEqual([event.name for event in played], ["a", "b"])


def reference_play(events):
    """参考实现：按时间分帧、组内去重排序、再按优先级抢占。"""
    frames = {}
    for event in events:
        slot = frames.setdefault(event.at, {})
        existing = slot.get(event.name)
        if existing is None:
            slot[event.name] = Event(event.at, event.name, event.volume, event.priority)
        else:
            existing.volume = max(existing.volume, event.volume)
            existing.priority = max(existing.priority, event.priority)
    played = []
    cut = 0
    current = None
    for at in sorted(frames):
        group = sorted(frames[at].values(), key=lambda e: (-e.priority, e.name))
        for event in group:
            if current is not None and current.priority >= VOICE_PRIORITY:
                if event.priority < VOICE_PRIORITY:
                    cut += 1
                    continue
            elif current is not None and event.priority >= VOICE_PRIORITY:
                played.pop()
                cut += 1
            played.append(event)
            current = event
    return played, cut


def fingerprint(played):
    return [(e.at, e.name, e.volume, e.priority) for e in played]


class DedupeTest(unittest.TestCase):
    def test_same_frame_same_name_merges_to_max_volume(self):
        played, cut = play([Event(0, "hit", 5), Event(0, "hit", 8)])
        self.assertEqual(cut, 0)
        self.assertEqual(len(played), 1)
        self.assertEqual(played[0].volume, 8)

    def test_same_name_different_frames_not_merged(self):
        played, cut = play([Event(0, "hit", 5), Event(10, "hit", 8)])
        self.assertEqual((len(played), cut), (2, 0))

    def test_dedupe_does_not_mutate_input(self):
        events = [Event(0, "hit", 5), Event(0, "hit", 8)]
        play(events)
        self.assertEqual([e.volume for e in events], [5, 8])


class PreemptionTest(unittest.TestCase):
    def test_voice_cuts_playing_low_priority(self):
        played, cut = play([Event(0, "hit", 5), Event(5, "voice", 9, VOICE_PRIORITY)])
        self.assertEqual(cut, 1)
        self.assertEqual([e.name for e in played], ["voice"])

    def test_low_priority_suppressed_while_voice_plays(self):
        played, cut = play([Event(0, "voice", 9, VOICE_PRIORITY), Event(5, "hit", 5)])
        self.assertEqual(cut, 1)
        self.assertEqual([e.name for e in played], ["voice"])

    def test_voice_never_cut_by_low_priority(self):
        played, cut = play([
            Event(0, "voice", 9, VOICE_PRIORITY),
            Event(1, "a", 1),
            Event(2, "b", 1),
        ])
        self.assertEqual([e.name for e in played], ["voice"])
        self.assertEqual(cut, 2)

    def test_voice_does_not_cut_voice(self):
        played, cut = play([
            Event(0, "voice", 9, VOICE_PRIORITY),
            Event(5, "voice", 9, VOICE_PRIORITY),
        ])
        self.assertEqual((len(played), cut), (2, 0))

    def test_low_priority_events_coexist(self):
        played, cut = play([Event(0, "a", 1), Event(1, "b", 1)])
        self.assertEqual((len(played), cut), (2, 0))


class OrderingTest(unittest.TestCase):
    def test_same_timestamp_sorted_by_name_within_same_priority(self):
        played, cut = play([
            Event(0, "c", 1),
            Event(0, "a", 1),
            Event(0, "b", 1),
        ])
        self.assertEqual([e.name for e in played], ["a", "b", "c"])
        self.assertEqual(cut, 0)

    def test_same_timestamp_voice_sorted_before_low_priority(self):
        played, cut = play([
            Event(0, "aaa", 1),
            Event(0, "zzz", 1, VOICE_PRIORITY),
        ])
        self.assertEqual([e.name for e in played], ["zzz"])
        self.assertEqual(cut, 1)

    def test_time_ascending(self):
        played, _ = play([Event(10, "late", 1), Event(0, "early", 1)])
        self.assertEqual([e.name for e in played], ["early", "late"])

    def test_deterministic_across_runs(self):
        events = [Event(0, "hit", 5), Event(0, "hit", 8),
                  Event(0, "voice", 9, VOICE_PRIORITY), Event(10, "step", 3)]
        first = play(list(events))
        second = play(list(events))
        self.assertEqual(fingerprint(first[0]), fingerprint(second[0]))
        self.assertEqual(first[1], second[1])


class SampleTest(unittest.TestCase):
    def test_sample_matches_readme(self):
        played, cut = play(sample())
        self.assertEqual((len(played), cut), (2, 2))
        self.assertEqual(fingerprint(played),
                         [(0, "voice", 9, 10), (10, "voice", 9, 10)])


class InvariantTest(unittest.TestCase):
    def test_played_plus_cut_equals_deduped_count(self):
        events = [Event(0, "hit", 5), Event(0, "hit", 8),
                  Event(0, "voice", 9, VOICE_PRIORITY),
                  Event(10, "step", 3), Event(10, "voice", 9, VOICE_PRIORITY)]
        played, cut = play(events)
        self.assertEqual(len(played) + cut, 4)


class RandomCrossCheckTest(unittest.TestCase):
    def test_matches_reference_on_200_random_streams(self):
        import random
        rng = random.Random(20260930)
        names = ["hit", "step", "voice", "boom", "ui"]
        for _ in range(200):
            events = [
                Event(rng.randrange(0, 8), rng.choice(names),
                      rng.randrange(1, 10), rng.choice([1, 1, 2, 5, 10, 12]))
                for _ in range(rng.randrange(0, 40))
            ]
            played, cut = play(events)
            ref_played, ref_cut = reference_play(events)
            self.assertEqual(cut, ref_cut)
            self.assertEqual(fingerprint(played), fingerprint(ref_played))
            deduped = len({(e.at, e.name) for e in events})
            self.assertEqual(len(played) + cut, deduped)


class PerformanceTest(unittest.TestCase):
    def test_100k_events_single_frame_under_half_second(self):
        import time
        events = [Event(0, "sfx%d" % i, i % 10, (i % 12) + 1)
                  for i in range(100000)]
        start = time.perf_counter()
        played, cut = play(events)
        elapsed = time.perf_counter() - start
        self.assertEqual(len(played) + cut, 100000)
        self.assertLess(elapsed, 0.5)


class CliTest(unittest.TestCase):
    def test_sample_cli_output(self):
        import io
        from contextlib import redirect_stdout
        from sfx.cli import main
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            main(["--script", "sample"])
        self.assertEqual(buffer.getvalue().splitlines(), [
            "played=2 cut=2",
            "event name=voice at=0 volume=9 priority=10",
            "event name=voice at=10 volume=9 priority=10",
        ])
