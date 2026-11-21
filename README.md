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
- The selector reconstructs the changed Python source in memory and verifies the diff context. It compares ASTs while preserving declarations, annotations, decorators, function docstrings, and generator status. For body-only changes it selects tests observed in the affected function bodies, source readers, opaque subprocess callers, and tests absent from the profile. When old statements are replaced line for line without changing local bindings, a narrower statement trace can be used; uncertain edits keep the body selection.
- On the main and file fallback branches, edits confined to comments or blank lines must preserve the Python AST including type comments. Encoding and shebang changes take the broader selection. Source-reading and subprocess tests still run.
- Edits to existing fixtures use the tests observed opening the file on the pristine checkout. Reads in shared class or module setup also select other tests in the same scope. Collection-time reads and structural file changes use the full suite.
- Other structural changes, unrecognized paths, compilation failures, and function bodies with absent or collection-time coverage take the all-tests fallback. The fallback uses longest-processing-time-first packing, testing the actual score for each feasible worker count from one to eight with integer millisecond arithmetic.
- A separate clean-suite profile observes constructors of SQLGlot dialects, tokenizer/parser/generator classes, and expression nodes, including their base classes. An existing class assignment may use that map only if the old and new values are literal data, every other AST node is unchanged, and a pristine source scan finds no import-time reader of its name. The narrow exception is a fixed-key boolean `Expr.arg_types` schema: the pinned class hook derives `required_args` from it. Its class users, references, reflective tests, tests missing from the class profile, source readers, and subprocess users are all selected. An early import hook records the receiver classes validated by `Expression.error_messages` before or between tests. Classes constructed outside test contexts and direct import-time copies of a class schema retain the broad fallback. A missing parent or import-constructor map disables class narrowing.
- The clean class profile separately records classes constructed outside test contexts. A second profile records dialect, tokenizer, parser, generator, and expression constructors inside spawned process-pool tasks and merges those users into every class selection. A sole lambda-body edit within a direct `Parser.FUNCTIONS` subclass dispatch table selects that parser's class users and generic table readers after proving no subclass hook or direct table alias is present. A same-key, value-only change to a nested dialect Tokenizer's `NUMERIC_ESCAPES` selects its tokenizer constructor users in the parent suite and spawned process pools. The pinned metaclass and generator inspect keys or truthiness only, so dialect construction alone does not consume changed tuple values. Tests with a direct source mention of `NUMERIC_ESCAPES`, reflective tests, opaque subprocess callers, and unprofiled tests are also included. Changed keys, other class shapes, unexpected read sites, absent maps, and multi-file changes retain broad selection. A missing or inconsistent child map makes structural edits select all tests.
- A single changed literal argument in an existing `SHOW_PARSERS` factory entry can use class consumers when the pinned factory only returns a closure and the class's derived trie reads dictionary keys. The selector verifies the factory, parser inheritance and constructor hooks, import-time aliases, and every other module AST node. Unsupported factories and multi-file patches use the existing fallback.

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
SKIP_INTEGRATION=0 PYTHON_CPU_COUNT=2 python tools/profile_classes.py \
  "$SQLGLOT" "$KIT/sample/tests.json" class-uses.json.gz \
  --import-output class-import-reads.json \
  --constructor-import-output class-import-constructors.json
SKIP_INTEGRATION=0 PYTHON_CPU_COUNT=2 python tools/profile_pool_classes.py \
  "$SQLGLOT" "$KIT/sample/tests.json" pool-classes.json.gz
```

The compressed map includes pristine source text for diff verification. The pool profile rejects a clean run unless every submitted task has a matching child record. The selector checks map consistency and uses the full suite for structural edits if it is missing. SQLGlot's [MIT license](LICENSE.sqlglot) ships with the map. Raw profiles and regression labels are outside the Docker build context. The image build uses the organizer's digest-pinned Python 3.13 base and performs no package installation.

## Independent regression benchmark

```sh
python tools/regression.py "$SQLGLOT" "$KIT/sample/tests.json" /tmp/blast-regression \
  --seed 45171 --jobs 3 --cases comment syntax rename lazy-import fixture multi-file \
  subsecond_precision format_time simplify execute body-subsecond_precision body-execute \
  body-parse body-eliminate_distinct_on
python tools/measure.py selector.py "$KIT/score.py" /tmp/blast-regression/data \
  /tmp/blast-regression/answers.json /tmp/blast-regression-output.jsonl
```

The regression generator runs the pinned suite on isolated copies, verifies a clean run, and logs pytest failures, subtest failures, and test collection errors. It passes only patch inputs and the test manifest to the selector. Each case is generated independently from the same clean checkout. See [EXPERIMENTS.md](EXPERIMENTS.md) for observed scores and platform differences.
