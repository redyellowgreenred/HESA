SHELL := /bin/bash
.ONESHELL:
.DEFAULT_GOAL := run

PYTHON ?= .venv/bin/python
LABEL ?= baseline
FAMILY ?= all
BUDGET ?= 10000
RUNS ?= 10
SEED ?= 0
POP_SIZE ?= 40
CROSSOVER_RATE ?= 0.9
MUTATION_RATE ?=
TOURNAMENT_SIZE ?= 2
ELITE_SIZE ?= 1
X_AXIS ?= evaluations
METRIC ?= best
FORMATS ?= png
TMP_DATA_DIR ?= results/.tmp_batch
LATEST_PLOT_DIR ?= results/report_plots
PLOT_ARCHIVE_ROOT ?= results/plot_runs
LATEST_LOG_FILE ?= results/latest_run.log
LATEST_INFO_FILE ?= results/latest_run_info.txt

.PHONY: help run show list-plots clean

help:
	@echo "make"
	@echo "  Run the full experiment once, delete intermediate CSV data, and keep this run's plots."
	@echo
	@echo "Useful overrides:"
	@echo "  make LABEL=repair"
	@echo "  make FAMILY=maxcut"
	@echo "  make RUNS=3 BUDGET=1000"
	@echo
	@echo "Other targets:"
	@echo "  make show"
	@echo "  make list-plots"
	@echo "  make clean"

run:
	@set -euo pipefail
	run_id="$$(date +%Y%m%d_%H%M%S)"
	archive_dir="$(PLOT_ARCHIVE_ROOT)/$(LABEL)_$${run_id}"
	mkdir -p results "$(PLOT_ARCHIVE_ROOT)" "$(LATEST_PLOT_DIR)" "$${archive_dir}"
	rm -rf "$(TMP_DATA_DIR)" "$(LATEST_PLOT_DIR)"
	mkdir -p "$(TMP_DATA_DIR)" "$(LATEST_PLOT_DIR)"
	echo "Running experiment..."

	batch_cmd=( "$(PYTHON)" batch_run.py \
		--family "$(FAMILY)" \
		--budget "$(BUDGET)" \
		--runs "$(RUNS)" \
		--seed "$(SEED)" \
		--pop-size "$(POP_SIZE)" \
		--crossover-rate "$(CROSSOVER_RATE)" \
		--tournament-size "$(TOURNAMENT_SIZE)" \
		--elite-size "$(ELITE_SIZE)" \
		--output-dir "$(TMP_DATA_DIR)" )

	if [[ -n "$(MUTATION_RATE)" ]]; then
		batch_cmd+=( --mutation-rate "$(MUTATION_RATE)" )
	fi

	{
		printf 'command='
		printf '%q ' "$${batch_cmd[@]}"
		printf '\n'
		"$${batch_cmd[@]}"

		"$(PYTHON)" plot_curves.py \
			--input-csv "$(TMP_DATA_DIR)/all_curves.csv" \
			--output-dir "$${archive_dir}" \
			--formats $(FORMATS) \
			--x-axis "$(X_AXIS)" \
			--mode family \
			--metric "$(METRIC)"
	} | tee "$(LATEST_LOG_FILE)"

	cp "$${archive_dir}"/* "$(LATEST_PLOT_DIR)/"

	{
		echo "label=$(LABEL)"
		echo "family=$(FAMILY)"
		echo "budget=$(BUDGET)"
		echo "runs=$(RUNS)"
		echo "seed=$(SEED)"
		echo "pop_size=$(POP_SIZE)"
		echo "crossover_rate=$(CROSSOVER_RATE)"
		echo "mutation_rate=$(if $(strip $(MUTATION_RATE)),$(MUTATION_RATE),default_1_over_n)"
		echo "tournament_size=$(TOURNAMENT_SIZE)"
		echo "elite_size=$(ELITE_SIZE)"
		echo "x_axis=$(X_AXIS)"
		echo "metric=$(METRIC)"
		echo "formats=$(FORMATS)"
		echo "latest_plot_dir=$(LATEST_PLOT_DIR)"
		echo "archive_dir=$${archive_dir}"
	} > "$(LATEST_INFO_FILE)"

	rm -rf "$(TMP_DATA_DIR)"

	echo
	echo "Latest plots:"
	find "$(LATEST_PLOT_DIR)" -maxdepth 1 -type f | sort
	echo
	echo "Archived plots:"
	find "$${archive_dir}" -maxdepth 1 -type f | sort

show:
	@set -euo pipefail
	if [[ ! -d "$(LATEST_PLOT_DIR)" ]]; then
		echo "No results yet. Run 'make' first."
		exit 0
	fi
	echo "Latest plots:"
	find "$(LATEST_PLOT_DIR)" -maxdepth 1 -type f | sort
	if [[ -f "$(LATEST_INFO_FILE)" ]]; then
		echo
		echo "Latest run info:"
		cat "$(LATEST_INFO_FILE)"
	fi

list-plots:
	@set -euo pipefail
	if [[ ! -d "$(PLOT_ARCHIVE_ROOT)" ]]; then
		echo "No archived plots yet."
		exit 0
	fi
	find "$(PLOT_ARCHIVE_ROOT)" -mindepth 1 -maxdepth 1 -type d | sort

clean:
	@rm -rf "$(TMP_DATA_DIR)" "$(LATEST_PLOT_DIR)" "$(PLOT_ARCHIVE_ROOT)" "$(LATEST_LOG_FILE)" "$(LATEST_INFO_FILE)"
	@echo "Cleaned generated results."
