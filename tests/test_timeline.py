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
