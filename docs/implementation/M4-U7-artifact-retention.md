# M4-U7 artifact retention — applied 7 November 2026

The user approved the source/generated split and explicitly authorized untracking the exact 377 listed artifacts. Those removals alone are staged. The 65 application, diagnostic, regression, fixture, reusable-tooling and documentation paths remain unstaged; no commit or history rewrite occurred.

## Preservation and inventory

All 879 artifact moves (130,470,075 bytes) and five detailed-record copies were verified against their approved SHA-256 values before original removal or shortening: **884/884 match**. The 377 formerly tracked files account for 59,594,201 bytes. Seven proposal files were separately copied, hash-verified and moved. No archived evidence was deleted. Four open historical acceptance logs were released by stopping the identified old acceptance services; their final hashes still matched, so no changed log version was discarded.

Original relative paths are mirrored below `../../.local-investigation-artifacts/M4-U7/original-tree/`. Evidence is local-only, not supplied by a clone. The [approved move list](../../.local-investigation-artifacts/M4-U7/proposals/source-generated-retention/moves.json), [script classification](../../.local-investigation-artifacts/M4-U7/proposals/source-generated-retention/scripts.json) and [final application inventory/check record](../../.local-investigation-artifacts/M4-U7/retention-application/final-inventory.json) give exact paths and hashes. Historical manifests remain unchanged; original path entries are provenance, not current packaging instructions.

Nine scripts were promoted: two focused browser suites with their config, deterministic fixture server and isolated launcher, plus provider-free pytest review controls. Twenty-one one-run/superseded scripts remain archived. Future modes, temporary documents, captures, logs, results and source identities go to unique directories under the ignored root; configuration and servers reject output locations outside it. Browser suites remain outside default E2E discovery.

Six curated synthetic inputs are retained in `apps/api/tests/fixtures/comparison_advice/`. The [fixture provenance](../../apps/api/tests/fixtures/comparison_advice/provenance.json) records original and promoted hashes and derivations. All six match approved bytes; two derived JSON files were normalized back to the approved LF bytes after patch application. Three affected regression files and reusable fixture servers read these source inputs, never archived captures. Existing provider blocking and dedicated test-database guards remain in place.

## Focused verification

- Three affected regression files plus the promoted review-control test: **38 passed**, one existing Starlette/AnyIO deprecation warning. The first run exposed an obsolete combined-v9 prompt assertion (37 passed, 1 failed); it was corrected to the reviewed v10 selection contract and currency constraints. Production code was not changed and the historical contradiction remains a failure fixture.
- Scoped Python Ruff and Pyright: pass, zero type errors/warnings. Promoted browser-tooling ESLint and full frontend TypeScript checking: pass. ESLint used the already-installed pnpm package directory for plugin resolution; no dependency change or install.
- Explicit Playwright discovery: two corrected-amount and three verification-action cases; no browser/server execution. Both configurations reject output paths outside the ignored root.
- Provider-blocked, database-free fixture smoke checks: corrected-PDF extraction and suggestion/null semantic acceptance pass; three verification-action modes produce valid typed selections. This is tooling/fixture verification, not a new browser or live acceptance run.
- All 13 reviewed application files match the original final-inventory hashes. No production source, protected specification, dependency or lockfile changed during retention.

Promoted source required normal lint/type cleanup, explicit API response types, missing-fixture assertions and output-root guards. These changes are confined to the approved nine tooling destinations. The obsolete prompt assertion correction is in one of the three approved regression files. Final membership remains exactly the approved 65 source paths plus 377 authorized index removals.

[Final acceptance](M4-U7-final-done-check.md) retains the original failed six-submission batch, separate supplemental PASS, source identity, pending human reviews and unresolved causes. Detailed original records remain archived before concise replacements. No unrelated application suite, browser acceptance run or paid call was performed. Commit remains paused.
