# Repository instructions

This repository contains AutoBangumi plugins and their development documentation.

- Keep each plugin self-contained in `plugins/<plugin-id>/`, with its own manifest, dependencies, README and tests.
- Use `ab_sdk` for new AutoBangumi 4.0 plugins. Do not import host internals (`module.*`) or vendor the host application or SDK.
- Read `skills/autobangumi-plugin/SKILL.md` before implementing or migrating a plugin.
- Use a versioned SDK wheel from an upstream Release. Do not assume the SDK is available from PyPI.
- Run manifest validation, relevant plugin tests and packaging from the changed plugin directory when the SDK is available. Report any verification that could not run.
- After changing Python code, run `make format` and `make format-check` from the repository root. These commands use the shared `ruff.toml` and pinned Ruff version; do not format vendored dependencies.
- Do not restore the backend, WebUI, Docker deployment, marketplace registry or host release workflows to this repository.
- Preserve the MIT license and do not commit credentials, local configuration or build archives.
