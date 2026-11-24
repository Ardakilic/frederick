# frederick - every command runs inside Docker (python:3.14-slim + pinned
# wheels); you only need Docker and make.
#
#   make              # = make all: generate, test, site
#   make image        # (re)build the Docker build image
#   make generate     # stl/frederick-*.stl + build/manifest.json
#   make test         # pytest
#   make site         # _site/: index.html + the STLs (the GitHub Pages layout)
#   make serve        # serve _site at http://localhost:$(PORT) (Ctrl-C stops it)
#   make shell        # interactive shell in the build image
#   make clean        # delete build/, _site/ and caches
#
# Override any config.py constant per run:
#   make generate GEN_ARGS="--angle 12"
#   make all GEN_ARGS="--set FOOT_D=22.0 --set THROAT_ID=34.2"
#
# GitHub Actions (.github/workflows/pages.yml) runs `make image`, then
# `make generate test site`, and publishes _site/ to GitHub Pages.

IMAGE    := frederick-build
# Runs as your own uid:gid so the files written into the repo stay yours.
DOCKER_RUN := docker run --rm -u $(shell id -u):$(shell id -g) -v "$(CURDIR)":/app -w /app
GEN_ARGS ?=
PORT     ?= 8000

.PHONY: all image generate test site serve shell clean

all: generate test site

image:
	docker build -t $(IMAGE) .

generate: image
	$(DOCKER_RUN) $(IMAGE) python3 generate.py $(GEN_ARGS)

test: image
	$(DOCKER_RUN) $(IMAGE) python3 -m pytest -q

site: image
	$(DOCKER_RUN) $(IMAGE) python3 tools/build_site.py

serve: site
	$(DOCKER_RUN) --init -p $(PORT):8000 $(IMAGE) python3 -m http.server 8000 -d _site

shell: image
	docker run --rm -it -u $(shell id -u):$(shell id -g) -v "$(CURDIR)":/app -w /app $(IMAGE) bash

clean:
	rm -rf build _site .pytest_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
