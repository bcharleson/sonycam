.PHONY: install editable status smoke session

install editable:
	python3.12 -m venv .venv 2>/dev/null || python3 -m venv .venv
	.venv/bin/python -m pip install -U pip setuptools wheel
	.venv/bin/pip install -e .
	@mkdir -p "$(HOME)/.local/bin"
	@ln -sf "$(CURDIR)/.venv/bin/sonycam" "$(HOME)/.local/bin/sonycam"
	@echo "installed: $(HOME)/.local/bin/sonycam"

status:
	sonycam status

session:
	./Scripts/agent-session.sh

smoke:
	sonycam server start
	sonycam connect
	sonycam status
	sonycam set --iso 800 --shutter 1/200
	sonycam rec status
	sonycam pull --list
