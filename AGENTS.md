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
11. After verification, package and deploy authorized viewer changes and usable scenes to the existing Railway viewer in the same workflow. Do not stop at a local build or ask for routine deployment approval already covered by the user's standing instruction. Record concrete deployment blockers when completion is not possible.
12. Publish only explicitly authorized derived world artifacts and their necessary public metadata/previews. Original footage, extracted frames, private source URLs, absolute local paths, probe metadata, logs and superseded trials must never be committed or incidentally included in a release. Publication permission does not imply an open redistribution license.
13. Keep every selected usable world clearly accessible in the scene catalog, with honest capture/reconstruction provenance and quality limits. Retain failed or superseded experiments locally instead of presenting them as accepted scenes.
14. Build and validate the curated release locally, publish a fresh checksum-pinned archive, and update the deployment pointer on the Railway-connected branch. Verify deployment status, public file hashes and actual public-browser rendering before calling the release complete. Follow docs/DEPLOYMENT.md and preserve a rollback package.
