# RWX Blast Radius entry

The selector assigns SQLGlot tests to up to eight workers. It takes independent unified diffs and a numbered test manifest from `/data`, and emits one JSON line for each patch. The Docker image contains a Python standard-library selector and a compressed map of the clean SQLGlot checkout at `eb11aec4be8cb2122afe713a4816662c3f0fb2fa`.

## Build and score

Download the [official sample kit](https://www.joinbuilders.org/buildathon/tracks/blast-radius/files/blast-radius-sample.tar.gz) into its own directory. From this repository, with `KIT` set to its absolute path:

```sh
python3 tools/check_docker_context.py
docker build --platform linux/amd64 -t blast-radius-entry .
docker run --rm --platform linux/amd64 --network none --cpus 2 \
  --memory 4096m --memory-swap 4096m --pids-limit 256 --read-only \
  --tmpfs /tmp:rw,size=64m,mode=1777 --cap-drop ALL \
  --security-opt no-new-privileges --user 65534:65534 --env HOME=/tmp \
  --volume "$KIT/sample/commits:/data/commits:ro" \
  --volume "$KIT/sample/tests.json:/data/tests.json:ro" \
  blast-radius-entry > output.jsonl
python3 "$KIT/score.py" "$KIT/sample" "$KIT/sample/answers.json" output.jsonl
```

For a host run, use `python3 selector.py --data "$KIT/sample"`. The official scorer calculates simulated seconds, including 300 seconds per missed patch. The contest adds container CPU time.

## How selection works

- The map combines coverage from the clean suite with coverage collected inside optimizer and executor worker processes. Each submitted worker task carries the current pytest node ID. Tests that launch other children are included conservatively.
- The selector reconstructs the changed Python source in memory and verifies the diff context. It compares ASTs while preserving declarations, annotations, decorators, function docstrings, and generator status. For body-only changes it selects tests observed in the affected function bodies, source readers, opaque subprocess callers, and tests absent from the profile. When old statements are replaced line for line without changing local bindings, a narrower statement trace can be used. A one-line `if` condition replacement qualifies only when its branches are AST-identical, the old header was observed, and the condition contains no nested scope or assignment expression; uncertain edits keep the body selection.
- On the main and file fallback branches, edits confined to comments or blank lines must preserve the Python AST including type comments. Encoding and shebang changes take the broader selection. A complete clean-suite source-read audit identifies tests that explicitly read each source file; a single-file comment edit selects those readers. Missing or mismatched audit data keeps the broader source-reader and subprocess selection.
- Edits to existing fixtures use the tests observed opening the file on the pristine checkout. Reads in shared class or module setup also select other tests in the same scope. Collection-time reads and structural file changes use the full suite.
- Other structural changes, unrecognized paths, compilation failures, and function bodies with absent or collection-time coverage take the all-tests fallback. The fallback uses longest-processing-time-first packing, testing the actual score for each feasible worker count from one to eight with integer millisecond arithmetic.
- A separate clean-suite profile observes constructors of SQLGlot dialects, tokenizer/parser/generator classes, and expression nodes, including their base classes. An existing class assignment may use that map only if the old and new values are literal data, every other AST node is unchanged, and a pristine source scan finds no import-time reader of its name. The narrow exception is a fixed-key boolean `Expr.arg_types` schema: the pinned class hook derives `required_args` from it. Its class users, references, reflective tests, tests missing from the class profile, source readers, and subprocess users are all selected. An early import hook records the receiver classes validated by `Expression.error_messages` before or between tests. Classes constructed outside test contexts and direct import-time copies of a class schema retain the broad fallback. A missing parent or import-constructor map disables class narrowing.
- The clean class profile separately records classes constructed outside test contexts. A second profile records dialect, tokenizer, parser, generator, and expression constructors inside spawned process-pool tasks and merges those users into every class selection. A sole lambda-body edit within a direct `Parser.FUNCTIONS` subclass dispatch table selects that parser's class users and generic table readers after proving no subclass hook or direct table alias is present. For a same-key, value-only change to a nested dialect Tokenizer's `NUMERIC_ESCAPES`, a third clean profile records which escape keys `TokenizerCore` actually consumes in the parent suite and spawned process pools. The pinned metaclass and generator inspect keys or truthiness only; the core's other dictionary read checks nonemptiness. Tests with direct source mentions, reflective tests, opaque subprocess callers, and unprofiled tests remain selected. A missing or inconsistent key profile uses the broader tokenizer constructor map. Changed keys, other class shapes, unexpected read sites, and multi-file changes retain broad selection. A missing or inconsistent child constructor map makes structural edits select all tests.
- A direct Dialect subclass's immutable scalar class value can use actual clean attribute readers. The profile wraps the Dialect instance and metaclass accessors in the test process and spawned workers while returning the original value. Static read-site contexts, reflective tests, source readers, subprocess callers, and tests absent from class profiling remain included. Import-time or setup/teardown reads, constructor snapshots, direct persistent writes, cache decorators, unproved class shapes, or a missing profile use the broader class-constructor selection.
- Class field reader lookup uses a compressed, inverted index of the same pinned source references and clean-suite coverage contexts. A missing, stale, or malformed index falls back to the original source scan.
- A single changed literal argument in an existing `SHOW_PARSERS` factory entry can use class consumers when the pinned factory only returns a closure and the class's derived trie reads dictionary keys. The selector verifies the factory, parser inheritance and constructor hooks, import-time aliases, and every other module AST node. For this proved value-only edit, a foreign parser class's bare-name trie construction can be excluded only when its table is an independently assigned literal-key dictionary and the pinned source proves the local `new_trie` binding and exact key-only generator. Runtime readers, direct test references, and unproved sites remain selected. Unsupported factories and multi-file patches use the existing fallback.
- For a sole lambda-body change in a direct Parser subclass's `FUNCTIONS` table, a receiver-aware read scan keeps observed executions and dynamic table readers. An additional clean call trace can narrow this to tests that invoked the exact original lambda, plus class users, explicit table/code-object observers, reflection, source readers, and subprocess gaps. The old and new bodies must have the same complete AST except for same-typed numeric or boolean literal values; new calls, attribute changes, writes, and control-flow changes select all tests, including when the call map is missing. The lambda line must remain fixed. Import and setup calls select all tests, while missing call data for an otherwise safe literal edit uses the broader reader selection. The trace includes every spawned task and starts before worker unpickling. Both trace maps are bound to the compressed impact map by SHA-256. An annotated table declaration qualifies only under postponed annotations, with its annotation and all other module AST nodes unchanged.

## Rebuild the maps

Use Python 3.13, the organizer's [pinned dependencies](requirements.lock), and `coverage==7.17.4` in an isolated environment. Use a pristine checkout at the SQLGlot commit above. Set `SQLGLOT` to the absolute checkout path and put the environment's Python first on the system path so Python children use the same dependencies.

```sh
SKIP_INTEGRATION=0 python tools/profile_suite.py "$SQLGLOT" /tmp/parent.json.gz
SKIP_INTEGRATION=0 python tools/profile_suite.py "$SQLGLOT" /tmp/pools.json.gz \
  --with-pools --tests tests/test_optimizer.py tests/test_executor.py
SKIP_INTEGRATION=0 PYTHON_CPU_COUNT=2 python tools/profile_fixtures.py "$SQLGLOT" \
  fixture-reads.json --shared fixture-shared.json
python tools/build_map.py "$SQLGLOT" impact.json.gz \
  --profile /tmp/parent.json.gz --profile /tmp/pools.json.gz
python tools/build_reference_index.py
COMMENT_PARENT_CACHE="$(mktemp -d)"
COMMENT_CHILD_CACHE="$(mktemp -d)"
SKIP_INTEGRATION=0 PYTHON_CPU_COUNT=2 PYTHONPYCACHEPREFIX="$COMMENT_PARENT_CACHE" \
  python tools/profile_comment_reads.py \
  "$SQLGLOT" "$KIT/sample/tests.json" /tmp/comment-source-profile.json
SKIP_INTEGRATION=0 PYTHON_CPU_COUNT=2 PYTHONPYCACHEPREFIX="$COMMENT_CHILD_CACHE" \
  python tools/profile_comment_pool.py \
  "$SQLGLOT" "$KIT/sample/tests.json" /tmp/comment-pool-profile.json
python tools/build_comment_reads.py /tmp/comment-source-profile.json \
  "$KIT/sample/tests.json" impact.json.gz comment-source-reads.json \
  --pool-profile /tmp/comment-pool-profile.json --pool-map pool-classes.json.gz \
  --checkout "$SQLGLOT"
SKIP_INTEGRATION=0 PYTHON_CPU_COUNT=2 python tools/profile_classes.py \
  "$SQLGLOT" "$KIT/sample/tests.json" class-uses.json.gz \
  --import-output class-import-reads.json \
  --constructor-import-output class-import-constructors.json
SKIP_INTEGRATION=0 PYTHON_CPU_COUNT=2 python tools/profile_pool_classes.py \
  "$SQLGLOT" "$KIT/sample/tests.json" pool-classes.json.gz
SKIP_INTEGRATION=0 PYTHON_CPU_COUNT=2 python tools/profile_numeric_keys.py \
  "$SQLGLOT" "$KIT/sample/tests.json" numeric-key-uses.json.gz \
  --impact-map impact.json.gz
SKIP_INTEGRATION=0 PYTHON_CPU_COUNT=2 python tools/profile_scalar_reads.py \
  "$SQLGLOT" "$KIT/sample/tests.json" scalar-reads.json.gz \
  --impact-map impact.json.gz
python tools/profile_lambda_imports.py "$SQLGLOT" /tmp/parser-lambda-import-sweep.json \
  --impact-map impact.json.gz --sweep-imports
SKIP_INTEGRATION=0 PYTHON_CPU_COUNT=2 python tools/profile_lambda_imports.py \
  "$SQLGLOT" parser-lambda-import-calls.json --impact-map impact.json.gz \
  --merge /tmp/parser-lambda-import-sweep.json
SKIP_INTEGRATION=0 PYTHON_CPU_COUNT=2 python tools/profile_lambda_key_calls.py \
  "$SQLGLOT" "$KIT/sample/tests.json" parser-lambda-key-calls.json.gz \
  --impact-map impact.json.gz
python tools/build_parser_lambda_reader_index.py "$KIT/sample/tests.json" \
  parser-lambda-reader-index.json.gz --map impact.json.gz
```

The compressed map includes pristine source text for diff verification. Both pool profiles reject a clean run unless every submitted task has a matching child record. The selector checks map consistency and uses the full suite for structural edits if the constructor map is missing. SQLGlot's [MIT license](LICENSE.sqlglot) ships with the map. Raw profiles and regression labels are outside the Docker build context. The image build uses the organizer's digest-pinned Python 3.13 base and performs no package installation.

## Independent regression benchmark

```sh
python tools/regression.py "$SQLGLOT" "$KIT/sample/tests.json" /tmp/blast-regression \
  --seed 45171 --jobs 3 --cases comment syntax rename lazy-import fixture multi-file \
  subsecond_precision format_time simplify execute body-subsecond_precision body-execute \
  body-parse body-eliminate_distinct_on
python tools/measure.py selector.py "$KIT/score.py" /tmp/blast-regression/data \
  /tmp/blast-regression/answers.json /tmp/blast-regression-output.jsonl
python tools/if_regression.py "$SQLGLOT" "$KIT/sample/tests.json" /tmp/blast-if-regression
python tools/measure.py selector.py "$KIT/score.py" /tmp/blast-if-regression/data \
  /tmp/blast-if-regression/answers.json /tmp/blast-if-output.jsonl
```

The regression generator runs the pinned suite on isolated copies, verifies a clean run, and logs pytest failures, subtest failures, and test collection errors. It passes only patch inputs and the test manifest to the selector. Each case is generated independently from the same clean checkout. See [EXPERIMENTS.md](EXPERIMENTS.md) for observed scores and platform differences.
