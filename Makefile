test:
	@for f in tests/*.md; do ./calced "$$f"; done
	git diff --exit-code -- tests

test-js:
	node web/test.mjs
