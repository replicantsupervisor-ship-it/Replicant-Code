## Summary
- Add one malformed public LEP v1 fixture, `tests/vectors/invalid/tlv-length-overrun.hex`.
- Extend `tools/check_test_vector.py` to assert stable public error categories for invalid fixtures.
- Document the expected `corrupt: tlv` category for the new TLV length overrun vector.

## Validation
- `python3 tools/check_test_vector.py`
- `cmake --preset host-debug`
- `cmake --build --preset host-debug --parallel 1`
- `ctest --preset host-debug --timeout 120 --output-on-failure` (31/31 passed)

Prepared by Eve Replicant, an autonomous AI coding agent. Addresses laststate/latch#31.
