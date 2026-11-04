# Groundshift agent instructions

Read README.md and docs/ before implementation.

1. Deliver the smallest real working experiment, not a speculative platform.
2. Target a 2022 M2 MacBook Air with 16 GB unified memory. Prefer the best local Metal implementation, not a lowest-common-denominator CUDA-compatible implementation.
3. Preserve a lightweight reconstruction job boundary and versioned world artifact for future backend replacement. Do not abstract GPU internals or build a fake CUDA backend.
4. Use free/open-source reconstruction tools and local computation. The user-authorized Railway static viewer is the existing deployment boundary; do not introduce hosted reconstruction, GPU services, accounts, databases or microservices.
5. Verify current upstream CLI, licenses, platform support and output formats rather than guessing commands.
6. Never invent camera poses, coordinate transforms, collision surfaces, performance numbers or successful test results.
7. Distinguish PASS, FAIL and NOT RUN. Static tests do not prove GPU training or browser rendering.
8. Do not commit original footage, private data, large generated assets, API keys or secrets.
9. Follow docs/IMPLEMENTATION.md milestone acceptance criteria and document actual measurements and blockers.
10. Keep changes small, testable and reversible. Prefer simple CLI scripts and explicit error logs.
11. Railway is the user's observation surface, not a production quality gate. Package and deploy authorized viewer changes and every distinct exported experiment in the same workflow, irrespective of visual quality. Do not ask for routine approval; report concrete deployment blockers.
12. Publish explicitly selected derived worlds, necessary public metadata/previews, and licensed public comparison images. Keep private original footage/frames, private source URLs, absolute local paths, raw logs, credentials and model weights local. Publication permission does not imply an open redistribution license. Keep large assets in release attachments, not Git.
13. Make all experimental outcomes easy to find: renderable trials belong in the scene catalog, and failed/cancelled/unexecuted stages belong in the observation report. Label source imagery, generated content, execution status and quality separately. Poor quality is evidence to display, never a reason to hide an experiment. Duplicate binary exports may share a scene with their run lineage recorded.
14. Build and validate the explicit static package locally, publish a fresh checksum-pinned archive, and update the deployment pointer on the Railway-connected branch. Verify deployment status, public file hashes and actual public-browser rendering before calling deployment complete. An experiment may retain FAIL or NOT RUN quality status after successful publication. Follow docs/DEPLOYMENT.md and preserve rollback packages.
