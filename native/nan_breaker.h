#ifndef NAN_BREAKER_H
#define NAN_BREAKER_H
typedef struct { int trip_after, consecutive_bad, open; } NanBreaker;
void nan_breaker_init(NanBreaker *b, int trip_after);
int nan_breaker_observe(NanBreaker *b, int finite);
int nan_breaker_allow(const NanBreaker *b);
void nan_breaker_reset(NanBreaker *b);
#endif
