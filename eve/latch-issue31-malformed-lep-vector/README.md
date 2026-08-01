# laststate/latch issue #31 patch

This folder contains a clean patch for `laststate/latch` issue #31: add one malformed LEP v1 public test vector and document/check the expected public decoder error.

Files:

- `latch-issue31.patch` — `git format-patch` for applying with `git am`.
- `diff.patch` — plain diff for review.
- `PR_BODY.md` — suggested pull request text.
- `VALIDATION.md` — commands run and results.
- `modified-files/` — copies of the three changed files from the patched tree.

Apply:

```bash
git clone https://github.com/laststate/latch.git
cd latch
git checkout prod
git am /path/to/latch-issue31.patch
python3 tools/check_test_vector.py
cmake --preset host-debug
cmake --build --preset host-debug --parallel 1
ctest --preset host-debug --timeout 120 --output-on-failure
```

Prepared by Eve Replicant, an autonomous AI coding agent.
