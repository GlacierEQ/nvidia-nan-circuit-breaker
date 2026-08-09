# Babel W4H — nvidia-nan-circuit-breaker

| Dimension | Choice |
|-----------|--------|
| **What** | NaN trip counter |
| **Where** | training step loop |
| **When** | consecutive bad steps |
| **Why** | C zero-overhead inner loop |
| **How** | struct breaker + observe |

**Primary:** `python` · **Companion:** `c`

Independent reference only. No employer affiliation.
