# Generated Pandas cleaning and provenance acceptance — 2026-09-21

Delivered Milestone B08: generated Pandas cleaning workflow with provenance tracking, isolated execution in gVisor, run-scoped immutable artifacts, and analysis run lifecycle orchestration. The execution boundary runs strictly inside gVisor (`runsc`) and never executes untrusted or generated Python code on the developer host or in the API process.

Executed evidence:

- `npm run test:postgres`: **114 passed**, no skips, no failures. Covers analysis run lifecycle, idempotent submission, stage progression (`clean_dataset`), run-scoped artifact storage (`cleaned_data`, `cleaning_report`, `generated_script`), and multi-tenant project/run ownership isolation for artifact downloads.
- `npm run check`: **4 JavaScript tests; 69 Python passed, 45 PostgreSQL-only skipped**; lint, format, type checks (`tsc --noEmit` and `mypy`), generated contracts (`api.d.ts` and `openapi.json`), and builds passed.
- `node scripts/python.mjs scripts/test-transformer.py --image sha256:e7ce1168... --inspector-image sha256:f878c5d1...`: **Real gVisor acceptance tests passed**. Validated end-to-end against `samples/synthetic-sales-messy.csv` (245 rows transformed to 240 rows with 5 duplicates removed and whitespace stripped), verified safe rejection of failing scripts, and verified safe rejection of invalid return types under strict sandboxing (`--network=none`, `--read-only`, tmpfs scratch, uid 65532).
- Unit suite `tests/python/test_cleaning.py`: AST validation, safe identifier normalization, and serialization tests passed.

Limitations & Next:

- Analysis runs currently implement stage `clean_dataset`; subsequent stages (`select_features`, `train_baseline`, `evaluate_baseline`, `generate_dashboard`) remain queued for milestones B09–B11.
- Code generation uses deterministic AST-validated heuristics derived from profile metadata. LLM provider integration with bounded token budgets is planned for later iterations.
