SHELL := /bin/bash

.PHONY: run
run:
	source env/secrets.sh && \
	export PYTHONPATH=. && \
	python src
