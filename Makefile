.PHONY: README.md deploy-web build-pypi
README.md:
	uvx --from cogapp cog -r README.md

test: test-py test-js

test-py:
	python3 tests/test_classify.py
	python3 tests/test_evaluate.py
	python3 tests/test_cli.py
	@for f in tests/*.md; do python/calced.py "$$f"; done
	git diff --exit-code -- tests/*.md

test-js:
	node web/test.mjs

deploy-web:
	@set -e; \
	VERSION=$$(grep '^version' python/pyproject.toml | sed 's/.*"\(.*\)".*/\1/'); \
	MAJOR=$$(echo "$$VERSION" | cut -d. -f1); \
	echo "Deploying web app v$$VERSION (major=$$MAJOR)"; \
	TMPDIR=$$(mktemp -d); \
	trap 'git worktree remove --force "$$TMPDIR" 2>/dev/null; rm -rf "$$TMPDIR"' EXIT; \
	if git show-ref --verify --quiet refs/remotes/origin/gh-pages; then \
		git worktree add "$$TMPDIR" gh-pages; \
	else \
		git worktree add --orphan -b gh-pages "$$TMPDIR"; \
	fi; \
	mkdir -p "$$TMPDIR/$$MAJOR"; \
	cp web/index.html "$$TMPDIR/$$MAJOR/index.html"; \
	printf '<!DOCTYPE html>\n<html>\n<head><meta http-equiv="refresh" content="0;url=./'"$$MAJOR"'/"></head>\n<body></body>\n</html>\n' > "$$TMPDIR/index.html"; \
	touch "$$TMPDIR/.nojekyll"; \
	cd "$$TMPDIR" && git add -A && git commit -m "Deploy web app v$$VERSION" && git push origin gh-pages

build-pypi:
	cp README.md LICENSE python/
	cd python && uv build
	rm python/README.md python/LICENSE

release-python: build-pypi
	uv publish python/dist/*
