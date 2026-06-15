# Main-Table Eligible Result Table

| function | primary_blocker | origin | strong_plain | diagnostic_only | case_card_only | full_method |
| --- | --- | --- | --- | --- | --- | --- |
| s122 | call_side_effect | - | 0.351x; v0/m5; formal; non_vectorized_slowdown | 0.868x; v1/m6; formal; non_vectorized_slowdown | 2.384x; v3/m3; formal; non_vectorized_speedup | 2.403x; v3/m3; formal; non_vectorized_speedup |
| s172 | call_side_effect | - | - | 2.251x; v2/m5; formal; non_vectorized_speedup | 2.186x; v3/m5; formal; non_vectorized_speedup | 2.230x; v3/m8; formal; non_vectorized_speedup |
| s1113 | dependency_unsafe | - | - | - | 1.049x; v0/m6; formal; non_vectorized_speedup | 1.099x; v0/m6; formal; non_vectorized_speedup |
