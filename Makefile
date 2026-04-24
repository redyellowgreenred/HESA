SHELL := /bin/bash
.ONESHELL:
.DEFAULT_GOAL := run

PYTHON ?= .venv/bin/python
PYTHON_UNBUFFERED ?= 1
SMOKE_BUDGET ?= 200
SMOKE_RUNS ?= 1
FULL_BUDGET ?= 10000
FULL_RUNS ?= 10
LABEL ?= baseline
FAMILY ?= all
BUDGET ?= 10000
RUNS ?= 10
SEED ?= 0
POP_SIZE ?= 40
CROSSOVER_RATE ?= 0.9
MUTATION_RATE ?=
ONE_PROB ?=
TOURNAMENT_SIZE ?= 2
ELITE_SIZE ?= 1
X_AXIS ?= evaluations
METRIC ?= best
FORMATS ?= png
TMP_DATA_DIR ?= results/.tmp_batch
LATEST_PLOT_DIR ?= results/report_plots
PLOT_ARCHIVE_ROOT ?= results/plot_runs
FINAL_PLOT_ROOT ?= results/final_plots
VERSION_STATE_DIR ?= results/.version_state
FORMAL_STATE_ROOT ?= results/.formal_state
VERSION_KEY ?= $(LABEL)
FORMAL_TRACK_KEY ?= $(LABEL)
LATEST_LOG_FILE ?= results/latest_run.log
LATEST_INFO_FILE ?= results/latest_run_info.txt
ARCHIVE_ROOT ?= $(PLOT_ARCHIVE_ROOT)
ARCHIVE_DATA ?= 0
FORMAL_RUN ?= 0

.PHONY: help run smoke smoke-maxcut smoke-maxcoverage full full-maxcut full-maxcoverage maxcut maxcoverage show list-plots clean

help:
	@echo "make"
	@echo "  Run the full experiment once, delete intermediate CSV data, and keep this run's plots."
	@echo "  Plot filenames and titles get an auto-incremented version number."
	@echo
	@echo "Useful overrides:"
	@echo "  make LABEL=repair"
	@echo "  make FAMILY=maxcut"
	@echo "  make RUNS=3 BUDGET=1000"
	@echo "  make maxcoverage"
	@echo "  make full-maxcoverage FULL_BUDGET=200 FULL_RUNS=1"
	@echo
	@echo "Other targets:"
	@echo "  make smoke"
	@echo "  make smoke-maxcut"
	@echo "  make smoke-maxcoverage"
	@echo "  make full"
	@echo "  make full-maxcut"
	@echo "  make full-maxcoverage"
	@echo "  make maxcut"
	@echo "  make maxcoverage"
	@echo "  make show"
	@echo "  make list-plots"
	@echo "  make clean"

run:
	@set -euo pipefail
	run_id="$$(date +%Y%m%d_%H%M%S)"
	tmp_data_dir="$(TMP_DATA_DIR)/$(LABEL)_$${run_id}"
	version_file="$(VERSION_STATE_DIR)/$(VERSION_KEY).txt"
	current_info_file="$${tmp_data_dir}/run_info.txt"
	mkdir -p results "$(ARCHIVE_ROOT)" "$(LATEST_PLOT_DIR)" "$(TMP_DATA_DIR)" "$(VERSION_STATE_DIR)"
	rm -rf "$${tmp_data_dir}" "$(LATEST_PLOT_DIR)"
	mkdir -p "$${tmp_data_dir}" "$(LATEST_PLOT_DIR)"
	version=1
	if [[ -f "$${version_file}" ]]; then
		last_version="$$(tr -d '[:space:]' < "$${version_file}")"
		if [[ "$${last_version}" =~ ^[0-9]+$$ ]]; then
			version="$$(($${last_version} + 1))"
		fi
	fi
	archive_dir="$(ARCHIVE_ROOT)/$(LABEL)_v$${version}_$${run_id}"
	run_summary_file="$${archive_dir}/run_summary.md"
	mkdir -p "$${archive_dir}"
	echo "Running experiment version v$${version}..."

	batch_cmd=( env PYTHONUNBUFFERED="$(PYTHON_UNBUFFERED)" "$(PYTHON)" batch_run.py \
		--family "$(FAMILY)" \
		--budget "$(BUDGET)" \
		--runs "$(RUNS)" \
		--seed "$(SEED)" \
		--pop-size "$(POP_SIZE)" \
		--crossover-rate "$(CROSSOVER_RATE)" \
		--tournament-size "$(TOURNAMENT_SIZE)" \
		--elite-size "$(ELITE_SIZE)" \
		--output-dir "$${tmp_data_dir}" )

	if [[ -n "$(MUTATION_RATE)" ]]; then
		batch_cmd+=( --mutation-rate "$(MUTATION_RATE)" )
	fi

	if [[ -n "$(ONE_PROB)" ]]; then
		batch_cmd+=( --one-prob "$(ONE_PROB)" )
	fi

	{
		printf 'command='
		printf '%q ' "$${batch_cmd[@]}"
		printf '\n'
		"$${batch_cmd[@]}"

		env PYTHONUNBUFFERED="$(PYTHON_UNBUFFERED)" "$(PYTHON)" plot_curves.py \
			--input-csv "$${tmp_data_dir}/all_curves.csv" \
			--output-dir "$${archive_dir}" \
			--version "$${version}" \
			--formats $(FORMATS) \
			--x-axis "$(X_AXIS)" \
			--mode family \
			--metric "$(METRIC)"
	} | tee "$(LATEST_LOG_FILE)"

	find "$${archive_dir}" -maxdepth 1 -type f \( -name '*.png' -o -name '*.svg' -o -name '*.pdf' \) -exec cp {} "$(LATEST_PLOT_DIR)/" \;
	printf '%s\n' "$${version}" > "$${version_file}"

	{
		echo "label=$(LABEL)"
		echo "version=$${version}"
		echo "run_id=$${run_id}"
		echo "family=$(FAMILY)"
		echo "budget=$(BUDGET)"
		echo "runs=$(RUNS)"
		echo "seed=$(SEED)"
		echo "pop_size=$(POP_SIZE)"
		echo "crossover_rate=$(CROSSOVER_RATE)"
		echo "mutation_rate=$(if $(strip $(MUTATION_RATE)),$(MUTATION_RATE),default_1_over_n)"
		echo "one_prob=$(if $(strip $(ONE_PROB)),$(ONE_PROB),default)"
		echo "tournament_size=$(TOURNAMENT_SIZE)"
		echo "elite_size=$(ELITE_SIZE)"
		echo "x_axis=$(X_AXIS)"
		echo "metric=$(METRIC)"
		echo "formats=$(FORMATS)"
		echo "latest_plot_dir=$(LATEST_PLOT_DIR)"
		echo "archive_root=$(ARCHIVE_ROOT)"
		echo "archive_dir=$${archive_dir}"
		echo "formal_run=$(FORMAL_RUN)"
		echo "formal_track_key=$(FORMAL_TRACK_KEY)"
	} > "$${current_info_file}"

	cp "$${current_info_file}" "$(LATEST_INFO_FILE)"

	if [[ "$(ARCHIVE_DATA)" == "1" ]]; then
		mkdir -p "$${archive_dir}/batch_outputs"
		cp -r "$${tmp_data_dir}"/. "$${archive_dir}/batch_outputs/"
		cp "$(LATEST_LOG_FILE)" "$${archive_dir}/run.log"
	fi

	if [[ "$(FORMAL_RUN)" == "1" ]]; then
		formal_track_dir="$(FORMAL_STATE_ROOT)/$(FORMAL_TRACK_KEY)"
		previous_info_file="$${formal_track_dir}/latest_run_info.txt"
		mkdir -p "$${formal_track_dir}"
		env PYTHONUNBUFFERED="$(PYTHON_UNBUFFERED)" "$(PYTHON)" record_formal_run.py \
			--current-info "$${current_info_file}" \
			--previous-info "$${previous_info_file}" \
			--output "$${run_summary_file}" \
			--track-key "$(FORMAL_TRACK_KEY)"
		cp "$${current_info_file}" "$${formal_track_dir}/latest_run_info.txt"
		cp "$${run_summary_file}" "$${formal_track_dir}/latest_run_summary.md"
	fi

	rm -rf "$${tmp_data_dir}"

	echo
	echo "Latest plots:"
	find "$(LATEST_PLOT_DIR)" -maxdepth 1 -type f | sort
	echo
	echo "Archived plots:"
	find "$${archive_dir}" -maxdepth 1 -type f \( -name '*.png' -o -name '*.svg' -o -name '*.pdf' -o -name '*.md' \) | sort

smoke:
	@$(MAKE) run LABEL=smoke FAMILY=all BUDGET=$(SMOKE_BUDGET) RUNS=$(SMOKE_RUNS)

smoke-maxcut:
	@$(MAKE) run LABEL=smoke-maxcut FAMILY=maxcut BUDGET=$(SMOKE_BUDGET) RUNS=$(SMOKE_RUNS)

smoke-maxcoverage:
	@$(MAKE) run LABEL=smoke-maxcoverage FAMILY=maxcoverage BUDGET=$(SMOKE_BUDGET) RUNS=$(SMOKE_RUNS)

full:
	@$(MAKE) run LABEL=full FAMILY=all BUDGET=$(FULL_BUDGET) RUNS=$(FULL_RUNS) ARCHIVE_ROOT=$(FINAL_PLOT_ROOT) VERSION_STATE_DIR=$(FORMAL_STATE_ROOT)/versions FORMAL_STATE_ROOT=$(FORMAL_STATE_ROOT) FORMAL_TRACK_KEY=full FORMAL_RUN=1 ARCHIVE_DATA=0

full-maxcut:
	@$(MAKE) run LABEL=full-maxcut FAMILY=maxcut BUDGET=$(FULL_BUDGET) RUNS=$(FULL_RUNS) ARCHIVE_ROOT=$(FINAL_PLOT_ROOT) VERSION_STATE_DIR=$(FORMAL_STATE_ROOT)/versions FORMAL_STATE_ROOT=$(FORMAL_STATE_ROOT) FORMAL_TRACK_KEY=full-maxcut FORMAL_RUN=1 ARCHIVE_DATA=0

full-maxcoverage:
	@$(MAKE) run LABEL=full-maxcoverage FAMILY=maxcoverage BUDGET=$(FULL_BUDGET) RUNS=$(FULL_RUNS) ARCHIVE_ROOT=$(FINAL_PLOT_ROOT) VERSION_STATE_DIR=$(FORMAL_STATE_ROOT)/versions FORMAL_STATE_ROOT=$(FORMAL_STATE_ROOT) FORMAL_TRACK_KEY=full-maxcoverage FORMAL_RUN=1 ARCHIVE_DATA=0

maxcut:
	@$(MAKE) run FAMILY=maxcut LABEL=maxcut

maxcoverage:
	@$(MAKE) run FAMILY=maxcoverage LABEL=maxcoverage

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
	@rm -rf "$(TMP_DATA_DIR)" "$(LATEST_PLOT_DIR)" "$(PLOT_ARCHIVE_ROOT)" "$(LATEST_LOG_FILE)" "$(LATEST_INFO_FILE)" "results/.version_state" "$(FORMAL_STATE_ROOT)"
	@echo "Cleaned generated results."
