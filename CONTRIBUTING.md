# Contributing to Q-Marauder

Please start with the [architecture](docs/ARCHITECTURE.md),
[feature status](docs/BLE-PARITY.md) and [validation evidence](docs/VALIDATION.md).
Small, focused changes with clear behavior and reproducible checks are easiest to
review. Open an issue first for a substantial new backend or hardware port.

## Report a problem

Include the release or commit, installation method, board/shield/radio model,
expected behavior and steps to reproduce. Distinguish the native portrait display
from the browser console. Include relevant error text and a cropped screenshot or
panel photograph when useful.

Remove passwords, pairing codes, private target names/addresses, location history
and unrelated network observations before posting. Do not attach a private capture
or survey database to a public issue.

## Make a change

1. Create a branch and keep changes focused on one problem or feature.
2. Preserve current display orientation, touch calibration and saved settings.
3. Describe hardware requirements and unsupported states honestly. A menu label
   must not imply that an unavailable backend works.
4. Run checks appropriate to the change. Protocol and backend changes need useful
   fixtures; hardware claims need recorded hardware evidence. Documentation-only
   changes need link, image and factual checks rather than new implementation tests.
5. Update the relevant guide and feature-status row with the resulting behavior.

The usual backend check is:

```sh
python3 -m unittest discover -s tests -v
```

For a release-package check:

```sh
python3 scripts/package.py
```

The package allowlist excludes local profiles and observation databases. Check the
archive before distributing it; do not add local captures to the allowlist.

## Credit and license new dependencies

Record upstream developers, exact source revision, license and the relationship to
Q-Marauder in [CREDITS.md](CREDITS.md) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
Retain required copyright notices. An upstream project without a repository-wide
license is not permission to copy its implementation. Keep externally downloaded
registry and artwork terms separate from the MIT application license.

## UI documentation

Use actual browser screenshots or clearly labeled firmware renders. Do not present
mockups as photographs of working hardware or populate screenshots with invented
radio results. The [gallery](docs/GALLERY.md) documents the reproducible TFT renderer
and its limits. New artwork must include its source and redistribution terms.
