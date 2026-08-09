#include "nan_breaker.h"
#include "nan_breaker.c"
#include <stdio.h>
int main(void) {
    NanBreaker b;
    nan_breaker_init(&b, 3);
    nan_breaker_observe(&b, 0);
    nan_breaker_observe(&b, 0);
    nan_breaker_observe(&b, 0);
    if (nan_breaker_allow(&b)) return 1;
    nan_breaker_reset(&b);
    if (!nan_breaker_allow(&b)) return 2;
    printf("ok\n");
    return 0;
}
