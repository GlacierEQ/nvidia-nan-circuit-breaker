from __future__ import annotations
import unittest
from src.nan_breaker import NanCircuitBreaker, BreakerState

class Adv(unittest.TestCase):
    def test_open_blocks_steps(self):
        b = NanCircuitBreaker(trip_after=2)
        b.observe(False); b.observe(False)
        self.assertEqual(b.state, BreakerState.OPEN)
        self.assertFalse(b.allow_step())
    def test_reset_requires_token(self):
        b = NanCircuitBreaker(trip_after=1)
        b.observe(False)
        with self.assertRaises(ValueError):
            b.reset("nope")
    def test_good_resets_streak(self):
        b = NanCircuitBreaker(trip_after=3)
        b.observe(False); b.observe(False); b.observe(True)
        self.assertEqual(b.consecutive_bad, 0)

