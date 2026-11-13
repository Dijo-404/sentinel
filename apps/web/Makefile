.PHONY: install check lint test build preview

install:
	npm ci

lint:
	npm run lint

test:
	npm test

check: install
	npm run check

build: install
	npm run build

preview: build
	npm run start
