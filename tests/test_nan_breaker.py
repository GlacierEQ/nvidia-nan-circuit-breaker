from __future__ import annotations
import unittest
from src.nan_breaker import BreakerState, NanCircuitBreaker

class NBTests(unittest.TestCase):
    def test_trip(self):
        b = NanCircuitBreaker(trip_after=3)
        b.observe(False); b.observe(False); b.observe(False)
        self.assertEqual(b.state, BreakerState.OPEN)
        self.assertFalse(b.allow_step())

    def test_reset(self):
        b = NanCircuitBreaker(trip_after=1)
        b.observe(False)
        b.reset("reset:ops")
        self.assertTrue(b.allow_step())

if __name__ == "__main__":
    unittest.main()
