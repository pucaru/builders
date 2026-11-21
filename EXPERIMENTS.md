# Experiment log

## Integrated child-safe release candidate

Local integration through `c493287` combines the closure factory rule, tokenizer value proof, statement relocation guard, and a second pristine profile of 2,183 process-pool tasks. The official scorer reports **248.610 simulated seconds, zero misses** on all 30 samples; a separate host run used 3.697 CPU seconds. The prior verified GitHub tree scored 267.140/0. All 10 Docker `COPY` inputs passed the build-context check. The exact payload ran read-only as UID/GID 65534 from the digest-verified base filesystem with two CPUs, 4 GiB address-space limit, 64 MiB `/tmp`, and blocked sockets; its output also scored 248.610/0. This is a Bubblewrap substitute, not a Docker build, and its wrapper CPU excludes namespaced child CPU.

The new full-suite `Exists.arg_types` mutation caused 35 test failures, including three in process workers. The parent-only class map missed those three and incurred one 300-second penalty (325.454/1). The integrated map selected all 35 (25.729/0). Fresh numeric value mutations, including two actual BigQuery failures, scored 33.248/0 on the three-case corpus. Three independent factory mutations included two actual SingleStore failures and scored 50.908/0 plus 25.454/0 on their separate corpora. The statement relocation mutation scored 4.738/0 after the guard, versus 302.495/1 before it. The earlier independent final, extended, fixture, schema, class, lambda, dialect, and statement corpora all retained zero misses. Labels are outside the selector and Docker image.

An isolated reader-index experiment at `34d6d68` scored 265.058/0 on the 30 samples from its 267.140/0 base. A draft omitted an observed lambda caller; the corrected index retains unresolved alias and cache uncertainty for about two seconds of sample savings. It was not promoted. The 255.777/0 factory-only commit `b084ca7` and 267.140/0 prior release remain available as fallbacks.

A further fail-closed guard rejects class-field narrowing for any receiver constructed outside test contexts, including cached expression templates. It also requires the parent class-use map even when the pool map is present. A synthetic `Identifier.arg_types` change and a missing-parent-map check both select all 1,620 tests. The official sample remains 248.610/0 and the independently labeled pool-only `Exists` mutation remains 25.729/0. No maps or labels were changed by this guard.

Class-field fast paths now require a single-file patch. Factory, lambda, and numeric value rules already had that gate; the generic literal rule gained it after an interaction audit. The three public multi-file patches do not take the literal rule, so the official score stays 248.610/0. The independent seeded multi-file case remains on its broad path.

An invalid hunk-context or compilation failure now directly selects all tests instead of allowing an uninitialized reconstructed source to reach class analysis. A synthetic class-field plus second-file patch also selects all 1,620 tests. The official sample plan is unchanged.

## Statement relocation safety

The statement-level fast path now accepts only an adjacent, single-line, same-kind replacement with unchanged name loads and bindings. Insertions, deletions, relocations, changed source headers, and mixed comment/code changes fall back to broader selection. A new full-suite label for an early return inserted in `Generator.property_sql` found 41 failing tests. The previous equal-line-count rule selected six tests, omitted 40 failures, and scored 302.495 seconds including one 300-second miss. The guarded selector scores 4.738 seconds with zero misses on that patch. The official 30-sample result remains 267.140 seconds with zero misses; the existing four fresh statement labels remain 37.740/0. Synthetic header, comment, and relocation fallback checks pass. The label and its test output are outside the Docker payload.

## Integrated class and shared setup selector

The independent class-use map and schema classifier from `class-coverage` were combined with the previously verified shared-fixture attribution and statement selection. The exact combined Dockerfile payload was run in the digest-verified read-only Bubblewrap substitute as UID/GID 65534 with the same two-core, 4 GiB, 64 MiB temporary filesystem and no-network limits used for the previous release. This was not a Docker build. The organizer's scorer reported 296.085 simulated seconds and zero misses on the 30 samples. A separate host run took 2.559 CPU seconds; the local scorer excludes CPU. The previous local release was 322.297 simulated seconds, zero misses.

| Labeled corpus | Integrated simulated s | Misses |
| --- | ---: | ---: |
| Official 30 samples | 296.085 | 0 |
| Fresh statement and shared TPC-H fixture edits | 37.740 | 0 |
| Fresh class mutations | 48.309 | 0 |
| Fresh expression schemas (110 failures in CREATE edit) | 42.300 | 0 |
| Independent final cases | 327.923 | 0 |
| Independent extended cases | 375.393 | 0 |
| Independent fixture cases | 4.832 | 0 |
| Independent dialect cases | 48.309 | 0 |

The prior release costs 42.306 seconds on the independent dialect and class pairs; the additional 6.003 seconds here is a conservative widening for class-field consumers. Hidden-test coverage of dynamic class introspection is still uncertain. The independent labels, including failures, remain outside the Docker image and selector.

## Statement and shared-setup experiment

We tested statement-level impact within otherwise unchanged function bodies and attribution of fixture reads from class setup to all tests in that class. Both maps come from the pinned pristine checkout. The shared fixture map comes from a clean run with 1,620 tests passing, one skipped, and 25,440 subtests passing. It identifies 34 paths opened during `setUpClass`, including the TPC-H and TPC-DS inputs in `TestExecutor`. Normal per-method fixture reads stay with the reading test.

| Corpus | Main simulated s | Candidate simulated s | Candidate misses |
| --- | ---: | ---: | ---: |
| Official 30 samples | 323.703 | 322.297 | 0 |
| Independent final cases | 327.923 | 327.923 | 0 |
| Independent extended cases | 375.393 | 375.393 | 0 |
| Independent fixture cases | 4.832 | 4.832 | 0 |
| Independent dialect cases | 42.306 | 42.306 | 0 |

The official local scorer supplied simulated costs. Candidate host CPU was approximately 1.4 seconds for the sample batch, versus approximately 1.0 second for main, measured during separate runs on a shared host. The narrow statement rule affects two sample patches; no existing independently labeled case exercises its narrower path. Do not infer hidden-test safety from these results alone. Docker has not been available for a real image build.

Four further independent mutations were labeled by running the full pinned test suite on each modified checkout, each taking approximately 102–105 seconds. Three replace a statement in `sqlglot/time.py` while preserving its surrounding function: two produced five failing tests each and one produced 49. The fourth alters a TPC-H SQL fixture loaded in executor class setup and produced two failing tests. These labels and logs are kept outside the selector and image under `independent-statements/`.

| Branch | Four-mutation simulated s | Misses | Host CPU s |
| --- | ---: | ---: | ---: |
| Previous main, `c07b8fb` | 316.410 | 1 | 0.429 |
| Statement plus shared setup, `39ea17b` | 37.740 | 0 | 0.459 |

The old selector missed one of the two TPC-H fixture failures because the fixture is opened during `TestExecutor.setUpClass`, once for the whole class. The new clean-suite setup map attributes that read to every test in the class. The three independently labeled statement replacements incurred zero misses under the narrower rule.

The promoted local main commit `f31115b` was run from the exact Dockerfile payload using the digest-verified base filesystem in a read-only Bubblewrap sandbox as UID/GID 65534, with two CPU cores, 4 GiB address-space limit, 64 MiB `/tmp`, and networking blocked. Its output scored 322.297 simulated seconds and zero misses on the official sample. This remains a substitute check, not a successful Docker build or an official practice score; its reported wrapper CPU does not measure all namespaced process CPU.

All simulated scores use the organizer's `score.py`. Miss penalties are included. Host CPU and wall time are for one 30-patch run under Debian Python 3.13.5. They are separate from simulated seconds and vary with host load.

| Branch or experiment | Commit | Official seconds | Misses | Host wall s | Host CPU s |
| --- | --- | ---: | ---: | ---: | ---: |
| Official starter | `56c66c7` | 1,210.470 | 0 | 0.049 | 0.049 |
| All tests, variable workers | `0e410e8` | 1,104.510 | 0 | 0.032 | 0.031 |
| Static imports | `5a028e9` | 1,093.147 | 0 | 0.267 | 0.228 |
| Parent-only file coverage | `2a65865` | 1,489.792 | 3 | 0.568 | 0.564 |
| Parent-only function coverage | `51b5d85` | 1,731.713 | 4 | 0.716 | 0.680 |
| Guarded parent-only function coverage | `8839c3f` | 1,671.678 | 3 | 0.818 | 0.765 |
| Static plus parent file coverage | `9878153` | 1,093.147 | 0 | 0.415 | 0.377 |
| File coverage with child traces | `e3232d5` | 885.113 | 0 | 0.916 | 0.881 |
| Function coverage with child traces | `eac8446` | 830.596 | 0 | 1.025 | 0.981 |
| Function coverage with child traces and guarded comments | `091dfe3` | 727.627 | 0 | 0.916 | 0.897 |
| File coverage with child traces and guarded comments | `9126949` | 782.144 | 0 | 1.070 | 0.939 |

The earlier 814.322-second static run was supplied as a checkpoint. Its original source was unavailable in this workspace. The static branch above is a new implementation.

## Observations

- The all-tests scheduler reached the mathematical lower bound on every official sample. That bound is the minimum over worker counts of the larger of the longest test and the average worker load, rounded up, plus worker overhead. The schedule invariants also passed 500 seeded tests.
- An audit hook recorded the lazy dialect test launching a fresh Python process. It also missed work in persistent optimizer and executor processes. A separate clean run traced 24 pytest nodes that submitted worker tasks. Both guarded selectors recovered every official sample miss after incorporating child attribution.
- The pristine parent profiling run passed 1,620 tests and 25,440 subtests, with one skipped test. The targeted optimizer and executor profiling run passed 227 tests and 6,508 subtests.
- An early regression labelling attempt set a 25-second per-test timeout. Two expensive tests timed out on the clean checkout, so the run was discarded. The replacement clean run passed all 1,620 numbered tests with the per-test timeout raised to 180 seconds. That timeout is a local labelling setting and may differ from the organizer's environment.
- Parent-only coverage was rejected. Its narrower plans had attractive costs before the 300-second penalties. The all-tests variable worker branch remains the fallback with the simplest coverage guarantee.

## Input provenance

- SQLGlot revision `eb11aec4be8cb2122afe713a4816662c3f0fb2fa`. Checkout archive SHA-256 `93b2445f15f395b81c20556777ece19a6c7507df950f13fa9fac4a3be739af0d`.
- Official sample kit SHA-256 `81efabbc69c3c4367d928f2dba0f33ce9dccccbd080b54721b2636e5d8afab9d`.
- Organizer's base image pinned by digest in the Dockerfile. Its verified linux/amd64 manifest digest is `sha256:48d884813cf44e927cf64c5529dd630dd3b18338c6dc727991eef9b71e934a20`.

## Independent regression pass

The independent pass used seed 45171, up to three simultaneous checkouts, and two CPUs exposed to each test suite's worker-pool defaults. The clean run passed 1,620 tests and 25,440 subtests with one skipped test. Ten cases produced 4,962 failing-test occurrences, counting the same test separately on each patch. Cases covered a harmless Python comment, a syntax error, a file rename, a fixture edit, lazy dialect loading in a fresh process, a seeded multi-file change, and execution and optimizer regressions.

Each cost below uses the official scorer with independent labels. The CPU and wall times were measured on the local host for the selector, separate from the time needed to label each patch.

| Branch | Independent seconds | Misses | Host wall s | Host CPU s |
| --- | ---: | ---: | ---: | ---: |
| Official starter | 403.490 | 0 | — | — |
| All tests, variable workers | 368.170 | 0 | 0.032 | 0.029 |
| Static imports | 356.807 | 0 | 0.115 | 0.081 |
| Parent-only file coverage | 1,747.030 | 5 | 0.365 | 0.333 |
| Parent-only function coverage | 1,742.135 | 5 | 1.485 | 1.444 |
| Guarded parent-only function coverage | 843.705 | 2 | 0.917 | 0.881 |
| Static plus parent file coverage | 356.807 | 0 | 0.367 | 0.335 |
| File coverage with child traces | 368.170 | 0 | 1.645 | 1.621 |
| Function coverage with child traces | 368.170 | 0 | 1.218 | 1.167 |
| Function coverage with child traces and guarded comments | 333.847 | 0 | 1.785 | 1.781 |
| File coverage with child traces and guarded comments | 333.847 | 0 | 1.628 | 1.586 |

The nine non-comment cases selected the full suite in both finalists. The comment case selected five tests. Two additional interface-preserving body mutations isolate the selection path that actually narrows the suite. Those cases keep the function docstring and signature intact.


### Body-only extension

The additional timestamp and executor changes produced five and 51 failing tests respectively. The function finalist selected ten timestamp tests and 56 executor tests. The file finalist selected 70 and 56. Each covered every failing test. The 12-case corpus recorded 5,018 failing-test occurrences.

| Branch | Independent seconds | Misses | Host wall s | Host CPU s |
| --- | ---: | ---: | ---: | ---: |
| Official starter | 484.188 | 0 | — | — |
| `scheduling` | 441.804 | 0 | 0.032 | 0.031 |
| `static` | 419.078 | 0 | 0.114 | 0.097 |
| `coverage-file` | 2,057.101 | 6 | 0.616 | 0.581 |
| `coverage-function` | 2,047.622 | 6 | 1.530 | 1.499 |
| `hybrid-function` | 1,150.180 | 3 | 1.225 | 1.158 |
| `hybrid` | 419.078 | 0 | 0.416 | 0.405 |
| `coverage-pool-file` | 400.436 | 0 | 1.168 | 1.162 |
| `coverage-pool-function` | 396.099 | 0 | 1.370 | 1.318 |
| `hybrid-noop` | 361.776 | 0 | 1.485 | 1.471 |
| `hybrid-file-noop` | 366.113 | 0 | 1.526 | 1.476 |

The original six-job regression run exceeded its 900-second case limit and was excluded from the comparison. The controlled 12-case benchmark above completed with full-suite labels. A clean rerun may have different wall times.

## Release validation

The main branch uses function coverage with guarded comments. The `fallback-file` branch uses file coverage with the same comment handling. The `fallback-all` branch selects every test with variable worker scheduling.

Docker was unavailable on the host. For a local substitute, the digest-verified linux/amd64 base filesystem ran the exact release payload in a read-only sandbox as UID/GID 65534. The smoke test used two CPUs, a 4 GiB address-space cap, a 64 MiB temporary filesystem, a 256-process limit, and socket denial. These resource limits are local substitutes for the organizer's Docker configuration. The main and fallback plans were checked against the official scorer. Hidden changes, especially dependencies absent from the clean trace, remain the largest scoring uncertainty.

## Collection-time hardening

| Revision | Official sample seconds | Official misses | Extended independent seconds | Independent misses |
| --- | ---: | ---: | ---: | ---: |
| Previous release, `d0d48f2` | 727.627 | 0 | 679.871 | 1 |
| Hardened selector with AST caching, `efe5d81` | 727.627 | 0 | 409.246 | 0 |

The extended 14-case benchmark contained 6,689 failing-test occurrences. The extra JSONPath case produced 1,124 failures and reached the changed body during collection. The previous release selected only 53 tests. The hardened selector selected the full suite and caught all failures. A separate DISTINCT ON transform mutation produced 547 failing tests, all covered by a 552-test selection.

The function selector now falls back to the full suite when a changed body has no baseline execution context or a collection-time context. An explicit synthetic collection guard check exercised the fallback. The original 30 official and 12 independent plans were byte-identical before and after hardening. Across six alternating local host runs, caching pristine AST fingerprints reduced median CPU time from 0.917 to 0.828 seconds with identical output.

Docker Engine was downloaded and attempted locally. Workspace socket restrictions prevented the daemon from listening on its Unix socket. The digest-pinned sandbox check remains the available local substitute for a Docker build.

## Fixture readers

A Python audit hook on the clean pinned suite recorded active pytest node IDs when fixtures were opened. It observed 62 fixture paths. The full profiling run passed 1,620 tests, with one skipped test. The selector uses this map for same-path fixture changes, and retains the full suite for tracked collection-time reads, structural changes, and unrecognized files.

| Revision | Official sample seconds | Official misses | Existing 14 independent seconds | Independent misses |
| --- | ---: | ---: | ---: | ---: |
| Hardened, `0300798` | 727.627 | 0 | 409.246 | 0 |
| Fixture-aware | 355.031 | 0 | 375.393 | 0 |

Eleven of the original sixteen all-tests fallbacks disappeared from the public sample. Two additional clean-checkout fixture mutations, in qualify_tables.sql and eliminate_ctes.sql, produced one and zero failing tests respectively. Both selected two tests and incurred zero misses. These were benchmark labels only. The selector uses the pristine file-read observations.

## Isolated class-use experiment

The `class-coverage` branch adds a 344 KiB class-use map from a pristine pinned suite run (1,620 tests and 25,440 subtests passed; one skipped; 110.5 seconds wall on this host). Constructor observations include SQLGlot base classes and class setup use is expanded to all tests of that test class. Its selector retains the full-suite fallback for unproved import-time dependencies, including class values read while other classes are built.

The `tools/measure.py` host run on the 30 samples measured 1.518 seconds wall and 1.483 seconds CPU for this branch, separate from the official 297.491 simulated seconds. The host CPU is not an organizer container measurement.

A second full clean-suite profile installs the hooks before SQLGlot is imported and records the class/MRO of every expression validated by `Expression.error_messages` before or between tests. It passed 1,620 tests and 25,440 subtests in 109.0 seconds wall and identified 95 import-time receiver classes. A one-test coupled coverage check reproduced the original blank coverage context at that method while the hook identified its receiver class. The selector disables schema narrowing without this map, for a target class appearing in it, or if the pinned AST contains an unexpected reader of derived `required_args`. The three class schemas in the sample and independent class-schema evaluation were absent from the import receiver set. Official and independent costs were unchanged by the new guard.

| Variant | Official 30-sample simulated s | Misses | Independent classes | Independent schema mutants |
| --- | ---: | ---: | ---: | ---: |
| Previous `c07b8fb` | 323.703 | 0 | 42.306 s / 0 misses | 73.634 s / 0 misses |
| Class map with fixed-key expression schemas | 297.491 | 0 | 48.309 s / 0 misses | 42.300 s / 0 misses |

Two fresh schema mutations were labeled by the complete pinned suite, separate from the selector and image. `SequenceProperties.arg_types['maxvalue']` becoming required broke no tests. `Create.arg_types['expression']` becoming required broke 110 tests; the selector chose 755 and caught all 110. Two earlier dialect mutations (`TSQL.WEEK_OFFSET` and Snowflake numeric escape table) also had zero selection misses, with 48.306 simulated seconds together.

This experiment started from `c07b8fb` and therefore still misses the later independently labeled shared TPC-H fixture setup mutation (316.410 seconds including one 300-second penalty). The fix for shared fixture setup is on the main branch and must be combined before release. The class-map branch alone is not a final candidate. The 297.491-second number is the organizer's local simulated sample cost; container CPU and hidden-test misses have not been measured. Docker remains unavailable in this environment, so no real image build was run for this branch.

## Runtime class-table dependency experiment

This isolated branch started from local main `dfcd070`, including the shared fixture fix. One additional full pinned suite profile recorded receiver classes constructed outside pytest test contexts: 1,620 tests and 25,440 subtests passed, one skipped, 126.53 seconds wall. The 114 class keys are stored in `class-import-constructors.json`. The branch recognizes a sole lambda-body edit in a direct parser subclass's `FUNCTIONS` dispatch dictionary and same-key literal-value changes to a nested dialect Tokenizer's `NUMERIC_ESCAPES` dictionary. All other AST differences and unexpected source shapes retain the existing broad fallback. Both exceptions use only pristine SQLGlot source and class observations. No regression labels enter the selector or Docker image.

| Variant | Official 30-sample simulated s | Missed patches | Host wall s | Host CPU s |
| --- | ---: | ---: | ---: | ---: |
| Main `dfcd070` | 296.085 | 0 | 2.572 | 2.559 |
| Parser dispatch lambda only | 286.804 | 0 | 3.574 | 3.518 |
| Parser lambda plus numeric values | 267.140 | 0 | 3.375 | 3.370 |

Two fresh lambda-body mutations were labeled by separate complete pinned suite runs: Dremio `REGEXP_SPLIT`'s `limit` argument and Exasol `BIT_NOT`'s argument index. Each caused one failing test. The branch selected both, costing 55.028 simulated seconds versus main's 73.634, with zero misses. Two independent numeric value changes in BigQuery and Snowflake were also labeled by complete runs; neither caused a test failure. They cost 33.718 seconds together versus main's 73.634, with zero misses. A third independent BigQuery hex escape value change caused two failing tests in a separate 110.706-second complete suite run. The branch selected both at 16.565 simulated seconds versus main's 36.817, again with zero misses.

The branch retained zero misses on the prior extended, final, class-schema, class, fixture, and quiet independent corpora (costs 375.393, 327.923, 42.300, 48.309, 4.832, and 299.994 simulated seconds respectively). The numeric exception does not include generic `NUMERIC_ESCAPES` read contexts because those are shared by nearly all tokenizers; the pinned generator reads only table truthiness and key membership, the metaclass reads only keys, and the runtime tokenization read is covered by receiver construction. Direct test-source references, reflective tests, source readers, opaque subprocess callers, and class-unprofiled tests remain selected. This classification can miss unobserved dynamic access to a value without constructing its tokenizer; the independent labels constrain but cannot eliminate that risk.

Two structural guard checks changed a numeric escape dictionary key and a parser lambda argument list separately. Both selected the entire 1,620-test suite, as intended.

No real Docker image build was available for this branch. The exact Dockerfile payload and `.dockerignore` include the new constructor-import map; release integration must check the actual build context and container limits.

On integration, direct `__init__`/`__new__` overrides in an eligible parser or tokenizer/dialect class were excluded, since the pristine receiver profile wraps the inherited base constructor. This guard preserved 267.140 simulated seconds and zero misses on the official sample, 55.028/0 on the two failing lambda labels, and 16.565/0 on the failing numeric label. A build-context preflight found all nine Docker `COPY` inputs. The exact payload ran as UID/GID 65534 in the digest-verified read-only Bubblewrap substitute with two CPUs, 4 GiB address-space cap, 64 MiB `/tmp`, and denied socket calls; its output again scored 267.140/0. The substitute is not a real Docker build, and its wrapper CPU reading excludes namespaced child CPU.

## Closure factory dispatch experiment

This isolated branch started from main `ac42533`, which contains the constructor override, relocated-statement, and comment/header safety guards. It recognizes a single existing literal argument change in a parser class's `SHOW_PARSERS` dictionary. The pinned imported factory must do no import-time work beyond defining and returning a closure; its inner function has no evaluated defaults, decorators, or unsupported annotations. The parser lineage must have no constructor/subclass hooks. The class's derived `SHOW_TRIE` must consume only dictionary keys through `sqlglot.trie.new_trie`, and static attribute reads must exclude import-time aliases of the changed table. All other source AST nodes must match. Changed keys, dynamic arguments, changed factory calls, and multi-file patches remain broad. The code uses only pinned unmodified SQLGlot source and clean-suite class maps; independent labels stay outside the selector and image.

| Variant | Official 30-sample simulated s | Missed patches | Host wall s | Host CPU s |
| --- | ---: | ---: | ---: | ---: |
| Main `ac42533` | 267.140 | 0 | 3.423 | 3.387 |
| Closure factory variant | 255.777 | 0 | 3.993 | 3.968 |

Three fresh single-file factory mutations were labeled by separate complete pinned SQLGlot suite runs. Changing the `INDEXES` closure's output name caused one failing test. Changing the `KEYS` closure's `target` keyword caused one failing test. Both were selected; the former corpus paired with a zero-failure `GROUPS FOR USER` edit cost 50.908 simulated seconds versus main's 73.634, and the latter cost 25.454 versus main's 36.817, all with zero misses. Each labeling run exercised 1,620 tests and 25,440 subtests (apart from the intentional failures). Three structural checks changing a dictionary key, using a dynamic argument, and replacing the factory call selected the full 1,620 tests.

The official sample gain is 11.363 simulated seconds, offset by roughly 0.6 extra host CPU seconds in this run. The changed sample patch selected 125 tests and retained a 21.454-second opaque pool reader. Hidden-test generalization remains uncertain, especially dynamically obtained callable references that bypass a profiled parser constructor; generic `SHOW_PARSERS` readers, source-reading tests, reflective tests, subprocess callers, and class-unprofiled tests are included. Docker inputs are unchanged; this isolated branch has not run a real Docker build.

## Spawned tokenizer receiver profile

The broad test-file guard for numeric escape values selected every test in a file mentioning the parent dialect's name. It added 464 tests to the Snowflake numeric sample and 229 to each BigQuery numeric case after other guards. The parent dialect constructor guard added another 91 tests to Snowflake and 78 to BigQuery after removing the file guard. Pinned source has only four SQLGlot reads of `NUMERIC_ESCAPES`: the dialect metaclass and two generator reads inspect keys or truthiness, and `Tokenizer._init_core` passes the tuple values to `TokenizerCore`. No pinned test source directly mentions `NUMERIC_ESCAPES`.

The parent class profile does not observe constructors in spawned optimizer/executor workers. The `numeric-precision` branch therefore profiles these workers separately on the pristine checkout: 227 tests and 6,508 subtests passed in 43.69 seconds on this host. All 2,183 submitted tasks yielded a child record; 24 tests submitted tasks, 317 dialect/tokenizer/parser/generator/expression class keys were observed, and zero tasks spawned nested processes. Snowflake's tokenizer appeared in nine child callers and BigQuery's in eight. The map is generated from the unmodified pinned checkout; no regression labels are included. A missing or inconsistent child map selects the full suite for structural edits. The child receiver map is unioned into every class-use fast path.

| Numeric selector | Official 30 simulated s | Misses | BigQuery hex independent s | Misses | Two other numeric independent s | Misses |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Parent-name and dialect guards, `d76f249` | 267.140 | 0 | 16.565 | 0 | 33.718 | 0 |
| Remove parent-name guard, retain dialect users and child map | 262.673 | 0 | 13.214 | 0 | 25.900 | 0 |
| Tokenizer receivers in parent and children, retain direct/reflection guards | 259.973 | 0 | 10.577 | 0 | 20.563 | 0 |

The final row selected 318 tests for the Snowflake sample numeric patch and 267 for the independently labeled BigQuery hex patch. Child tracing uniquely added six tests for each compared with parent-only receiver selection. The independent hex patch caused two real test failures; both selected tests use the BigQuery tokenizer in the clean profile. Three more full-suite numeric mutations (DuckDB hex, Snowflake hex, BigQuery hex limit) cost 33.248 seconds, with two BigQuery failures covered and zero misses. The generalized child map changes the class-schema corpus from 42.300 to 42.543 simulated seconds with zero misses; the extended corpus stays 375.393/0. Local selector wall/CPU for the official sample was 4.050/4.017 seconds; this is separate from organizer container CPU. A file-wide fallback for all 227 process-pool tests would make the Snowflake numeric patch cost 27.871 seconds, compared with 9.986 seconds using the complete child trace. Direct dynamic access to a numeric escape value without constructing a tokenizer remains an unobserved risk; pinned test source and the reflective/source-reader guards constrain it.

A separate `Exists.arg_types['expression']` optional-to-required mutation was labeled by the complete pinned test suite (35 failing test IDs in 92.75 seconds). The parent-only class map missed three failing process-pool tests and scored 325.454 seconds including one 300-second miss penalty. The generalized child map selects all 35 failures in 167 tests and scores 25.729 seconds, zero misses. This is direct evidence that child receivers matter for expression schema changes, not only tokenizer values.

## Pinned source-reference index

On the `class-reader-index` branch, `tools/build_reference_index.py` inverts the existing class-field reader scan across the pristine source and coverage contexts in `impact.json.gz`. It stores 1,355 referenced symbol names in a 3,822,776-byte compressed map and binds the map to the SHA-256 of `impact.json.gz`. Neither patches nor regression labels are used to build it. Missing, mismatched, corrupt, and malformed entries use the unchanged live scan.

Against fixed commit `f51157c`, the index and a separate, smaller AST-cache prototype both emitted byte-identical output for the 30 official patches and 68 independent patches across 19 corpora. The official scorer gave 248.610 simulated seconds and zero misses, unchanged from the base. Every independent corpus likewise had zero misses. Fifty seeded source symbols and five named class/table fields matched the original source scan exactly, including the import-read flag. Alternating sample host CPU measurements (four runs per variant, shared host) had medians of 3.457 seconds for the base, 3.859 for the AST cache, and 2.073 for the index. This is a CPU improvement only; host CPU is not the organizer container CPU. The AST cache was not retained because it did not improve CPU time.

After rebasing onto the later safety-guard commit `056b928`, a fixed-commit comparison again emitted byte-identical outputs for all 98 patches across the official sample and 19 independent corpora; the organizer's scorer reported 248.610 simulated seconds and zero misses on the official sample, and zero missed patches across the independent corpora. The Docker context check found all 11 required inputs. A real Docker build was not available in this environment for this isolated branch.
