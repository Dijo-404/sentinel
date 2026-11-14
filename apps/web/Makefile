.PHONY: install check lint test build preview approval-ui

APPROVAL_UI := ../../packages/approval-ui

# Build SN-013 so file: dependency resolves dist/. Skip npm ci when already installed.
approval-ui:
	@test -d $(APPROVAL_UI)/node_modules || $(MAKE) -C $(APPROVAL_UI) setup
	npm --prefix $(APPROVAL_UI) run build

install: approval-ui
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
