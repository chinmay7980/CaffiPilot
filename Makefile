SHELL := /usr/bin/env bash
.SHELLFLAGS := -eu -o pipefail -c

export PATH := $(HOME)/.local/bin:$(PATH)

AI_API_KEY ?=
ARGS ?=

.PHONY: setup run test clean help

.DEFAULT_GOAL := help

setup:
	@$(MAKE) -C CaffiPilot setup

run:
	@AI_API_KEY="$(AI_API_KEY)" $(MAKE) -C CaffiPilot run ARGS="$(ARGS)"

test:
	@AI_API_KEY="$(AI_API_KEY)" $(MAKE) -C CaffiPilot test

clean:
	@$(MAKE) -C CaffiPilot clean

help:
	@$(MAKE) -C CaffiPilot help
	