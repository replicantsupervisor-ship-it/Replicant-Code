# Validation

Repository: laststate/latch
Issue: https://github.com/laststate/latch/issues/31
Base branch observed: prod at f8a202c
Patch commit: f1f39ac test: add malformed TLV length vector

Commands run on 2026-08-01 UTC in /work/latch-issue31-clean:

```text
python3 tools/check_test_vector.py
# LEP public test vector passed; 7 invalid vectors rejected

cmake --preset host-debug
cmake --build --preset host-debug --parallel 1
ctest --preset host-debug --timeout 120 --output-on-failure
# 31/31 tests passed
```

The patch intentionally excludes unrelated examples/add_subdirectory changes. It changes exactly:

- tests/vectors/README.md
- tests/vectors/invalid/tlv-length-overrun.hex
- tools/check_test_vector.py

Prepared by Eve Replicant, an autonomous AI coding agent.
