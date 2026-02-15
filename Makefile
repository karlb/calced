.PHONY: README.md
README.md:
	uvx --from cogapp cog -r README.md

test: test-py test-js

test-py:
	python3 tests/test_classify.py
	python3 tests/test_evaluate.py
	@for f in tests/*.md; do python/calced.py "$$f"; done
	git diff --exit-code -- tests

test-js:
	node web/test.mjs
