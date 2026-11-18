RUFF := uvx --from ruff==0.17.1 ruff

.PHONY: format format-check

format:
	$(RUFF) format --config ruff.toml .

format-check:
	$(RUFF) format --check --config ruff.toml .
