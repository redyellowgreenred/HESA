# EA Code Framework

## 1. Project Goal

This project implements a binary evolutionary algorithm (EA) baseline for IOH submodular optimization problems.

Supported problem families:

- MaxCut: problem IDs `2000-2004`
- MaxCoverage: problem IDs `2100-2127`

Core idea:

- use a unified binary EA framework
- represent a solution as a 0-1 vector
- run under a fixed fitness evaluation budget
- repeat multiple runs and aggregate results


## 2. Top-Level File Structure

### Main execution

- `main.py`
  - single-instance experiment entry
  - orchestrates one complete EA run through the six phases
  - supports repeated runs on one problem instance

### Phase modules

- `ea_phase1_setup.py`
  - problem loading
  - random generator creation
  - default parameter setup
  - parameter normalization

- `ea_phase2_population.py`
  - random binary solution sampling
  - initial population creation
  - initial best-solution recording

- `ea_phase3_selection.py`
  - parent selection
  - current implementation: tournament selection

- `ea_phase4_variation.py`
  - variation operators
  - current implementation:
    - uniform crossover
    - bitwise mutation

- `ea_phase5_survival.py`
  - survivor selection
  - current implementation: elitism

- `ea_phase6_reporting.py`
  - stopping check
  - history row creation
  - CSV writing
  - averaging histories across runs
  - final result packaging

### Experiment utilities

- `batch_run.py`
  - batch evaluation over many instances
  - writes per-run, per-instance, and per-family CSV summaries

- `plot_curves.py`
  - plots averaged fitness curves from CSV outputs

- `Makefile`
  - simplified experiment entry
  - generates plots and handles temporary output


## 3. Main Data Objects

### `EASetup`

Defined in `ea_phase1_setup.py`.

Purpose:

- store all normalized configuration and run context for one EA run

Fields:

- `problem`
- `rng`
- `dimension`
- `one_prob`
- `mutation_rate`
- `pop_size`
- `tournament_size`
- `elite_size`


### `PopulationState`

Defined in `ea_phase2_population.py`.

Purpose:

- store the current population and current best solution

Fields:

- `population`
- `fitnesses`
- `best_x`
- `best_y`


## 4. Six-Phase EA Design

### Phase 1: Setup

File:

- `ea_phase1_setup.py`

Main responsibilities:

- load IOH problem instance
- create RNG with seed
- read dimension `n`
- choose default initialization density
- choose default mutation rate
- make parameters legal

Important functions:

- `load_problem(problem_id)`
- `default_one_prob(problem_id)`
- `create_ea_setup(...)`


### Phase 2: Population Initialization

File:

- `ea_phase2_population.py`

Main responsibilities:

- sample random binary individuals
- build initial population
- evaluate the initial population
- record the initial best individual

Important functions:

- `sample_random_solution(...)`
- `initialize_population(...)`


### Phase 3: Parent Selection

File:

- `ea_phase3_selection.py`

Main responsibilities:

- select one parent from the current population

Current strategy:

- tournament selection

Important function:

- `tournament_select(...)`


### Phase 4: Variation

File:

- `ea_phase4_variation.py`

Main responsibilities:

- recombine parent solutions
- perturb child solutions

Current operators:

- `uniform_crossover(...)`
- `bitwise_mutation(...)`


### Phase 5: Survivor Selection

File:

- `ea_phase5_survival.py`

Main responsibilities:

- directly preserve the best current individuals for the next generation

Current strategy:

- elitism

Important function:

- `select_elite_survivors(...)`


### Phase 6: Termination and Reporting

File:

- `ea_phase6_reporting.py`

Main responsibilities:

- decide whether the EA should continue
- record generation statistics
- aggregate histories across runs
- export CSV outputs
- package final run results

Important functions:

- `should_continue(...)`
- `make_history_row(...)`
- `write_csv_rows(...)`
- `average_histories(...)`
- `build_run_result(...)`


## 5. Single EA Run: Execution Flow

The core execution function is:

- `run_binary_ea(...)` in `main.py`

Its workflow is:

1. Phase 1: call `create_ea_setup(...)`
2. Phase 2: call `initialize_population(...)`
3. record generation 0 into `history`
4. while evaluation budget is not exhausted:
   - Phase 5: preserve elites
   - repeatedly fill the next generation:
     - Phase 3: select parent A
     - Phase 3: select parent B
     - Phase 4: crossover with probability `crossover_rate`
     - Phase 4: mutate each child
     - evaluate each child
     - update global best if necessary
   - replace current population with the next population
   - increase generation counter
   - Phase 6: append one history record
5. Phase 6: package and return final results


## 6. Control Layer in `main.py`

`main.py` has two layers:

### `run_binary_ea(...)`

Purpose:

- execute one full EA run on one problem instance

Output:

- one result dictionary containing:
  - problem metadata
  - best solution
  - best fitness
  - final mean fitness
  - evaluation count
  - generation count
  - parameter settings
  - full history

### `main()`

Purpose:

- parse CLI arguments
- run the EA multiple times on one problem instance
- collect all run results
- optionally export run summary CSV
- optionally export averaged curve CSV
- print average final results


## 7. Problem-Specific Customization

Current design uses one unified EA framework for both MaxCut and MaxCoverage.

At the moment, the only explicit difference is in Phase 1:

- MaxCoverage uses a sparser default initialization probability
- MaxCut uses a denser default initialization probability

This framework can be extended in two ways:

### Parameter-level customization

Examples:

- different `one_prob`
- different `mutation_rate`
- different `pop_size`

### Phase-level customization

Examples:

- different initialization logic in Phase 2
- different variation operators in Phase 4
- different survivor rules in Phase 5

This means the two problem families do not need fully separate algorithms.
They can share the same global EA pipeline while using different logic inside selected phases.


## 8. Output Data

### Per-run outputs

Typical information:

- `best_fitness`
- `final_mean_fitness`
- `evaluations`
- `generations`

### History outputs

Typical information:

- `generation`
- `evaluations`
- `best_fitness`
- `mean_fitness`

### Aggregated curve outputs

Typical information:

- `mean_best_fitness`
- `mean_population_fitness`


## 9. Current Algorithm Summary

Current MVP algorithm:

- binary representation
- random initialization
- tournament parent selection
- uniform crossover
- bitwise mutation
- elitist survivor selection
- fixed evaluation budget termination
- repeated independent runs for averaging

This is a standard binary EA baseline suitable as the starting point for later problem-specific improvements.
