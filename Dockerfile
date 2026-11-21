# The scorer builds this on linux/amd64 and runs it with no network. The
# digest is the image we labeled every commit in: its Python and SQLite
# decide which sqlglot tests run, so keep it if your image runs them.
FROM python:3.13-slim@sha256:e48f59cdba69a3cbd9ed2cf0f348d90d45a8d350d98134cf1070bc106ee9ed90
COPY selector.py impact.py impact.json.gz class-uses.json.gz class-import-reads.json class-import-constructors.json parser-lambda-import-calls.json parser-lambda-key-calls.json.gz parser-lambda-reader-index.json.gz pool-classes.json.gz numeric-key-uses.json.gz numeric-safety-index.json.gz scalar-reads.json.gz reference-index.json.gz comment-source-reads.json fixture-reads.json fixture-shared.json LICENSE.sqlglot /app/
CMD ["python", "/app/selector.py"]
