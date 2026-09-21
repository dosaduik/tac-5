# Feature: Random Natural Language Query Button

## Feature Description
Add a "Random Query" button to the Natural Language SQL Interface that generates an interesting, LLM-authored natural language question about the data currently loaded in the database (based on the actual tables and their column structures), and populates the query input field with that generated question. This gives users — especially first-time users who aren't sure what to ask — a one-click way to discover what kinds of questions they can ask their data, without having to think one up themselves.

## User Story
As a user of the Natural Language SQL Interface
I want to click a button that suggests a natural language query tailored to my currently loaded tables
So that I can quickly explore my data without having to come up with a question myself

## Problem Statement
Users who upload data (or load sample data) are presented with an empty query input and no guidance on what kinds of questions are answerable given their specific schema. This creates a "blank page" problem: users must already know their schema well enough to phrase a useful query. There's currently no discovery mechanism in the UI to help users understand the art of the possible for their data.

## Solution Statement
Introduce a new backend capability in `core/llm_processor.py` that sends the current database schema (table names, columns, and row counts — the same schema representation already used by `generate_sql`) to the configured LLM provider (OpenAI or Anthropic, using the same key-priority routing logic already used for SQL generation) and asks it to produce one interesting, specific, natural-language question (capped at two sentences) that references the real tables/columns. Expose this via a new `POST /api/random-query` endpoint, wire up a new "Random Query" button in the UI (styled like the existing "Upload Data" secondary button, visually separated/justified apart from the primary Query/Upload controls), and have it always overwrite the contents of the query input field with the freshly generated question.

## Relevant Files
Use these files to implement the feature:

- `app/server/core/llm_processor.py` — Contains `generate_sql_with_openai`, `generate_sql_with_anthropic`, `format_schema_for_prompt`, and the `generate_sql` routing function. The new random query generation functions must follow the exact same structural pattern (provider-specific functions + a router function that prioritizes: 1) OpenAI key present, 2) Anthropic key present, 3) request's `llm_provider` preference). Reuses `format_schema_for_prompt` to describe the schema to the LLM.
- `app/server/core/data_models.py` — Pydantic request/response models. Add `RandomQueryRequest` and `RandomQueryResponse` here, following the exact style of `QueryRequest`/`QueryResponse`.
- `app/server/core/sql_processor.py` — Contains `get_database_schema()`, which is the source of truth for what tables/columns exist. The new endpoint reuses this exact function (same as `/api/query` does) to fetch schema info before generating a random query.
- `app/server/server.py` — FastAPI app with all `/api/*` route handlers. Add a new `POST /api/random-query` endpoint here, following the try/except + logging + graceful-error-response pattern used by every other endpoint (e.g. `process_natural_language_query`).
- `app/server/tests/core/test_llm_processor.py` — Existing unit tests for `llm_processor.py`. Add new test classes/functions here for the new random-query generation functions, mirroring the existing `TestLLMProcessor` structure (mocked OpenAI/Anthropic clients, key-priority routing tests, no-API-key error tests).
- `app/server/tests/test_sql_injection.py` — Example of a top-level (non-`core/`) test file that exercises `server.py` endpoint-level behavior; use as a style reference for the new endpoint test file.
- `app/client/index.html` — Contains the `.query-controls` div with the `Query` (`primary-button`) and `Upload Data` (`secondary-button`) buttons. Add the new `Random Query` button here, in its own group so it can be visually justified apart from the existing buttons.
- `app/client/src/main.ts` — Contains `initializeQueryInput()` (wires the Query button) and `initializeFileUpload()`/`initializeModal()` (wire the Upload Data button and modal). Add a new `initializeRandomQuery()` function following the same loading-state/error-handling conventions as `initializeQueryInput()`.
- `app/client/src/api/client.ts` — Typed `api` object wrapping `apiRequest<T>()` calls to each backend endpoint. Add a `generateRandomQuery()` method here, following the exact pattern of `processQuery()`.
- `app/client/src/types.d.ts` — TypeScript interfaces that must mirror the Pydantic models exactly. Add `RandomQueryRequest`/`RandomQueryResponse` interfaces here matching the new Pydantic models.
- `app/client/src/style.css` — Contains `.query-controls` (flex row, `gap: 1rem`, `align-items: center`) and the `.primary-button`/`.secondary-button` styles. Update `.query-controls` layout so the new button group is justified apart from the existing Query/Upload Data group, without breaking existing button styling.
- `README.md` — Documents the API endpoints list and usage instructions. Add the new `POST /api/random-query` endpoint to the "API Endpoints" section and mention the new button under "Usage".
- `.claude/commands/e2e/test_basic_query.md` and `.claude/commands/test_e2e.md` — Read these to understand the required structure/conventions (User Story, Test Steps, Success Criteria, screenshot conventions) for authoring the new E2E test file.

### New Files
- `app/server/tests/test_random_query_endpoint.py` — Endpoint-level tests for `POST /api/random-query` using FastAPI's `TestClient`, covering the success path, the "no tables loaded" edge case, and error propagation.
- `.claude/commands/e2e/test_random_query_button.md` — New E2E test file (Playwright-driven) validating the Random Query button end-to-end: loading sample data, clicking the button, and verifying the query input is populated/overwritten with a generated question.

## Implementation Plan
### Phase 1: Foundation
Add the new Pydantic models (`RandomQueryRequest`, `RandomQueryResponse`) to `core/data_models.py` and their mirrored TypeScript interfaces in `types.d.ts`. These are pure data-shape additions with no behavior, and everything else in the feature depends on them.

### Phase 2: Core Implementation
Implement the LLM-facing logic in `core/llm_processor.py`: provider-specific random-query generators (`generate_random_query_with_openai`, `generate_random_query_with_anthropic`) that reuse `format_schema_for_prompt`, a two-sentence enforcement helper, and a `generate_random_query` router function mirroring `generate_sql`'s key-priority logic. Add unit tests for all of this. Then wire the new `POST /api/random-query` endpoint into `server.py`, handling the "no tables in database" edge case explicitly (don't call the LLM with an empty schema), and add endpoint-level tests.

### Phase 3: Integration
Wire the frontend: add the `Random Query` button markup to `index.html` (visually separated from the primary Query/Upload Data controls per the "justify apart" requirement, styled like the existing `secondary-button`/Upload Data button), add `generateRandomQuery()` to `api/client.ts`, and add `initializeRandomQuery()` to `main.ts` so clicking the button calls the new endpoint and always overwrites the `#query-input` textarea's value with the returned question (matching the "always overwrite" requirement). Update `style.css` so the new button group is justified apart from the existing controls. Author and run the new E2E test, then run the full validation suite.

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

### 1. Add backend data models
- In `app/server/core/data_models.py`, add `RandomQueryRequest(BaseModel)` with `llm_provider: Literal["openai", "anthropic"] = "openai"` (mirrors `QueryRequest`).
- Add `RandomQueryResponse(BaseModel)` with `query: str` and `error: Optional[str] = None` (mirrors `QueryResponse`'s error-field convention).

### 2. Add frontend TypeScript interfaces
- In `app/client/src/types.d.ts`, add `RandomQueryRequest` and `RandomQueryResponse` interfaces that exactly mirror the new Pydantic models (same field names/types/optionality), placed near the existing `QueryRequest`/`QueryResponse` interfaces.

### 3. Implement random query generation in `llm_processor.py`
- Add a private helper `_limit_to_two_sentences(text: str) -> str` that splits generated text on sentence-ending punctuation (`.`, `!`, `?`) and truncates to at most the first two sentences, re-appending the correct terminal punctuation. This acts as a safety net in case the LLM doesn't fully respect the prompt's instruction.
- Add `generate_random_query_with_openai(schema_info: Dict[str, Any]) -> str`, structurally mirroring `generate_sql_with_openai`: reads `OPENAI_API_KEY`, builds a prompt using `format_schema_for_prompt(schema_info)` that asks the model to "invent one interesting, specific question a user might ask about this data, referencing real table and column names where natural, in at most two sentences, with no explanations, no markdown, and no surrounding quotes", calls the OpenAI chat completions API, strips markdown fences the same way `generate_sql_with_openai` does, and pipes the result through `_limit_to_two_sentences`.
- Add `generate_random_query_with_anthropic(schema_info: Dict[str, Any]) -> str` mirroring `generate_sql_with_anthropic` in the same way.
- Add `generate_random_query(request: RandomQueryRequest, schema_info: Dict[str, Any]) -> str` that applies the exact same routing priority as `generate_sql`: 1) OpenAI key present → use OpenAI, 2) Anthropic key present → use Anthropic, 3) fall back to `request.llm_provider`.
- Import `RandomQueryRequest` in `llm_processor.py` alongside the existing `QueryRequest` import.

### 4. Add unit tests for the new `llm_processor.py` functions
- In `app/server/tests/core/test_llm_processor.py`, add tests for `generate_random_query_with_openai` and `generate_random_query_with_anthropic`: success case, no-API-key error case, API-error case — mirroring the existing `TestLLMProcessor` test methods for `generate_sql_with_openai`/`generate_sql_with_anthropic`.
- Add tests for `generate_random_query` covering the same routing-priority scenarios as the existing `test_generate_sql_*_priority`/`test_generate_sql_*_fallback` tests.
- Add tests for `_limit_to_two_sentences` covering: text with 1 sentence (unchanged), text with exactly 2 sentences (unchanged), text with 3+ sentences (truncated to 2), and text with no terminal punctuation (returned as-is).

### 5. Add the `POST /api/random-query` endpoint
- In `app/server/server.py`, import `RandomQueryRequest` and `RandomQueryResponse` from `core.data_models`, and `generate_random_query` from `core.llm_processor`.
- Add `@app.post("/api/random-query", response_model=RandomQueryResponse)` handler `generate_random_query_endpoint(request: RandomQueryRequest) -> RandomQueryResponse` that: fetches `schema_info = get_database_schema()`; if `schema_info.get('tables')` is empty, returns `RandomQueryResponse(query="", error="No tables available. Upload data to generate a query suggestion.")` without calling the LLM; otherwise calls `generate_random_query(request, schema_info)` and returns `RandomQueryResponse(query=<result>)`; wraps the LLM call in the same try/except + `logger.error` + traceback-logging pattern used by the other endpoints, returning `RandomQueryResponse(query="", error=str(e))` on failure.

### 6. Add endpoint-level tests
- Create `app/server/tests/test_random_query_endpoint.py` using FastAPI's `TestClient` (import `from fastapi.testclient import TestClient` and `from server import app`), following the structure of `tests/test_sql_injection.py`.
- Test: schema with no tables (mock `get_database_schema` to return `{'tables': {}}`) → response has `error` set and `query == ""`, and the LLM function is never called.
- Test: schema with tables (mock `get_database_schema` and `generate_random_query`) → response contains the mocked query text and `error is None`.
- Test: `generate_random_query` raising an exception → response has `error` set and a 200-style graceful `RandomQueryResponse` (matching how `/api/query` degrades on failure) rather than an unhandled 500.

### 7. Update the frontend API client
- In `app/client/src/api/client.ts`, add `generateRandomQuery(request: RandomQueryRequest): Promise<RandomQueryResponse>` to the exported `api` object, POSTing to `/random-query` with a JSON body, following the exact pattern of `processQuery()`.

### 8. Add the Random Query button to the UI
- In `app/client/index.html`, restructure the `.query-controls` div so the existing `Query` (`primary-button`) and `Upload Data` (`secondary-button`) buttons remain grouped together, and add a new `<button id="random-query-button" class="secondary-button">Random Query</button>` as a sibling group so it can be justified apart (e.g. wrap the existing two buttons in a `<div class="query-controls-left">` and place the new button directly in `.query-controls` alongside that wrapper).
- In `app/client/src/style.css`, update `.query-controls` to `justify-content: space-between;` and add a `.query-controls-left { display: flex; gap: 1rem; align-items: center; }` rule so the left-hand button group keeps its existing spacing while the Random Query button is pushed apart to the opposite side of the row.

### 9. Wire up the Random Query button behavior
- In `app/client/src/main.ts`, add `initializeRandomQuery()`, called from the `DOMContentLoaded` handler alongside the other `initialize*()` calls.
- On click: disable the button and show the same `<span class="loading"></span>` treatment used by `initializeQueryInput()`; call `api.generateRandomQuery({ llm_provider: 'openai' })`; on success, **always overwrite** `queryInput.value` with `response.query` (regardless of any existing content) if `response.error` is falsy, otherwise call `displayError(response.error)`; on thrown error, call `displayError(...)`; in `finally`, re-enable the button and restore its original label text ("Random Query").

### 10. Create the E2E test file
- Read `.claude/commands/test_e2e.md` and `.claude/commands/e2e/test_basic_query.md` to confirm the required structure and conventions.
- Create `.claude/commands/e2e/test_random_query_button.md` with a User Story, numbered Test Steps, and Success Criteria. Steps should: navigate to the app, take an initial screenshot, load the "Users Data" sample dataset (so a table exists), type placeholder text into the query input, click "Random Query", verify the query input's value changed (is non-empty and different from the placeholder text that was typed), take a screenshot showing the populated field, and verify no error message is displayed.

### 11. Update documentation
- In `README.md`, add `POST /api/random-query` to the "API Endpoints" list, and add a short note under "Usage" describing the new button (e.g., "Click 'Random Query' to have the AI suggest an interesting question based on your currently loaded tables — this will overwrite anything currently in the query box").

### 12. Run full validation
- Run every command in the `Validation Commands` section below and confirm they all pass with zero regressions, including executing the new E2E test via Playwright per `.claude/commands/test_e2e.md`.

## Testing Strategy
### Unit Tests
- `core/llm_processor.py`: new functions `generate_random_query_with_openai`, `generate_random_query_with_anthropic`, `generate_random_query`, and `_limit_to_two_sentences`, covering success, markdown-stripping, missing-API-key errors, upstream API errors, and provider routing priority (mirroring the existing `generate_sql*` test coverage).
- `server.py`: new `POST /api/random-query` endpoint via `TestClient`, covering the empty-schema edge case, the happy path, and graceful error handling.

### Edge Cases
- No tables exist in the database yet (fresh install / all tables deleted) — must not call the LLM and must return a clear, non-crashing error the UI can display.
- Neither `OPENAI_API_KEY` nor `ANTHROPIC_API_KEY` is set — should behave the same as `generate_sql`'s fallback-to-`request.llm_provider` behavior, and surface a clear error to the user if that provider call fails.
- LLM returns more than two sentences, or returns markdown/quotes/extra commentary despite prompt instructions — `_limit_to_two_sentences` and the existing markdown-stripping logic must normalize this before it reaches the UI.
- User has existing (possibly long, possibly manually-typed) text in the query input when they click Random Query — it must be fully overwritten, not appended to.
- Rapid repeated clicks on the Random Query button — the button must be disabled while a request is in flight (same convention as the Query button).
- Backend LLM call throws (network error, invalid key, rate limit) — the endpoint must return a `200` with `RandomQueryResponse.error` set rather than surfacing a raw `500`, consistent with every other endpoint in `server.py`.

## Acceptance Criteria
- A "Random Query" button is visible in the query section, styled like the existing "Upload Data" secondary button, and visually separated (justified apart) from the primary `Query`/`Upload Data` button group.
- Clicking the button calls the backend, which uses `core/llm_processor.py` to generate a natural-language question grounded in the real tables/columns currently in the database.
- The generated query text is at most two sentences.
- The query input field's contents are always fully overwritten with the newly generated query, never appended.
- If no tables are loaded, clicking the button surfaces a clear error instead of crashing or calling the LLM with an empty schema.
- All new backend unit and endpoint tests pass, and all pre-existing tests continue to pass with zero regressions.
- The frontend type-checks and builds successfully with the new interfaces/DOM wiring in place.
- The new E2E test (`test_random_query_button.md`) passes when executed via Playwright.

## Validation Commands
Execute every command to validate the feature works correctly with zero regressions.

- `cd app/server && uv run pytest` - Run server tests (including the new `llm_processor` unit tests and the new `/api/random-query` endpoint tests) to validate the feature works with zero regressions
- `cd app/client && bun tsc --noEmit` - Type-check the frontend, including the new `RandomQueryRequest`/`RandomQueryResponse` interfaces and DOM wiring
- `cd app/client && bun run build` - Build the frontend to validate the feature works as expected
- Read `.claude/commands/test_e2e.md`, then read and execute the new `.claude/commands/e2e/test_random_query_button.md` E2E test file (via Playwright browser automation) to validate the Random Query button works end-to-end, including taking the required screenshots

## Notes
- No new third-party libraries are required — the feature reuses the existing `openai` and `anthropic` SDKs already declared in `app/server/pyproject.toml`, and FastAPI's `TestClient` (bundled with `fastapi`/`starlette`, no new dependency needed since `httpx` is already an indirect dependency of the `openai`/`anthropic` SDKs).
- The random-query prompt should explicitly instruct the LLM not to return SQL — it must return a natural-language *question*, which the user will subsequently submit through the normal Query flow (which does the NL → SQL conversion). This is a distinct responsibility from `generate_sql` and must not be conflated with it.
- Consider (but do not require for this feature) future work such as excluding the previously-generated question from repeating on consecutive clicks, or letting the button respect the currently-selected LLM provider if/when the UI ever exposes that choice to the user (today the UI always sends `llm_provider: 'openai'`, matching the existing `initializeQueryInput()` convention).
