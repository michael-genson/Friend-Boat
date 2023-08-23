SHELL := /bin/bash

.PHONY: run
run:
	source env/secrets.sh && \
	export PYTHONPATH=. && \
	export LOG_LEVEL=20 && \
	python src
