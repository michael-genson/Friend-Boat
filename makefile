SHELL := /bin/bash

.PHONY: run
run:
	source env/secrets.sh && \
	export LOG_LEVEL=20 && \
	export DEBUG=true && \
	sh entry.sh
