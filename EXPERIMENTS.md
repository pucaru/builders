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

## Receiver-aware parser lambda readers

This isolated branch starts from `b6392f0`. For a single existing lambda-body edit in a direct `Parser.FUNCTIONS` subclass table, it keeps the edited lambda's observed body contexts, exact parser receiver constructors from the parent and process-pool profiles, dynamic `parser_class.FUNCTIONS` consumers, explicit test references, reflective and source-reading tests, and opaque subprocess callers. It excludes only statically unrelated class-body copies of base tables and the pinned base Parser's `self.FUNCTIONS` read, whose receiver is covered by the constructor map. Unexpected import-time reads, descendants, changed class shape, multi-file edits, and malformed diffs retain the all-tests fallback. No patch key or failing-test label enters the selector.

The separate pristine code-object call trace passed 1,620 tests and 25,440 subtests with one skipped test in 184.19 host seconds. It found zero parser lambda calls outside test contexts or during setup/teardown. A fresh interpreter sweep importing all SQLGlot modules except the CLI-only `__main__` module also observed zero such calls. The trace map includes its `impact.json.gz` SHA-256; missing, stale, or malformed maps disable this optimization. The full-suite trace observes the parent pytest process. The module sweep covers the same pinned imports before a process-pool worker hook is installed, while the existing child coverage and constructor maps cover task-time execution. A dynamically computed alias or a child-only import side effect outside those observations remains a residual risk.

| Variant | Official 30-sample simulated s | Missed patches | Host wall s | Host CPU s |
| --- | ---: | ---: | ---: | ---: |
| Main `b6392f0` | 248.610 | 0 | 4.084 | 4.054 |
| Receiver-aware candidate | 233.011 | 0 | 6.139 | 6.069 |

Three new single-file parser lambda mutations were labeled in independent copies by complete pinned suites. Dremio `REGEXP_SPLIT` and Exasol `BIT_NOT` each caused one failing test; a ClickHouse `LENGTH` argument edit caused none. All were selected, scoring 36.538 seconds versus main's 82.639, zero misses. A fourth, separate ClickHouse `TRIMRIGHT` lambda edit caused one failing test and scored 12.686 seconds versus main's 27.611, zero misses. The earlier reader-index prototype `34d6d68` took 25.742 seconds on that ClickHouse case. Existing Dremio/Exasol lambda failures also scored 23.852 seconds versus main's 55.028, zero misses.

All 22 available independent labeled corpora scored zero missed patches. A wrong diff context, a multi-file lambda edit, an absent call trace, and an injected setup/import call for the edited lambda each selected all 1,620 tests. `tools/check_docker_context.py` found all 12 Docker `COPY` inputs, including the new trace map. The extra host CPU is about two seconds for the 30-sample batch, leaving a measured local gain of roughly 13.6 seconds after CPU. A real Docker build and container CPU measurement remain to be done by release integration; no regression labels or profiling scripts enter the image.

## Foreign parser trie-key reader filter

The `factory-reader-filter` branch retains the existing value-only parser factory proof and recomputes direct readers for that branch. It excludes only a foreign class body's bare-name `SHOW_TRIE` construction when the same class previously assigned an independent literal-key dictionary to the field, the exact expression iterates only the dictionary's keys, and `new_trie` resolves to the pinned `sqlglot.trie` import without rebinding. Decorators, metaclasses, unparseable source, aliases, and other read shapes keep the broad selection. This rule uses only pristine source and clean-suite contexts. No patch or failure label is embedded in the selector.

The 30 official patches scored 211.657 simulated seconds with zero misses, compared with 233.011/0 for parent `94ed6cb`. The SingleStore factory edit dropped nine tests, including the 21.454-second TPCDS test, whose clean context had read an unrelated MySQLParser table during its class-body trie construction. Six alternating host runs measured median selector CPU 3.490 seconds for the parent and 3.751 seconds for this branch; the official scorer excludes CPU, and this host is shared.

Across 23 existing independently labeled corpora (105 patches), the branch had zero misses. Two prior SingleStore factory edits scored 8.200/0 versus 50.908/0; a separate third scored 4.100/0 versus 25.454/0. Two fresh, complete pinned-suite labels changed different SingleStore factory literals: `ROLES FOR USER` target `True` to `False` failed no tests, while `PLAN` target `True` to `False` failed only test #670 (`TestSingleStore::test_show`). Both selected test #670 and excluded TPCDS; together they scored 8.200/0 versus 50.908/0. The other optimizer, executor, dialect, and serializer selections of TPCDS remain unchanged. Docker payload files are unchanged; no real Docker build was available for this isolated branch.

## One-line conditional header coverage

Starting from `322606f`, this branch extends guarded adjacent replacements to an `if` header only when the old and new nodes have the same type, unchanged branch and alternate ASTs, unchanged name loads/bindings, no nested scope or assignment expression in the condition, verified diff context, and compilable patched source. Tests reaching the original header are selected with the existing source reader, subprocess, unmapped, and same-file guards. Other conditions retain the whole-function selection; a relocated return, changed source header, and mixed code/comment edits keep their broader fallbacks. No patch ID, test outcome, or public sample answer enters this rule.

| Variant | Official 30-sample simulated s | Missed patches | Fresh six condition edits simulated s | Missed patches |
| --- | ---: | ---: | ---: | ---: |
| Parent `322606f` | 211.657 | 0 | 76.962 | 0 |
| Guarded `if` condition | 207.303 | 0 | 76.721 | 0 |

The six fresh edits were labeled by separate complete pinned-suite runs after a clean run of 1,620 passed, one skipped, and 25,440 passing subtests. BigQuery parser identifier handling caused 60 failing test IDs, a separate BigQuery catalog condition caused one, a MySQL limit parser condition caused two, optimizer set-operation scope caused 57, date simplification caused none, and generator boolean handling caused 46. All 166 failing IDs were selected; the identifier edit contains a generator expression and deliberately takes the broader fallback. Labels and logs remain in `independent-if-condition` outside the selector and Docker payload. Twenty-three other `independent-*` corpora (81 patches), plus `parser-independent` and `compare-independent` (six patches), scored zero misses under the official scorer. On the sample, the BigQuery parser plan lost 101 tests and fell from 9.214 to 4.876 seconds; one other parser edit saved 0.016 seconds. An exact 12-file Docker payload under the digest-pinned read-only Bubblewrap substitute, UID/GID 65534, two CPUs, 4 GiB, and a 64 MiB temporary filesystem scored 207.303/0. Host selector CPU in a sample run was 3.674 seconds. This substitute is not a real Docker build or a container CPU measurement.

## Numeric escape key consumption

This isolated branch starts from `322606f`. The existing safe numeric specialization handles fixed-key, tuple-value edits to a direct dialect Tokenizer. It previously selected every clean construction of that tokenizer, even when a test never consumed the edited escape key. The pinned source passes the dictionary through `Tokenizer._init_core` to `TokenizerCore`; two methods retrieve tuple values with the key `"0" if is_octal else peek`. Its only other core read tests dictionary nonemptiness. The dialect metaclass and generator also inspect only keys or truthiness, as checked by the existing AST guard. The new guard verifies this core read shape, scans SQLGlot for any other `.numeric_escapes` read or dialect `_init_core` override, then selects clean observations of the changed key in parent and process-pool workers. Direct test-source access, reflection, source readers, subprocess callers, and tests absent from the profile remain selected. Missing/stale/inconsistent key data uses the prior constructor selection. No regression label or patch ID enters the map or image.

The profile passed 1,620 tests and 25,440 subtests with one skipped in 116.02 host seconds. It recorded every one of 2,183 pool tasks, nine owner class keys, no nested processes and no import-time numeric-key read. The compact 815-byte map is bound to the SHA-256 of the pristine `impact.json.gz` and verified against the independent pool-class task counts. Snowflake's numeric escape dictionary had no key value consumed by the clean suite; BigQuery's `x` key had four test consumers. The pinned optimizer pool submits a function, SQL and dialect strings, and fixture dictionaries; the executor passes an expression built by `parse_one(sql)` in the observed parent process plus fixture metadata. Its worker initializer only assigns schema/tables. The selector checks these two `submit` call shapes and initializer body before using key precision, since the child hook is installed after arguments are unpickled.

| Variant | Official sample simulated s | Misses | Host selector wall s | Host selector CPU s | Three fresh numeric edits | Misses |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Main `322606f` | 211.657 | 0 | — | — | 33.248 s | 0 |
| Per-key consumption | 205.495 | 0 | 4.957 | 4.638 | 13.772 s | 0 |

The official Snowflake numeric edit fell from 318 tests/9.986 seconds to 48 tests/3.824 seconds. The three independent edits altered DuckDB hex, Snowflake hex, and BigQuery hex limits; the latter produced two failing tests, both selected. A separate BigQuery hex edit also produced two failing tests and scored 6.124 seconds/0 misses instead of 10.577/0. Earlier two independent numeric edits cost 7.648/0 instead of 20.563/0. The class-schema and extended independent corpora were unchanged at 42.543/0 and 375.393/0. Removing the key map or corrupting its task count reverted the Snowflake edit from 48 to the original 318 tests. The Docker context check found all 13 inputs. The exact payload ran under the digest-verified read-only Bubblewrap substitute with two CPUs, a 4 GiB address-space cap, a 64 MiB temporary filesystem, UID/GID 65534, and denied socket calls; its output again scored 205.495/0. The substitute's wrapper CPU measure excludes namespaced child CPU. A real Docker build and organizer container CPU remain unavailable.

## Reuse pristine AST traversals

The `cpu-opt-322606f` branch reuses a single `ast.walk` node list within each pristine source file when checking parser lambda and factory readers, and within guarded statement replacement. The order, predicates, selected tests, and scheduler are unchanged. This is a run-time optimization; the map is still derived only from pinned SQLGlot.

Against fixed parent `322606f`, selector output was byte-for-byte identical for all 30 official patches and 104 patches across 26 independent corpora, including additional deep mutants and conditional edits. The official scorer reports 211.657 simulated seconds and zero misses for both. Four alternating sample runs per variant on a shared host measured median selector CPU 4.233 seconds for the parent and 3.862 seconds for this candidate. The measured reduction is 0.371 host CPU seconds; organizer CPU may differ. The Docker context checker found all 12 required `COPY` inputs. No real Docker build was available for this branch.

A further traversal pass builds parser-lambda node order and parent links together using the same breadth-first order as `ast.walk`. It again emitted byte-identical output for the 30 official and 104 independent patches, scoring 211.657/0 officially. In four alternating host runs, median CPU moved from 3.758 seconds for the prior CPU candidate to 3.601 seconds for this pass, a 0.157-second additional host reduction. The Docker context still contains all 12 inputs; a real Docker build was unavailable.

## Immutable dialect scalar readers

This isolated follow-up starts from `637cc23`. A pristine AST scan identifies 122 direct Dialect class field names assigned immutable scalar literals. During clean-suite profiling, wrappers on the Dialect instance and `_Dialect` metaclass `__getattribute__` return the original value and record the receiver class and field. The same wrappers run inside process-pool tasks. Every submitted child task must produce a record, and the compressed map is tied to `impact.json.gz` by SHA-256. This captures dynamic `getattr` readers as well as direct attribute syntax. The selector also includes all static read-site contexts, source readers, reflective tests, opaque subprocess callers, and tests absent from class profiling. It excludes derived class constructor users only for a single scalar edit in a direct undecorated Dialect subclass with no import-time source or observed read. A missing/stale map, any observed setup/teardown read, a descendant attribute-access override, unproved class-dictionary/`vars` use, or a read site that writes to a persistent cache returns to the prior class-use selection.

The full profile passed 1,620 tests and 25,440 subtests, with one skipped, in 112.64 host seconds. It matched all 2,183 pool tasks, recorded 35 owner keys, and found no shared-phase scalar reads. The target TSQL, BigQuery, Oracle, and Teradata `WEEK_OFFSET` values and independent BigQuery `HEX_LOWERCASE` and Snowflake `COPY_PARAMS_ARE_CSV` values had no import-time reads. Class-dictionary reads in the pinned metaclass use fixed keys, the Tokenizer class-body check tests only `BYTE_STRING_ESCAPES`, and two arbitrary `exp.convert(value.__dict__)` contexts remain selected. The unused `object_to_dict(vars(obj))` helper and any new call to it are guarded. A source-derived gate rejects fields read in constructors/core initialization or any function with direct attribute/subscript stores or deletions, global/nonlocal bindings, or a cache decorator. It excludes `_type_mapping_cache` for `SUPPORTS_USER_DEFINED_TYPES`, Generator's `NORMALIZE_FUNCTIONS` snapshot, TokenizerCore's `BYTE_STRING_IS_BYTES_TYPE` snapshot, and an UNNEST resolver field while retaining the tested values. Indirect persistence through a callee or a result reused across tests remains a hidden-test risk; this is not a full interprocedural purity proof.

| Variant | Official sample simulated s | Misses | Host selector CPU s | Fresh three week edits | Misses | Two other scalar edits | Misses |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Numeric base `637cc23` | 205.495 | 0 | ~4.54 | 34.155 s | 0 | 25.462 s | 0 |
| Scalar readers | 198.692 | 0 | 5.386 | 14.067 s | 0 | 10.842 s | 0 |

The public TSQL week edit selects 60 tests/4.689 seconds instead of 205/11.492. Fresh complete pinned-suite labels changed BigQuery, Oracle, and Teradata week offsets; each had at least one real failure, including an Oracle change detected by a Teradata test. BigQuery `HEX_LOWERCASE` had two failing tests and Snowflake `COPY_PARAMS_ARE_CSV` one; all three were selected. The independent dialect, class, schema, extended, final, fixture, statement, and numeric corpora retained zero misses. Missing scalar maps, an injected descendant `__getattribute__` override, or a new dynamic `vars` reader each reverted the sample edit to 205 selected tests. Docker preflight found all 14 inputs. The exact payload ran as UID/GID 65534 under the digest-verified read-only Bubblewrap substitute, two CPUs, 4 GiB address cap, 64 MiB temporary filesystem, and denied socket calls; its output scored 198.692/0. The wrapper CPU reading excludes namespaced child CPU. No real Docker build was available.

## Pristine source reads for comment-only edits

The isolated `schedule_audit_candidate` branch starts from `322606f`. A fresh clean-suite `open` audit completed 1,620 tests and 25,440 subtests, with one skipped, in 112.43 host seconds. Because cached bytecode can hide source imports, an independent run from a copy with no `__pycache__` files audited 197 `.py` opens: 183 distinct source files, 97 Python importlib reads during collection/import, 86 lazy importlib reads during tests, and 14 direct reads by `TestTyping::test_no_redundant_expression_metadata`, all in `sqlglot/typing/`. Importlib reads only compile the source; recursively identical executable bytecode is proved before narrowing. The pinned `test_sqlglotc` tests read source files they create in temporary directories; `test_lazy_load` starts a subprocess that only checks SQLGlot's initial dialect registry. A pinned-source scan found no test use of `co_firstlineno`, line tables, tracebacks, or source line numbers. `test_typing.py` compares code objects and source ASTs in the typing package. These are properties of the pinned checkout and test suite, not assumptions about a changed patch's intent.

A pure single-file comment edit must pass the existing diff-context, source-header, compilation, and AST checks including type comments. It additionally requires recursively identical compiled code after removing only source-location metadata. The new source-read map credits every direct read to all tests in that test module, conservatively covering shared setup, and credits collection-time direct reads to the entire suite. A task-complete child profile captured 2,183 process-pool tasks from all 24 callers, including no-cache task-time imports. Every spawned worker loaded an early `sitecustomize` hook to cover bootstrap and initializer reads before its first task. Six task-time `.py` opens were all importlib reads; no bootstrap or direct child source reads occurred. The pinned `test_optimizer` and `test_executor` suites passed 227 tests and 6,508 subtests in this run. A separate source-derived line-observer map enumerates every `EXPRESSION_METADATA` annotator code filename read by `TestTyping`'s `co_consts` comparison; all 14 code files are in `sqlglot/typing/`, including `__init__.py`. Any other pinned test use of line-sensitive APIs becomes a global conservative test set. The map is tied to the impact map, child map, exact test IDs, read entries, and line-observer entries by SHA-256; raw profiles and independent labels remain outside the image. Missing, stale, or malformed maps keep the previous five-test conservative selection for an ordinary comment edit. Multi-file edits and changes to code or type comments retain the existing fallbacks.

| Variant | Official 30-sample simulated seconds | Missed patches | Host selector CPU seconds |
| --- | ---: | ---: | ---: |
| Parent `322606f` | 211.657 | 0 | ~4.5 on shared host |
| Source-read candidate | 204.175 | 0 | 4.3 on shared host |

The 7.482-second gain comes from three comment-only samples previously scheduled at 2.494 seconds each and now emitted with zero workers. Two fresh full-suite comment mutations in Oracle generator and DuckDB typing code failed no tests; the Oracle edit selected zero tests and the typing edit retained its line/source observer. A separate mixed comment and executable early raise in `time.format_time` produced 62 failing test IDs in a complete 108.145-second suite and selected all 1,620 tests. A parser comment inserted before a later `# type: ignore` shifted the recorded AST type-ignore line and correctly selected the full suite. The two comment controls and mixed edit scored 75.645 simulated seconds, zero misses, versus 76.128/0 on the parent; the typing case remains conservative. The separate Oracle comment scored 0.000/0 versus 2.494/0 on the parent. Across 28 independent corpora (95 patches) available at the time of scoring, the candidate had zero misses. The source-read auditors and full-suite mutation labels remain outside the Docker payload. Real Docker build status is unchanged.

## Integrated release checkpoints

The following scores are from the organizer's exact local scorer on the same 30 supplied patches. Host CPU is shown separately because the board adds its own three-run container CPU measurement. Each commit has a clean Docker `COPY` context check. The final row's 15-file payload ran read-only as UID/GID 65534 with two CPUs, a 4 GiB address cap, a 64 MiB temporary filesystem, and denied sockets under the digest-verified Bubblewrap substitute. Its output was byte-identical to the host selector. This is not a real Docker build.

| Local commit | Change | Simulated s | Misses | Host selector CPU s | Independent labels |
| --- | --- | ---: | ---: | ---: | --- |
| `322606f` | Foreign trie-key proof | 211.657 | 0 | 3.850 repeat | Prior corpora, zero misses |
| `f460abb` | Guarded `if` and numeric key reads | 201.141 | 0 | 4.661 run | 94 patches in 29 corpora, zero misses |
| `f274ee4` | Reuse AST traversals | 201.141 | 0 | 3.449 alternating median | Byte-identical to parent across 95 independent patches |
| `b2612ea` | Guarded immutable scalar reads | 194.338 | 0 | 3.788 run | 97 patches in 29 corpora, zero misses |
| `fc4dcbc` | Proved comment-only source/line reads | 186.856 | 0 | 4.149 run | 97 patches in 29 corpora, zero misses |

The scalar rule retains a residual risk from indirect state persisted by a callee in one test and consumed in another. It rejects observed import/setup reads, direct stores, constructor snapshots, cache decorators, and concrete pinned cache examples; five new scalar mutations with actual full-suite failures were all selected. The comment rule uses recursively equal compiled code excluding only locations, a fresh no-cache source-read audit, and a task-complete early worker audit. The unchanged broader selector is available at `f274ee4` (201.141/0), with earlier `322606f` (211.657/0) also retained. The GitHub tree at `dbba02a` exactly matches local `fc4dcbc`.

## Binary gzip-map reads

From `f274ee4`, the five pinned gzip JSON maps are opened as binary streams. Python's standard `json.load` accepts byte streams and decodes them directly, avoiding `TextIOWrapper` work. This makes no selection, scheduler, image file, or Dockerfile changes. Output was byte-for-byte identical for the 30 official patches and 111 patches across 29 independent corpora. The official scorer reported 201.141 simulated seconds, zero misses, for both. The exact 13-file payload run as `nobody` in the digest-verified Python 3.13 base-root substitute likewise returned identical output. The Docker context checker passed; a real Docker build was unavailable.

Two four-run alternating measurements with host Python 3.12 found median CPU 4.148→3.417 and 4.067→3.189 seconds. Host Python 3.13, however, measured 3.064→3.096 seconds in one four-run comparison. Inside the constrained Python 3.13 base-root substitute, self-reported median CPU was 3.825→3.725 seconds across four alternating runs per variant. The likely organizer CPU benefit is small and noisy, roughly one tenth of a second in the closest substitute, and this candidate should not be claimed as a large score gain.

## Exact parser lambda call profile

This isolated branch starts from `f274ee4`. A full pristine pinned-suite profile records each parser lambda code object by source path, first line, and qualified name in the parent pytest process and every spawned optimizer/executor task. A worker startup hook begins before argument deserialization and imports; the task wrapper records calls during execution. The profile checks the collected manifest (including the skipped test), all 2,183 submitted child records and worker startup markers, and expands setup/teardown observations to class scope. The completed clean run passed 1,620 tests and 25,440 subtests with one skipped in 209.75 host seconds. It found 513 executed parser lambda sites, zero import/startup calls, and zero setup/teardown sites. The 8 KiB compressed map is bound to the pristine impact map SHA-256 and exact pool task/caller distribution. No patch or regression label is in the map or Docker image.

For a sole body edit to an existing direct Parser subclass `FUNCTIONS` lambda, the selector first runs its existing structural and import/alias reader proof. It then permits the call trace only if the lambda's line and total source line count stay fixed; Name loads and bindings remain identical; no `__class__`, `super`, nested scope, named expression, yield, or await appears; and the exact target site is present in the profile. Import or shared calls select all tests. Absent, corrupt, or stale maps and unsupported source shapes keep the previous reader selection. Direct test table references, callable code-object inspectors, target parser constructor users, reflective tests, source readers, unprofiled tests, and subprocess gaps remain selected. The pinned production source has no callable code-object or dynamic `getattr(..., "FUNCTIONS")` reader; an unexpected one disables this precision. Tests with changed callable behavior must invoke its body at least once, and that clean invocation is attributed to their test ID. Changed closure construction is excluded by the shape guards.

| Variant | Official 30-sample simulated s | Misses | Fresh three lambda edits simulated s | Misses |
| --- | ---: | ---: | ---: | ---: |
| Parent `f274ee4` | 201.141 | 0 | 88.837 | 0 |
| Per-lambda calls | 193.446 | 0 | 86.319 | 0 |

The Dremio sample's parser edit selected 79 tests/4.242 seconds instead of 379/11.937 seconds; its lambda was invoked by one clean Dremio test. Three fresh mutations were independently labeled by full pinned-suite runs: DuckDB `SHA256` output length caused four failing tests and used the precise rule (529 to 294 selected tests); Presto `BITWISE_NOT` caused three failures but remained the all-tests fallback because a derived parser copies its table; BigQuery `LENGTH` caused three failures but remained broad because its table is annotated rather than a direct assignment. All ten failures were selected. The other 100 available independent patches across 30 corpora also had zero misses under the official scorer. Injected free names/`__class__`/nested scopes, stale and missing maps, import/setup calls, and a multi-file edit restored the earlier selection or all tests as appropriate. One host sample run measured 4.381 selector CPU seconds, separate from the official 193.446 simulated seconds. The exact 14-file Docker payload ran read-only under the digest-verified Bubblewrap substitute at UID/GID 65534, two CPUs, 4 GiB, 64 MiB `/tmp`, and denied sockets; its output matched the host bytes and scored 193.446/0. No real Docker build or organizer CPU measurement was available.

## Combined lambda-call checkpoint

From `7b459f1` (186.856/0), integrating the pristine parent-and-child parser-lambda call profile at `fcc4b59` produced **179.161 simulated seconds, zero misses** on the official 30 patches. The Dremio lambda edit fell from 11.937 seconds/379 tests to 4.242 seconds/79 tests. One host Python 3.13 run measured 5.220 selector CPU seconds. All 100 independently labeled patches across 30 corpora scored zero misses with the organizer's scorer. A fresh DuckDB mutation caused four failures and used the exact call path; Presto and BigQuery edits caused three failures each and retained broad fallbacks. The 16-file Docker payload passed the COPY allowlist check and emitted byte-identical output under the digest-verified read-only Bubblewrap substitute, scoring 179.161/0. No real Docker build was available. The prior `fc4dcbc` 186.856/0 and `f274ee4` 201.141/0 remain verified fallbacks. The call path excludes changed closures and import/setup calls but still carries residual risk from indirect cross-test state or dynamic code inspection not present in the pinned source audit.

## Annotated parser dispatch dictionaries

`class_lambda_edit` already accepts an `AnnAssign` class dictionary and proves that replacing only the edited lambda bodies makes the entire original and patched module AST identical, including annotation, keys, defaults and class headers. The receiver-aware reader check previously searched only `Assign` declarations, so a BigQuery `FUNCTIONS` lambda edit took the all-tests fallback. This branch accepts a simple annotated Name target with a dictionary value only when `from __future__ import annotations` is present. The existing clean import-call trace, constructor map, direct alias and subclass guards still apply. BigQueryParser is the only pinned parser class with such an annotated `FUNCTIONS` dictionary.

The official 30 patches scored 186.856 simulated seconds, zero misses, unchanged from base `7b459f1`. An independently full-suite-labeled BigQuery `LENGTH` lambda edit changed argument index 0 to 1 and caused failures #27, #73 and #1295. This branch selected 504 tests and all three failures, versus the base's 1,620 tests. The three-case `independent-lambda-key` corpus scored 65.593/0 versus 88.837/0. Across the official sample and 30 available independent corpora (130 patches), the organizer scorer reported zero missed patches. Docker payload files are unchanged; no real Docker build was available for this isolated branch.

### Exact-call extension for annotated tables

After the generic postponed-annotation proof in `8044708` (the same `impact.py` change as the separate `1a77f0f` branch), the exact-call rule also accepts a simple annotated `FUNCTIONS` dictionary. The unchanged class annotation must have `from __future__ import annotations` before the generic reader proof is reached; otherwise the broad fallback remains. On the independently labeled BigQuery `LENGTH` lambda edit, generic annotation handling selected 504 tests/13.573 simulated seconds, and the exact-call rule selected 266 tests/10.577 seconds. All three actual failures were selected. The three fresh lambda edits together scored 60.079/0, versus 63.075/0 for generic annotation handling without call precision and 86.319/0 for the original direct-assignment-only rule. The official 30 scored 193.446/0 unchanged. Across 100 independent patches in 30 corpora, there were zero misses. Shape/map fallback guards and all 14 Docker build-context inputs passed; no real Docker build was available.

## Parser lambda static-scan CPU filter

From fixed `8080ce3`, the parser-lambda callable safety scan parses a pristine production file only if its source contains a code-object field token or both `getattr` and the table name. Without those text tokens, neither existing AST predicate can match. The two read-only AST walks are combined into one. This changes no proof condition, test selection, scheduler, map, or Docker payload.

Selector output was byte-for-byte identical for the 30 official patches and 114 patches in 30 independent corpora. The official scorer reported 193.446 simulated seconds and zero misses for both. Four alternating host runs per variant measured median CPU 4.323 seconds for `8080ce3` and 3.810 seconds for this candidate. The exact 14-file payload also matched byte-for-byte under the digest-verified Python 3.13 base-root substitute at UID/GID 65534, two CPUs, and 4 GiB; four alternating self-reported CPU runs measured medians 4.882 versus 4.530 seconds. The gain is a CPU-only observation on this host. The Docker context checker passed. A real Docker build was unavailable.

## Integrated annotated-lambda and CPU checkpoint

The combined branch applies the guarded annotated-table reader (`eba552e`), exact-call extension (`008b5a1`), and AST prefilter (`7dceddb`) on top of `199514a`. The organizer's scorer reports **179.161 simulated seconds and zero misses** for the official 30 patches, identical to `199514a`; the emitted bytes are identical. All **100 independently labeled patches in 30 corpora** have zero misses. A fresh, full-suite-labeled BigQuery `LENGTH` body mutation selected 266 tests, including all three actual failures; the three independent lambda mutations together score 60.079/0 versus 88.837/0 before annotated-table handling. The AST prefilter changes no selected tests. Three alternating host Python 3.13 runs per branch measured median selector CPU of 4.569 seconds on `199514a` and 4.167 seconds on `7dceddb`.

The Dockerfile's exact 16 `COPY` inputs passed the context check. A read-only Bubblewrap run using the digest-verified Python 3.13 base filesystem, UID/GID 65534, two CPUs, a 4 GiB address cap, 64 MiB `/tmp`, and denied sockets emitted bytes identical to the host run and scored 179.161/0. This substitute does not measure the organizer's full container CPU and is not a real Docker build. The prior `verified-179` branch at `fcc4b59` remains available. The exact-call proof still has residual risk from indirect state shared across tests or dynamic introspection of a callable after it is constructed; no such pinned reader was found in the source audit.

## Literal-only parser lambda bodies

An independently labeled adversarial BigQuery `LENGTH` edit replaced its expression constructor with `exp.Length.arg_types.clear() or seq_get(args, 0)`. The old and new lambda bodies load exactly the same names, so the prior per-call guard accepted the edit. Running the complete pinned suite yielded 24 failing test IDs. Its 266-test selection omitted 16 and scored 310.577 simulated seconds with one 300-second miss penalty; disabling the exact call map still left 15 failures outside the generic 504-test selection. This is a concrete cross-test side effect: a lambda call mutates global expression schema consumed by later tests.

The new guard compares the entire old/new lambda body AST before either reader fast path, admitting only changed `bool`, `int`, or `float` constant values of the same exact type. Call targets, attributes, operators, branches, arguments, and bindings must match. Unsupported body changes select all 1,620 tests even if the exact call map is absent. The adversarial edit now scores 36.817/0 with all 24 failures selected. Benign index/value edits retain their per-call selection, including the public Dremio change and independent BigQuery `LENGTH` and DuckDB `SHA256` changes. A fresh full-suite BigQuery `DATE_TRUNC` index mutation caused nine actual failures; all nine were selected among 266 tests, scoring 10.577/0. That helper mutates its fresh expression argument. An AST scan found no direct mutator call in the 247 pinned parser lambda sites with a numeric or boolean literal; indirect helper effects remain a residual risk.

The organizer scorer reports **179.161 simulated seconds/0 misses** on all 30 official samples, unchanged from parent `7cc5f9a`; the three prior fresh lambda changes remain 60.079/0. All 101 patches across 31 available independent corpora, including the adversarial label, scored zero misses, as did the separate `DATE_TRUNC` corpus. Missing and stale maps, injected side-effect calls, new names/scopes, import/setup calls, and multi-file changes passed explicit fallback checks. Four alternating host Python 3.12 sample runs measured median CPU 5.001 seconds on parent and 5.030 on this branch, a difference within host noise. The 16-file Docker context passed the allowlist check. Its exact payload emitted byte-identical sample output under the digest-verified Python 3.13 read-only Bubblewrap substitute at UID/GID 65534 with two CPUs, 4 GiB address cap, 64 MiB `/tmp`, and denied sockets, scoring 179.161/0. A real Docker build and organizer container CPU measurement remain unavailable.

## Scalar safety scan CPU refactor

On isolated parent `7cc5f9a`, cache the `_Dialect` AST parent relationships once per safety call and skip parsing a pristine dialect module for `__getattribute__`/`__getattr__` definitions when neither spelling occurs in its source. These are equivalent read-only checks. The official 30 output is byte-identical and scores 179.161/0. All 101 independent patches across 31 corpora also emitted byte-identical plans; the original 100 labels had zero misses, while a newly constructed global side-effect lambda mutation missed one patch in both this CPU branch and its parent. Three alternating Python 3.13 host runs per branch measured median selector CPU 4.375 seconds for the parent and 4.180 seconds for this refactor. The exact 16-file payload emitted byte-identical output in the digest-verified constrained Bubblewrap substitute and scored 179.161/0. A real Docker build and organizer CPU measurement remain unavailable. This CPU refactor is independent of the separate side-effect guard under investigation.

## Combined guarded release checkpoint

Applying the CPU refactor at `00180b7` after the literal-only safety guard at `14a1884` preserved byte-identical plans for the official 30 patches and all **102 patches across 32 independent corpora**. The organizer scorer reports **179.161 simulated seconds, zero misses** on the official sample and zero misses in every independent corpus. In particular, the full-suite-labeled cross-test side-effect mutation scores 36.817/0 after the guard, versus 310.577/1 before it; the separate nine-failure BigQuery `DATE_TRUNC` mutation scores 10.577/0. Three alternating host Python 3.13 runs measured median selector CPU **4.235 to 4.091 seconds** for the guarded parent and combined branch. The 16-file Docker context and structural fallback checks pass. The exact Docker payload emitted byte-identical official output in the digest-verified read-only Bubblewrap substitute at UID/GID 65534, two CPUs, 4 GiB address cap, 64 MiB `/tmp`, and denied sockets, scoring 179.161/0. This is not a real Docker build or organizer CPU measurement. `verified-179` at `fcc4b59` remains a measured fallback; the current guard addresses a concrete miss that fallback also admits for some lambda shapes.

## Per-patch pristine AST cache

The selector repeatedly parses the same pristine modules while checking one patch. This variant caches those read-only ASTs only for the duration of `select`; patched source is always parsed separately, and the cache is cleared in a `finally` block after every patch. Keeping the cache for the whole batch was rejected because retaining hundreds of trees increased garbage-collector scan time. The accepted version changes no safety predicate, map, selection, scheduler, or Docker input.

The official 30 output is byte-identical to `aa8b2aa` and scores **179.161 simulated seconds, zero misses**. All **102 independently labeled patches across 32 corpora** emitted byte-identical plans and scored zero misses, including the 24-failure cross-test side-effect label. Four alternating Python 3.13 host runs per version measured median selector CPU **4.262 to 3.934 seconds**. Structural lambda fallbacks and the 16-file Docker context passed. The exact payload emitted byte-identical output under the digest-verified read-only Bubblewrap substitute and scored 179.161/0. No real Docker build or organizer CPU measurement was available.

## Pristine parser-lambda reader index

The receiver-aware parser-table proof previously parsed and walked every pinned module containing `FUNCTIONS` for each qualifying patch. A reproducible builder now runs that same proof against the clean checkout and stores its 64 existing lambda sites in a 15 KiB compressed index. The payload is bound to the impact map, import-call map, exact test IDs, schema version, and an entry-list digest. Missing, truncated, stale, malformed, or unknown data runs the prior source scan. The index contains clean reader selections only; it has no patches or failure labels.

Official output is byte-identical to `d188e5a` and remains **179.161 simulated seconds, zero misses**. Every one of the **102 independent patches in 32 corpora** emitted a byte-identical plan and scored zero misses. Five alternating pinned-core Python 3.13 runs measured median selector CPU **4.345 to 3.736 seconds**. Deleting or truncating the index produced byte-identical output through the source-scan fallback, and two independent rebuilds were byte-identical. The Docker context contains 17 files and remains below the 20 MB repository limit. The exact payload emitted byte-identical official output under the digest-verified read-only Bubblewrap substitute and scored 179.161/0. No real Docker build or organizer CPU measurement was available.

## Pristine numeric-table safety index

The value-only `NUMERIC_ESCAPES` rule previously repeated a whole-source proof of metaclass, generator, tokenizer, constructor, and class-map behavior for every qualifying patch. A second reproducible clean-checkout index records the result for all nine existing nested Tokenizer tables in 516 compressed bytes. It is bound to the impact, class-use, import-constructor and process-pool maps, exact test IDs, schema version, and entry-list digest. Missing, truncated, stale, malformed, or unknown data repeats the original proof.

Official output remains byte-identical at **179.161 simulated seconds, zero misses**. All **102 independent patches across 32 corpora**, including the numeric mutations and cross-test side-effect label, emitted byte-identical plans and scored zero misses. Five alternating pinned-core Python 3.13 runs measured median selector CPU **3.493 to 3.080 seconds**. Missing and truncated index checks fell back byte-identically, and an independent rebuild matched exactly. The 18-file Docker context remains under 20 MB. A real Docker build and organizer CPU measurement were unavailable.

## Reuse scalar safety source proofs

The selector now reuses pristine ASTs in the scalar-read checks and caches the source-wide reflective-read proof across patches. The cached inputs are the pinned, unmodified SQLGlot source and coverage maps; patch-specific owner, field, and value checks still run for each patch. The `BYTE_STRING_ESCAPES` dictionary exception remains field-specific. No regression labels or patch identifiers are stored in the selector or image.

Against parent `1acbdec`, the official 30 plans were byte-identical and scored **179.161 simulated seconds, zero misses**. The 102 independently labeled patches across 32 corpora were also byte-identical and had zero misses. Seven alternating, pinned-core Python 3.13 runs measured median host selector CPU **3.033 to 2.952 seconds**, a 0.081-second reduction; the paired median reduction was 0.066 seconds. An AST-reuse-only prototype changed the median by just 0.003 seconds and was not promoted separately.

The Docker context checker found all 18 `COPY` inputs. The copied payload emitted byte-identical official plans inside the digest-verified Python 3.13 base filesystem with a read-only application mount, UID/GID 65534, two CPU affinity, and a 4 GiB address-space cap. The local Bubblewrap network namespace failed to initialize, so this latest substitute run did not enforce network isolation or a 64 MiB temporary-filesystem size. No real Docker build or organizer container CPU measurement was available. The previous release remains the verified fallback.

## Fresh scalar regression labels

Two new value-only class-field edits were labeled by running the complete pinned SQLGlot suite on separate pristine checkout copies. Oracle's `LOCKING_READS_SUPPORTED = True` to `False` produced no failing tests in 116.886 host seconds. Snowflake's `TRY_CAST_REQUIRES_STRING = True` to `False` produced one failing test, `TestSnowflake.test_try_cast`, in 118.356 host seconds. The verified selector commit `3b877a0` selected 58 and 408 tests respectively, including that failure. The official scorer reports **16.757 simulated seconds and zero misses** across the two fresh cases. These labels remain outside the selector and Docker image. This experiment adds no selection rule; the official 30-sample checkpoint remains 179.161/0.

## Fresh parser lambda regression labels

Four more parser dispatch edits were labeled with separate complete pinned-suite runs. An Exasol `HASH_SHA256` lambda changed the length literal from 256 to 128 and caused one failure; an Exasol `DATE_TRUNC` lambda changed its `this` argument index from 1 to 0 and caused one failure. Before labels were available, the selector chose 78 tests for each. The official scorer reports **4.146 simulated seconds and zero misses** for each case. Their labeling runs took 106.290 and 103.911 host seconds.

A Snowflake `TRY_TO_BOOLEAN` lambda changed `safe=True` to `safe=False` and caused one failure; a Presto `BITWISE_NOT` lambda changed its argument index from 0 to 1 and caused three failures. Both edits selected the full 1,620-test suite through existing guards, scoring 73.634 simulated seconds together with zero misses. Their labeling runs took 107.794 and 108.447 host seconds. These four new labels remain outside the selector and Docker image. The verified code commit is still `3b877a0`, and the official 30-sample result is still 179.161/0.

## Fresh process-pool optimizer regression

Two independent edits to the existing `_distribute` body in `sqlglot/optimizer/normalize.py` were labeled with complete pinned-suite runs. Changing its final `copy=False` to `copy=True` caused no test failures in 107.161 host seconds. Changing the first `b.left` input in the final `to_func` call to `b.right` caused two failures in 103.742 host seconds: `TestOptimizer.test_normalize` and `TestOptimizer.test_tpcds`. Before either label, the selector chose the same 12 tests on its clean coverage map, including both failing tests. Each plan scored **25.454 simulated seconds and zero misses** with the official scorer. The TPCDS failure exercises the spawned optimizer work and its mapped test context. Labels remain outside the selector and Docker image; the official 30-sample checkpoint remains 179.161/0.

## Constrained payload recheck

The 18 Docker `COPY` inputs were recopied from local main `944097a` into a read-only Bubblewrap application mount over the previously digest-verified Python 3.13 base filesystem. The process ran as UID/GID 65534 with affinity restricted to two CPUs, a 4 GiB address-space limit, a 256-process limit, and a 64 MiB `/tmp` tmpfs. A libseccomp filter denied socket, socketpair, connect, bind, listen, and accept calls; a separate probe confirmed `socket.socket()` fails with `EPERM` under the same filter. The payload's official 30-sample output was byte-identical to the host output and scored **179.161 simulated seconds with zero misses**. This is a stronger local substitute for the earlier check, but Docker Engine was unavailable, so an actual `docker build` and organizer container CPU score remain unverified.

## Batch cyclic-GC reduction

Starting from `d68cf4a`, the selector disables Python's cyclic garbage collector during batch planning and explicitly collects after every 32 patches. This changes no selection rule, map, scheduler, or output; periodic collection bounds accumulated cycles on larger inputs. On the official 30 patches, the organizer scorer reported **179.161 simulated seconds and zero misses**, and the output was byte-identical to the parent. Seven alternating, pinned-core Python 3.13 runs measured median selector CPU **3.088 to 2.777 seconds**; every paired run favored the candidate. This 0.311-second host reduction is not a measured organizer container score.

All **113 independently full-suite-labeled patches across 40 corpora** emitted byte-identical plans and had zero misses. A separate 50-patch stress batch was also byte-identical; peak child RSS was 279,228 KiB on the parent and 280,868 KiB on the candidate. The Docker context checker found all 18 `COPY` inputs. The exact copied payload emitted byte-identical official plans under the digest-verified Python 3.13 read-only Bubblewrap substitute at UID/GID 65534, two CPUs, 4 GiB address-space cap, 256-process cap, 64 MiB `/tmp`, and denied sockets; the official scorer reported 179.161/0. Docker Engine was unavailable, so no real `docker build` or organizer CPU measurement was performed.

## Pinned process-pool proof cache

From `4e3ba09`, memoize the process-pool argument proof that reads only the pinned, unmodified test sources. Reuse the existing per-patch pristine AST cache for its two source parses. The proof and every selection condition are unchanged. The official 30-patch output is byte-identical and scores **179.161 simulated seconds with zero misses**. All **113 independently labeled patches across 40 corpora** emitted byte-identical output with zero misses.

Seven alternating pinned-core Python 3.13 runs measured median CPU **2.643 to 2.534 seconds**. A fresh nine-pair run measured **2.639 to 2.562 seconds**, with a 0.112-second median paired reduction. The modest host CPU gain is not a measured organizer container score. All 18 Docker `COPY` inputs passed the context checker, and the exact copied payload emitted byte-identical official output under the digest-verified Python 3.13 constrained Bubblewrap substitute, scoring 179.161/0. Docker Engine remained unavailable.

## Rejected batch-wide AST cache

An isolated branch (`batch-tree-cache`, commit `a65cf40`) retained pristine ASTs for the whole input batch instead of clearing them after each patch. The official 30-patch output remained byte-identical and scored **179.161 simulated seconds with zero misses**; a separate 50-patch stress output was also byte-identical. Seven alternating pinned-core Python 3.13 runs measured median CPU **2.645 to 2.602 seconds**, only a 0.043-second difference amid run-to-run noise. Peak child RSS on the 50-patch batch rose from **280,352 to 355,836 KiB**. This variant was rejected before the independent regression gate because its small, uncertain CPU gain did not justify retaining roughly 75 MiB more ASTs. No selector change was promoted.

## Rejected pristine body-shape index

Isolated `shape-index` commit `0d946bb` replaces repeat parsing of clean SQLGlot function shapes with an impact-map-bound compressed index, falling back to source parsing when absent or stale. This is a CPU-only prototype; it does not change the source proof or selection rule. A full 184-file index occupied 936 KiB and kept the official 30-patch plans byte-identical at **179.161 simulated seconds/0 misses**. Seven alternating pinned-core runs measured median CPU **2.508 to 2.459 seconds**, a 0.049-second gain. Restricting the index to all pristine SQLGlot modules of at least 20,000 source characters reduced it to 688 KiB but measured **2.492 to 2.543 seconds** in another seven-pair run. The added payload and complexity did not produce a repeatable material CPU gain, so the branch was rejected before the independent corpus gate. Main retains the verified selector and its 113/0 independent checkpoint.

## Fresh spawned-worker regression labels

Two new patches were prepared against separate copies of the pinned, unmodified SQLGlot checkout, with selection fixed before labeling. Each label came from a complete pinned-suite run and remains outside the selector and Docker image. Raising after the docstring of `projection_reachability` in `sqlglot/optimizer/pushdown_projections.py` produced **94 failing test IDs**, including both executor and optimizer TPCDS tests, in 83.285 host seconds. The current selector chose 99 tests and the official scorer reported **25.454 simulated seconds/0 misses**; this equals the failing-tests-only scheduled cost for that case. Raising in `PythonExecutor.scan_table` in `sqlglot/executor/python.py` produced **48 failing IDs**, including executor TPCDS, in 87.962 host seconds. The selector chose 54 tests and scored **25.099/0**, versus a 24.592-second failing-tests-only cost. The independent corpus now totals **115 patches across 42 corpora with zero misses**. The selector code and official 30-sample checkpoint remain unchanged at 179.161/0.

## Equivalent AST traversal with lower CPU cost

From `50fdbc2`, replace the 47 `ast.walk` call sites in the selector's proof code with a breadth-first walker that visits `_fields` directly while preserving the standard traversal order. An independent identity-by-identity comparison of both walkers over all 250 pinned Python source ASTs found identical node sequences. No selection predicate, map, scheduler, or Docker input changed.

The official 30-patch plans were byte-identical and the organizer scorer reported **179.161 simulated seconds/0 misses**. All **115 independently full-suite-labeled patches across 42 corpora** emitted byte-identical plans and had zero misses, including both new spawned-worker regressions. Structural header, mixed-comment, and relocation guards passed. Nine alternating pinned-core Python 3.13 runs measured median host selector CPU **2.500 to 2.363 seconds**, with a 0.163-second median paired reduction; every pair favored the new walker. This is a host CPU observation, not an organizer container measurement. The 18-file Docker context passed, and the exact copied payload emitted byte-identical official output under the digest-verified read-only Python 3.13 Bubblewrap substitute, scoring 179.161/0. Docker Engine remained unavailable.
