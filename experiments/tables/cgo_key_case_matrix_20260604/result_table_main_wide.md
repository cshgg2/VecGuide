# Main-Table Eligible Result Table

| function | primary_blocker | origin | strong_plain | diagnostic_only | case_card_only | full_method |
| --- | --- | --- | --- | --- | --- | --- |
| s1244 | dependency_unsafe | - | 2.700x; v2/m0; formal; vectorized_speedup | 2.725x; v2/m0; formal; vectorized_speedup | 2.730x; v2/m0; formal; vectorized_speedup | 2.679x; v2/m0; formal; vectorized_speedup |
| s293 | dependency_unsafe | - | 2.403x; v1/m0; formal; vectorized_speedup | 1.000x; v0/m2; formal; non_vectorized_flat | 1.941x; v1/m0; formal; vectorized_speedup | 1.799x; v1/m0; formal; vectorized_speedup |
| s275 | recurrence_reduction | - | 6.042x; v0/m0; formal; non_vectorized_speedup | 0.939x; v0/m2; formal; non_vectorized_slowdown | 6.537x; v0/m0; formal; non_vectorized_speedup | 24.118x; v1/m0; formal; vectorized_speedup |
| s278 | unknown_or_already_vectorized | - | 1.000x; v0/m0; formal; non_vectorized_flat | 2.203x; v1/m0; formal; vectorized_speedup | 2.262x; v1/m0; formal; vectorized_speedup | 2.295x; v1/m0; formal; vectorized_speedup |
