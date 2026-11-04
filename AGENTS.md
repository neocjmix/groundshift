# Groundshift agent instructions

Read README.md and docs/ before implementation.

1. Deliver the smallest real working experiment, not a speculative platform.
2. Target a 2022 M2 MacBook Air with 16 GB unified memory. Prefer the best local Metal implementation, not a lowest-common-denominator CUDA-compatible implementation.
3. Preserve a lightweight reconstruction job boundary and versioned world artifact for future backend replacement. Do not abstract GPU internals or build a fake CUDA backend.
4. Use free/open-source tools and local computation. Do not introduce paid services, hosted GPU, accounts, databases or microservices.
5. Verify current upstream CLI, licenses, platform support and output formats rather than guessing commands.
6. Never invent camera poses, coordinate transforms, collision surfaces, performance numbers or successful test results.
7. Distinguish PASS, FAIL and NOT RUN. Static tests do not prove GPU training or browser rendering.
8. Do not commit original footage, private data, large generated assets, API keys or secrets.
9. Follow docs/IMPLEMENTATION.md milestone acceptance criteria and document actual measurements and blockers.
10. Keep changes small, testable and reversible. Prefer simple CLI scripts and explicit error logs.
