# Feature: Random Natural Language Query Button

## Feature Description
Add a "Random Query" button to the query section of the Natural Language SQL Interface. When clicked, it calls the backend, which uses the LLM processor to inspect the current database schema (tables, columns, and types) and generate an interesting, LLM-crafted natural language question (max two sentences) that could be asked of the existing data. The generated query text always overwrites whatever is currently in the query input textarea, giving users a fast way to discover useful questions to ask about their uploaded data without having to write one themselves.

## User Story
As a user of the Natural Language SQL Interface
I want to click a button that generates a random, relevant natural language question based on my uploaded tables
So that I can quickly explore my data without having to think of a query myself

## Problem Statement
Users who upload data may not know what interesting questions to ask about it, especially when tables have many columns or non-obvious relationships. There is currently no way to get inspiration for a query — users must manually compose natural language questions from scratch, which creates friction for new or unsure users and reduces feature discoverability (e.g., users may not realize the app supports multi-table joins, aggregations, or date filtering).

## Solution Statement
Add a new backend endpoint that reuses the existing `get_database_schema()` schema introspection and a new `llm_processor.py` function to ask the configured LLM (OpenAI or Anthropic, following the exact same provider-routing logic already used for SQL generation) to produce one interesting natural language question (limited to two sentences) grounded in the real tables/columns/row-counts available. On the frontend, add a "Random Query" button — styled like the existing "Upload Data" secondary button — placed with clear visual separation (justified apart, via `justify-content: space-between`) from the primary "Query"/"Upload Data" button group. Clicking it calls the new endpoint and always overwrites the contents of the query textarea with the returned question, ready for the user to review and run manually (it does not auto-submit).

## Relevant Files
Use these files to implement the feature:

- `app/server/server.py` - FastAPI app with all route handlers (`/api/query`, `/api/schema`, etc.); add the new `GET /api/random-query` endpoint here, following the exact same try/except/logging pattern as the other endpoints.
- `app/server/core/data_models.py` - Pydantic request/response models; add a new `RandomQueryResponse` model here, following the pattern of `QueryResponse`/`DatabaseSchemaResponse`.
- `app/server/core/llm_processor.py` - Contains `generate_sql_with_openai`, `generate_sql_with_anthropic`, `generate_sql` (provider routing), and `format_schema_for_prompt`. Add parallel functions `generate_random_query_with_openai`, `generate_random_query_with_anthropic`, and `generate_random_natural_language_query` here, reusing `format_schema_for_prompt` for consistency and the exact same "OpenAI key present → OpenAI, else Anthropic key present → Anthropic, else provider preference" routing logic as `generate_sql`.
- `app/server/core/sql_processor.py` - Contains `get_database_schema()`, already used by `/api/query` and `/api/schema`; reuse this directly (no changes needed) to fetch schema info for the random query prompt.
- `app/client/index.html` - Contains the `.query-controls` div with the `Query` (`primary-button`) and `Upload Data` (`secondary-button`) buttons; add the new `Random Query` button here, styled with `secondary-button` (matching Upload Data), inside a layout that separates it from the other two buttons.
- `app/client/src/style.css` - Contains `.query-controls` (currently `display: flex; gap: 1rem`) and the `.primary-button`/`.secondary-button` styles; update `.query-controls` to `justify-content: space-between` and add a small wrapper class to keep Query + Upload Data grouped together on one side while Random Query sits apart on the other.
- `app/client/src/main.ts` - Contains `initializeQueryInput()`, `initializeFileUpload()`, `initializeModal()`, `displayError()`; add a new `initializeRandomQuery()` function (called from the `DOMContentLoaded` listener) that wires the new button's click handler, shows a loading state, calls the API, and always overwrites `queryInput.value` with the result (or calls `displayError` on failure).
- `app/client/src/api/client.ts` - Contains the `api` object with `uploadFile`, `processQuery`, `getSchema`, `generateInsights`, `healthCheck`; add a new `generateRandomQuery()` method that calls `GET /random-query`.
- `app/client/src/types.d.ts` - Contains TypeScript interfaces mirroring the Pydantic models; add a `RandomQueryResponse` interface mirroring the new `RandomQueryResponse` Pydantic model.
- `app/server/tests/test_sql_injection.py` - Existing test file showing the project's test conventions (uses `unittest.mock.patch`/`MagicMock` to mock `sqlite3.connect`, and direct function-level testing of `core.*` modules); use this as the pattern reference for new unit tests, though a new test file should be created rather than editing this one.
- `.claude/commands/test_e2e.md` - Read this to understand how E2E tests are structured and executed (via Playwright MCP), including the screenshot directory convention and output format.
- `.claude/commands/e2e/test_basic_query.md` - Read this as the reference example for writing the new E2E test file for this feature (structure: User Story, Test Steps with numbered **Verify** steps and screenshots, Success Criteria).

### New Files
- `app/server/tests/test_random_query.py` - Unit tests for the new `generate_random_natural_language_query` routing logic, schema-based prompt formatting, and the `/api/random-query` endpoint (including the "no tables" edge case), following the mocking conventions in `test_sql_injection.py`.
- `.claude/commands/e2e/test_random_query_button.md` - New E2E test file validating the Random Query button: it is visible and styled apart from the primary buttons, clicking it populates the query input with a non-empty, two-sentence-or-fewer question, and repeated clicks always overwrite the field.

## Implementation Plan
### Phase 1: Foundation
Add the new Pydantic response model (`RandomQueryResponse`) and the new LLM processor functions (`generate_random_query_with_openai`, `generate_random_query_with_anthropic`, `generate_random_natural_language_query`) that generate a natural-language question (not SQL) from schema info, reusing the existing `format_schema_for_prompt` helper and provider-routing pattern from `generate_sql`.

### Phase 2: Core Implementation
Wire up the new `GET /api/random-query` FastAPI endpoint in `server.py`: fetch the schema via `get_database_schema()`, short-circuit with a friendly error if there are no tables, call `generate_random_natural_language_query(schema_info)`, and return a `RandomQueryResponse`. Add unit tests covering the routing logic and the endpoint's success/empty-schema/error paths.

### Phase 3: Integration
Update the frontend: add the `Random Query` button to `index.html` (styled like `Upload Data`, visually separated from the primary button group via updated `.query-controls` CSS), add the `generateRandomQuery()` API client method and `RandomQueryResponse` type, and wire up the click handler in `main.ts` to always overwrite the query textarea with the returned question (with loading state and error handling matching the existing `Query`/`Upload Data` button patterns). Create the E2E test file and run it to validate the full flow visually.

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

### 1. Add `RandomQueryResponse` model
- In `app/server/core/data_models.py`, add a `RandomQueryResponse(BaseModel)` with `query: str` and `error: Optional[str] = None`, placed near the other Query Models for consistency.

### 2. Add random-query generation functions to `llm_processor.py`
- Add `generate_random_query_with_openai(schema_info: Dict[str, Any]) -> str` mirroring `generate_sql_with_openai`'s structure (API key lookup, `OpenAI` client, `format_schema_for_prompt`, markdown/code-fence stripping), but with a prompt instructing the model to produce ONE interesting, specific natural language question about the data (not SQL), grounded in real table/column names, limited to two sentences maximum, with no explanations or quotes.
- Add `generate_random_query_with_anthropic(schema_info: Dict[str, Any]) -> str` mirroring `generate_sql_with_anthropic` the same way, using the `claude-3-haiku-20240307` model for consistency with the existing SQL generation call.
- Add `generate_random_natural_language_query(schema_info: Dict[str, Any], llm_provider: str = "openai") -> str` that mirrors the routing logic in `generate_sql`: if `OPENAI_API_KEY` is set, use OpenAI; elif `ANTHROPIC_API_KEY` is set, use Anthropic; otherwise fall back to `llm_provider`.
- Raise a clear exception if `schema_info.get('tables')` is empty (no tables to base a question on) before calling the LLM, to avoid wasted API calls and a nonsensical prompt.

### 3. Add the `/api/random-query` endpoint
- In `app/server/server.py`, import `RandomQueryResponse` and `generate_random_natural_language_query`.
- Add `GET /api/random-query` returning `RandomQueryResponse`, following the same try/except/logging structure as `get_database_schema_endpoint`: fetch schema via `get_database_schema()`, raise a friendly error if there are no tables (e.g. `"No tables available. Upload data first to generate a random query."`), call `generate_random_natural_language_query(schema_info)`, log success, and return the response; on exception, log the error/traceback and return `RandomQueryResponse(query="", error=str(e))`.

### 4. Write backend unit tests
- Create `app/server/tests/test_random_query.py` following the `unittest.mock` conventions from `test_sql_injection.py`.
- Test `generate_random_natural_language_query` provider routing: mocks `os.environ.get` (or patches the underlying `generate_random_query_with_openai`/`_with_anthropic` functions) to verify OpenAI is preferred when its key is present, Anthropic is used when only its key is present, and the `llm_provider` fallback is respected when neither key is set.
- Test that `generate_random_natural_language_query` raises/returns an error when `schema_info['tables']` is empty.
- Test the `/api/random-query` endpoint via FastAPI's `TestClient`, mocking `core.sql_processor.get_database_schema` and `core.llm_processor.generate_random_natural_language_query` to verify: (a) success path returns a `query` string, (b) empty-schema path returns a populated `error` field and empty `query`.
- Run `cd app/server && uv run pytest` to confirm all tests (existing and new) pass.

### 5. Add `RandomQueryResponse` TypeScript type
- In `app/client/src/types.d.ts`, add `interface RandomQueryResponse { query: string; error?: string; }` near the other Query Types.

### 6. Add API client method
- In `app/client/src/api/client.ts`, add `generateRandomQuery(): Promise<RandomQueryResponse>` calling `apiRequest<RandomQueryResponse>('/random-query')` (GET, no body — same shape as `getSchema`).

### 7. Update `index.html` layout
- In `app/client/index.html`, inside `.query-controls`, wrap the existing `Query` and `Upload Data` buttons in a new inner `<div class="query-controls-primary">` group, and add a new sibling button `<button id="random-query-button" class="secondary-button">🎲 Random Query</button>` as the second child of `.query-controls`, so it sits apart from the primary group.

### 8. Update `style.css`
- Change `.query-controls` to use `justify-content: space-between` (keep `display: flex; align-items: center;`).
- Add a `.query-controls-primary { display: flex; gap: 1rem; align-items: center; }` rule to keep `Query` and `Upload Data` visually grouped on the left.

### 9. Wire up the button in `main.ts`
- Add a new `initializeRandomQuery()` function: gets `#random-query-button` and `#query-input`, adds a `click` listener that disables the button, shows a loading state (matching the `loading` span pattern used in `initializeQueryInput`), calls `api.generateRandomQuery()`, and on success **always overwrites** `queryInput.value` with `response.query` (even if the textarea already has content), or calls `displayError(response.error)` if `response.error` is set; wrap in try/catch calling `displayError` on thrown errors; restore button state in a `finally` block.
- Call `initializeRandomQuery()` from the `DOMContentLoaded` listener alongside the other `initialize*` calls.

### 10. Create the E2E test file
- Read `.claude/commands/test_e2e.md` and `.claude/commands/e2e/test_basic_query.md` to understand the required structure.
- Create `.claude/commands/e2e/test_random_query_button.md` with: a User Story, Test Steps (navigate to the app; verify the Random Query button is present and visually separated from Query/Upload Data; click it with at least one table present via sample data upload; verify the query input is populated with non-empty text; take a screenshot; click again and verify the field's contents change/are overwritten rather than appended to), and Success Criteria.

### 11. Manual verification and E2E run
- Start the app per `README.md` / `scripts/start.sh`, upload a sample dataset, click the Random Query button, and manually confirm the query field is overwritten with a relevant, concise (≤2 sentences) natural language question.
- Read `.claude/commands/test_e2e.md`, then execute `.claude/commands/e2e/test_random_query_button.md` using Playwright to validate the feature end-to-end, saving screenshots per the documented convention.

### 12. Final validation
- Run the full `Validation Commands` list below to confirm zero regressions.

## Testing Strategy
### Unit Tests
- `generate_random_natural_language_query` provider routing (OpenAI-key-present, Anthropic-key-present, neither-key-present fallback), matching the existing coverage style for `generate_sql`.
- `generate_random_natural_language_query` behavior when schema has no tables (should raise/produce a clear error rather than calling the LLM with an empty schema).
- `/api/random-query` endpoint: success path (mocked schema + mocked LLM call returns a query), empty-database path (returns `error`, empty `query`), and LLM-failure path (exception surfaced via `error` field, HTTP 200 with error payload — consistent with how `/api/query` and `/api/schema` handle failures).

### Edge Cases
- No tables uploaded yet: endpoint should return a clear, user-facing error instead of an LLM hallucination or crash.
- Neither `OPENAI_API_KEY` nor `ANTHROPIC_API_KEY` set: should behave the same as `/api/query`'s existing fallback behavior (attempts the default provider, surfaces the resulting `ValueError` as an `error` field).
- LLM returns a multi-paragraph or overly long response: prompt instructs a two-sentence maximum, but the frontend should still render it gracefully in the textarea regardless of length (textarea already supports multi-line/long text).
- Clicking Random Query repeatedly: each click must overwrite the field with a fresh value, not append to or leave stale text mixed with the new query.
- Clicking Random Query while the query input already has unsaved user-typed text: per the feature spec, always overwrite — no confirmation prompt.
- Many tables with many columns: `format_schema_for_prompt` already handles arbitrary schema size; verify the prompt remains within reasonable token limits (existing `max_tokens=500` cap on the SQL call is a reasonable reference point for the new call too).

## Acceptance Criteria
- A "Random Query" button is visible in the query section, styled identically to the "Upload Data" secondary button.
- The button is visually separated (justified apart) from the "Query" and "Upload Data" button group, not simply placed inline with the same spacing.
- Clicking the button, when at least one table exists in the database, populates the query input with an LLM-generated natural language question of two sentences or fewer that is grounded in the actual table/column names present in the database.
- Clicking the button always overwrites the current contents of the query input, regardless of what was previously there.
- Clicking the button does not automatically execute the query — the user must still click "Query" to run it.
- If no tables exist, the button surfaces a clear error message instead of crashing or producing a nonsensical query.
- All existing tests continue to pass with zero regressions.

## Validation Commands
Execute every command to validate the feature works correctly with zero regressions.

- `cd app/server && uv run pytest` - Run server tests (including new `test_random_query.py`) to validate the feature works with zero regressions
- `cd app/client && bun tsc --noEmit` - Run frontend type-checking to validate the new types/API method/DOM wiring compile with zero errors
- `cd app/client && bun run build` - Run frontend build to validate the feature works with zero regressions
- Read `.claude/commands/test_e2e.md`, then read and execute the new `.claude/commands/e2e/test_random_query_button.md` E2E test file (via Playwright) to validate this functionality works end-to-end, including screenshots proving the button's placement and the query field being overwritten.

## Notes
- No new third-party libraries are required; the feature reuses the existing `openai` and `anthropic` SDK clients already used by `llm_processor.py`.
- The endpoint is implemented as `GET /api/random-query` (no request body needed) since generation is driven entirely by the current database schema and environment-configured provider keys, consistent with how `GET /api/schema` requires no body. If future work wants to let users pick a specific `llm_provider` or topic hint from the UI, this can be extended to a `POST` with a small request body without breaking the existing contract (add fields as optional).
- The 🎲 emoji is a suggestion for the button label to make it visually distinct from Query/Upload Data at a glance — follow the existing emoji-in-copy convention seen elsewhere in the UI (e.g., `getTypeEmoji`, sample data buttons in the modal); this can be adjusted to match team preference.
