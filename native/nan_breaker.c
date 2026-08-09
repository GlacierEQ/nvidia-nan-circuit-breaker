/* Babel: C — NaN circuit breaker for training step loops. */
#include "nan_breaker.h"

void nan_breaker_init(NanBreaker *b, int trip_after) {
    b->trip_after = trip_after > 0 ? trip_after : 3;
    b->consecutive_bad = 0;
    b->open = 0;
}

int nan_breaker_observe(NanBreaker *b, int finite) {
    if (b->open) return 1;
    if (finite) b->consecutive_bad = 0;
    else {
        b->consecutive_bad++;
        if (b->consecutive_bad >= b->trip_after) b->open = 1;
    }
    return b->open;
}

int nan_breaker_allow(const NanBreaker *b) { return !b->open; }

void nan_breaker_reset(NanBreaker *b) {
    b->open = 0;
    b->consecutive_bad = 0;
}
