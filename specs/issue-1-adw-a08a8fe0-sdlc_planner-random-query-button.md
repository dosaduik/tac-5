# Feature: Random Natural Language Query Button

## Feature Description
Add a "Random Query" button to the query section of the Natural Language SQL Interface. When clicked, the button asks the backend to generate an interesting, valid natural language question about the data currently loaded in the database (based on the existing tables and their column structures), and populates the query input field with that generated text — always overwriting whatever is currently in the field. The user can then review, edit, or immediately execute the suggested query using the existing "Query" button/flow. Generation is powered by the LLM routing logic already implemented in `core/llm_processor.py`, and the generated query is capped at two sentences.

## User Story
As a user exploring a newly uploaded dataset
I want to click a button that suggests an interesting natural language question about my data
So that I can quickly discover useful queries without having to think of one myself or already know the schema

## Problem Statement
Once a user uploads data, they are presented with a blank query input and must come up with their own natural language question from scratch. New users, or users unfamiliar with the shape of the uploaded data, don't know what kinds of questions are interesting or even valid against the current schema. There is no guided or inspirational entry point into the query experience.

## Solution Statement
Introduce a new backend endpoint that uses the existing schema introspection (`get_database_schema`) plus the existing LLM routing pattern in `core/llm_processor.py` to generate a short (max two sentences), interesting natural language query tailored to the tables and columns currently in the database. Add a new "Random Query" button to the frontend, styled like the existing "Upload Data" button (`.secondary-button`) but visually separated from the primary Query/Upload Data button group (placed on the opposite side of the control row using `justify-content: space-between`). Clicking the button calls the new endpoint and always overwrites the contents of the query textarea with the generated text, ready for the user to run or edit.

## Relevant Files
Use these files to implement the feature:

- `app/server/core/llm_processor.py` - Contains the existing `generate_sql_with_openai`, `generate_sql_with_anthropic`, `format_schema_for_prompt`, and `generate_sql` routing function. The new random-query generation functions must follow the exact same structure/pattern (provider-specific functions + a routing function that prioritizes OpenAI key > Anthropic key > request preference).
- `app/server/core/data_models.py` - Contains all Pydantic request/response models (e.g. `QueryRequest`/`QueryResponse`). Add new `GenerateQueryRequest`/`GenerateQueryResponse` models here following the existing style (e.g. `HealthCheckResponse`, `QueryResponse` with optional `error` field).
- `app/server/core/sql_processor.py` - Contains `get_database_schema()`, which is the schema introspection function already used by `/api/query` and `/api/schema`. Reuse this to build the schema context passed into the new LLM generation functions.
- `app/server/server.py` - FastAPI app with all route handlers (`/api/upload`, `/api/query`, `/api/schema`, `/api/insights`, `/api/health`, `/api/table/{table_name}`). Add a new `POST /api/generate-query` endpoint here following the exact try/except/logging pattern used by the other endpoints.
- `app/server/tests/core/test_llm_processor.py` - Existing unit test suite for `llm_processor.py`, using `unittest.mock.patch` on the `OpenAI`/`Anthropic` classes. Add new test cases for the random-query generation functions following the same mocking patterns.
- `app/client/src/types.d.ts` - TypeScript interfaces that must mirror the Pydantic models exactly (per the file's own header comment). Add `GenerateQueryRequest`/`GenerateQueryResponse` interfaces here.
- `app/client/src/api/client.ts` - Frontend API client wrapping `fetch` calls to the backend. Add a `generateRandomQuery()` method following the existing `processQuery`/`getSchema` patterns.
- `app/client/index.html` - Contains the `.query-controls` div with the `#query-button` (`.primary-button`) and `#upload-data-button` (`.secondary-button`). Add the new `#random-query-button` here, using `.secondary-button` style, restructured so it is justified apart from the existing buttons.
- `app/client/src/main.ts` - Contains `initializeQueryInput()` and `initializeFileUpload()` which wire up DOM event listeners. Add a new `initializeRandomQueryButton()` (or extend `initializeQueryInput()`) to wire up the new button's click handler, call the API, and overwrite `queryInput.value`.
- `app/client/src/style.css` - Contains `.query-controls` (currently `display: flex; gap: 1rem;`) and the `.primary-button`/`.secondary-button`/`.toggle-button` shared button styles. Update `.query-controls` layout (or introduce a wrapper) so the new button is justified apart from the existing button group.
- `.claude/commands/test_e2e.md` - Read this to understand how to run/structure an E2E test file for this project.
- `.claude/commands/e2e/test_basic_query.md` - Read this as the reference example for E2E test file structure (User Story, Test Steps with screenshots, Success Criteria).
- `.claude/commands/e2e/test_complex_query.md` - Read this as a second reference example for E2E test file structure.

### New Files
- `app/server/tests/core/test_llm_processor.py` - (existing file, extended) add tests for the new random query generation functions.
- `.claude/commands/e2e/test_random_query.md` - New E2E test file validating the Random Query button end-to-end (generation + overwrite behavior), modeled after `test_basic_query.md` and `test_complex_query.md`.

## Implementation Plan
### Phase 1: Foundation
Add the new Pydantic request/response models (`GenerateQueryRequest`, `GenerateQueryResponse`) to `core/data_models.py`, mirrored exactly in `app/client/src/types.d.ts`. These models define the contract for the new feature: an optional `table_name` to focus generation on a specific table (defaulting to using the whole schema), and a response containing the generated natural language `query` string plus an optional `error`.

### Phase 2: Core Implementation
Implement the query-generation logic in `core/llm_processor.py`, mirroring the exact structure of `generate_sql_with_openai` / `generate_sql_with_anthropic` / `generate_sql`:
- `generate_random_query_with_openai(schema_info)` — prompts OpenAI to produce one interesting natural language question (max two sentences) about the given schema, returns cleaned text.
- `generate_random_query_with_anthropic(schema_info)` — same but for Anthropic.
- `generate_random_query(schema_info, llm_provider)` — routes using the same priority order as `generate_sql` (OpenAI key present > Anthropic key present > request-preferred provider).
Reuse `format_schema_for_prompt(schema_info)` to build the schema context for the prompt so the LLM knows the real table/column names it must reference.

Add the `POST /api/generate-query` endpoint to `server.py`: fetch `schema_info` via `get_database_schema()`, guard against an empty database (return a helpful `error` if there are no tables), call `generate_random_query(...)`, and return a `GenerateQueryResponse`. Follow the same try/except + `logger.info`/`logger.error` + traceback logging pattern used by every other endpoint in this file.

### Phase 3: Integration
Wire up the frontend:
- Add `#random-query-button` to `index.html` inside `.query-controls`, styled with `.secondary-button` (matching the "Upload Data" button style per the feature request), but structurally separated (e.g. wrap `#query-button` + `#upload-data-button` in a left-aligned group and place `#random-query-button` in a right-aligned group) so `.query-controls` uses `justify-content: space-between` to visually justify it apart from the primary action buttons.
- Add `generateRandomQuery()` to `api/client.ts` calling `POST /api/generate-query`.
- Add a click handler in `main.ts` that disables the button, shows a loading state (matching the existing `queryButton` loading-state pattern), calls the API, and on success **always overwrites** `queryInput.value` with the returned `query` (per the explicit requirement to always overwrite what's in the field), then re-enables the button. On error, reuse the existing `displayError()` helper.
- Create the E2E test file `.claude/commands/e2e/test_random_query.md`.

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

### Add backend request/response models
- In `app/server/core/data_models.py`, add `GenerateQueryRequest` (fields: `llm_provider: Literal["openai", "anthropic"] = "openai"`, `table_name: Optional[str] = None`) and `GenerateQueryResponse` (fields: `query: str`, `error: Optional[str] = None`), following the existing style of `QueryRequest`/`QueryResponse`.

### Implement LLM query-generation logic
- In `app/server/core/llm_processor.py`, add `generate_random_query_with_openai(schema_info: Dict[str, Any]) -> str` that builds a prompt (using `format_schema_for_prompt`) instructing the model to produce exactly one interesting, schema-grounded natural language question, in at most two sentences, with no explanation/preamble, and returns the cleaned text (strip markdown/quotes similar to the existing SQL cleanup logic).
- Add `generate_random_query_with_anthropic(schema_info: Dict[str, Any]) -> str` with the equivalent Anthropic implementation.
- Add `generate_random_query(schema_info: Dict[str, Any], llm_provider: str = "openai") -> str` that routes using the same priority logic as `generate_sql` (OpenAI key present → OpenAI; else Anthropic key present → Anthropic; else fall back to `llm_provider`).
- Add unit tests to `app/server/tests/core/test_llm_processor.py` covering: successful OpenAI generation, successful Anthropic generation, markdown/quote cleanup, missing API key error, API error propagation, and provider routing priority — mirroring the existing test patterns for `generate_sql_with_openai`/`generate_sql_with_anthropic`/`generate_sql`.

### Add the backend endpoint
- In `app/server/server.py`, import the new model classes and `generate_random_query`.
- Add `POST /api/generate-query` with `response_model=GenerateQueryResponse`: call `get_database_schema()`; if there are no tables, return a `GenerateQueryResponse` with `query=""` and an `error` message (e.g. "No tables available. Upload data first."); otherwise call `generate_random_query(schema_info, request.llm_provider)` and return the result. Wrap in try/except with `logger.info`/`logger.error` + traceback, matching the other endpoints exactly.
- Add/extend server tests (if an existing `tests/test_server.py`-style file exists for endpoints; otherwise add coverage alongside the `llm_processor` tests) to verify the endpoint returns a query string when tables exist and an error when the database is empty.

### Mirror types on the frontend
- In `app/client/src/types.d.ts`, add `GenerateQueryRequest` and `GenerateQueryResponse` interfaces that exactly match the new Pydantic models.
- In `app/client/src/api/client.ts`, add `generateRandomQuery(request?: GenerateQueryRequest): Promise<GenerateQueryResponse>` performing a `POST` to `/generate-query` with a JSON body (default `{ llm_provider: 'openai' }` if none provided), following the existing `processQuery` method pattern.

### Update the UI markup and styles
- In `app/client/index.html`, restructure `.query-controls` so `#query-button` and `#upload-data-button` are grouped together (e.g. in a `.query-controls-primary` wrapper div) and add a new `#random-query-button` (text: "Random Query", class `secondary-button`) in a separate wrapper (e.g. `.query-controls-secondary`) placed after it, so the two groups can be justified apart.
- In `app/client/src/style.css`, update `.query-controls` to `justify-content: space-between` (it is already `display: flex`) so the new secondary wrapper is pushed to the opposite side of the primary button group; add any minor wrapper styles needed (e.g. `display: flex; gap: 1rem;` on the new wrapper classes) so existing button spacing is preserved within each group.

### Wire up the button behavior
- In `app/client/src/main.ts`, add a new `initializeRandomQueryButton()` function (called from the `DOMContentLoaded` listener alongside `initializeQueryInput()`, etc.) that: looks up `#random-query-button` and `#query-input`; on click, disables the button and shows a loading state (reuse the same `loading` span pattern used by `queryButton`); calls `api.generateRandomQuery()`; on success, **always overwrites** `queryInput.value` with `response.query` (even if the field already has text) or calls `displayError(response.error)` if an error is present; on failure, calls `displayError(...)`; finally re-enables the button and restores its label ("Random Query").

### Create the E2E test file
- Read `.claude/commands/test_e2e.md` and `.claude/commands/e2e/test_basic_query.md` to understand the E2E test file conventions used in this project.
- Create `.claude/commands/e2e/test_random_query.md` following the same structure (User Story, numbered Test Steps with screenshots, Success Criteria). The test should: navigate to the app, ensure at least one table exists (load sample data if needed), type some placeholder text into the query input, click "Random Query", verify the query input's value changed to a non-empty generated question (and is no longer the placeholder text that was typed), verify the generated text does not exceed two sentences, and take screenshots before/after clicking.

### Validate the full feature
- Run the validation commands below to confirm the feature works end-to-end with zero regressions.

## Testing Strategy
### Unit Tests
- `generate_random_query_with_openai` / `generate_random_query_with_anthropic`: successful generation, markdown/quote stripping, missing-API-key error, upstream API error propagation.
- `generate_random_query`: provider routing priority (OpenAI key present, Anthropic-only, neither key present falls back to request preference) — mirrors the existing `generate_sql` routing tests.
- `POST /api/generate-query` endpoint: returns a populated `query` when tables exist (with LLM calls mocked), returns a descriptive `error` and empty `query` when the database has zero tables.

### Edge Cases
- Empty database (no tables uploaded yet) — endpoint should return a friendly error rather than calling the LLM or crashing.
- LLM returns a query longer than two sentences — prompt instructs a two-sentence maximum, but frontend/backend should not crash if the model doesn't perfectly comply (no hard truncation required, just document the expectation in the prompt).
- Neither `OPENAI_API_KEY` nor `ANTHROPIC_API_KEY` set — should raise/propagate a clear error that the frontend surfaces via `displayError`.
- User has already typed text into the query input before clicking "Random Query" — clicking must always overwrite the existing text, never append or prompt for confirmation.
- Clicking "Random Query" multiple times in a row — each click should independently overwrite the field with a freshly generated query and the button should be disabled during the in-flight request to prevent duplicate submissions.

## Acceptance Criteria
- A new "Random Query" button is visible in the query section, styled like the "Upload Data" button, and visually separated (justified apart) from the "Query"/"Upload Data" button group.
- Clicking "Random Query" calls a new backend endpoint that uses `core/llm_processor.py` (via the same OpenAI/Anthropic routing pattern as `generate_sql`) to produce a natural language question grounded in the actual tables/columns currently in the database.
- The generated query is at most two sentences.
- Clicking "Random Query" always overwrites the current contents of the query input field, regardless of what was previously there.
- If no tables exist in the database, the feature surfaces a clear error instead of crashing or calling the LLM with an empty schema.
- All existing tests continue to pass with zero regressions.
- New unit tests cover the new `llm_processor.py` functions and the new endpoint.
- A new E2E test file validates the button's behavior end-to-end.

## Validation Commands
Execute every command to validate the feature works correctly with zero regressions.

- `cd app/server && uv run pytest` - Run server tests to validate the feature works with zero regressions
- `cd app/client && bun tsc --noEmit` - Run frontend tests to validate the feature works with zero regressions
- `cd app/client && bun run build` - Run frontend build to validate the feature works with zero regressions
- Read `.claude/commands/test_e2e.md`, then read and execute the new `.claude/commands/e2e/test_random_query.md` test file to validate this functionality works end-to-end.

## Notes
- No new third-party libraries are required — `openai` and `anthropic` SDKs are already dependencies used by `core/llm_processor.py`.
- Follow the existing convention of prioritizing the OpenAI API key over Anthropic when both are present, consistent with `generate_sql`'s routing logic, so behavior is predictable and consistent across both LLM-powered features.
- Consider in a future iteration allowing the user to scope random query generation to a specific table (the `table_name` field is included in `GenerateQueryRequest` for forward compatibility) via a dropdown, but this is out of scope for this feature — the initial implementation can generate a query against the full schema.
