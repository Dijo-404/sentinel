NPM ?= npm

.PHONY: setup check preview

setup:
	$(NPM) ci

check: setup
	$(NPM) run check

preview: setup
	$(NPM) run preview
