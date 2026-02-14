test:
	@for f in tests/*.nc; do ./notecalc "$$f"; done
	git diff --exit-code -- tests

test-js:
	node web/test.mjs
