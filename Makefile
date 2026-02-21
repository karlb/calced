.PHONY: README.md deploy-web build-pypi release
README.md:
	uvx --from cogapp cog -r README.md

test: test-py test-js

test-py:
	python3 -m unittest discover -s tests
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
	cp web/og.png "$$TMPDIR/og.png"; \
	printf '<!DOCTYPE html>\n<html>\n<head><meta http-equiv="refresh" content="0;url=./'"$$MAJOR"'/"></head>\n<body></body>\n</html>\n' > "$$TMPDIR/index.html"; \
	touch "$$TMPDIR/.nojekyll"; \
	cd "$$TMPDIR" && git add -A && git commit -m "Deploy web app v$$VERSION" && git push origin gh-pages

build-pypi:
	cp README.md LICENSE python/
	cd python && uv build
	rm python/README.md python/LICENSE

release-python: build-pypi
	uv publish python/dist/*

release: test README.md
	@set -e; \
	if [ -n "$$(git status --porcelain)" ]; then \
		echo "Error: working directory is dirty. Commit changes first."; \
		exit 1; \
	fi; \
	VERSION=$$(grep '^version' python/pyproject.toml | sed 's/.*"\(.*\)".*/\1/'); \
	TAG="v$$VERSION"; \
	if git rev-parse "$$TAG" >/dev/null 2>&1; then \
		echo "Error: tag $$TAG already exists. Bump version in python/pyproject.toml."; \
		exit 1; \
	fi; \
	echo "Releasing $$TAG..."; \
	git tag "$$TAG"; \
	$(MAKE) release-python; \
	$(MAKE) deploy-web; \
	git push origin master "$$TAG"; \
	echo "Released $$TAG"
