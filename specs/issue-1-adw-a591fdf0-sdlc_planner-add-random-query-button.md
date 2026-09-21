# Feature: Random Natural Language Query Button

## Feature Description
A new "Random Query" button in the query section that generates an interesting, LLM-authored natural language question based on the current database tables and their structures (columns, types, row counts), and populates the query input field with it. The user can then review, edit, or immediately run the suggested query via the existing "Query" button. The button always overwrites whatever text currently exists in the query input, uses the same visual style as the existing "Upload Data" button, and is visually separated from the primary "Query"/"Upload Data" button group (placed at the opposite end of the controls row). Generated queries are constrained to a maximum of two sentences.

## User Story
As a user exploring an unfamiliar dataset
I want to click a button and get a suggested natural language question about my data
So that I can discover interesting things to ask without having to study the schema myself or think of a query from scratch

## Problem Statement
Users who upload a new dataset often don't know what questions are worth asking. The interface currently requires users to manually compose a natural language query with no schema-aware assistance, which is a barrier for first-time users or anyone exploring an unfamiliar table. There's no existing way to get inspiration for a query based on what data is actually available.

## Solution Statement
Add a new backend endpoint that reads the current database schema (tables, columns, types, row counts — the same schema info already produced by `get_database_schema()`), sends it to the existing LLM routing infrastructure in `llm_processor.py` with a prompt asking for one interesting, concise (max two sentences) natural language question about the data, and returns that question to the client. Add a "Random Query" button, styled like the existing "Upload Data" secondary button and positioned apart from the primary button group, that calls this endpoint and overwrites the query input field with the returned text. If no tables exist, the endpoint returns a friendly error instead of calling the LLM.

## Relevant Files
Use these files to implement the feature:

**Server-side files:**
- `app/server/server.py` - FastAPI route definitions; add new `POST /api/random-query` endpoint following the exact pattern of the existing `/api/query` endpoint (try/except, logging, Pydantic response model).
- `app/server/core/data_models.py` - Add `RandomQueryRequest` and `RandomQueryResponse` Pydantic models, following the pattern of `QueryRequest`/`QueryResponse`.
- `app/server/core/llm_processor.py` - Add the LLM-facing generation functions (`generate_random_query_with_openai`, `generate_random_query_with_anthropic`, `generate_random_query`) that mirror the existing `generate_sql_with_openai`/`generate_sql_with_anthropic`/`generate_sql` routing pattern (OpenAI key priority, then Anthropic key, then request preference). Reuses `format_schema_for_prompt`.
- `app/server/core/sql_processor.py` - No changes needed; reuse existing `get_database_schema()` to build the prompt context.
- `app/server/tests/core/test_llm_processor.py` - Existing test file/patterns to follow when adding unit tests for the new LLM functions (mocking `OpenAI`/`Anthropic` clients exactly like the existing `generate_sql_with_*` tests).

**Client-side files:**
- `app/client/index.html` - Add the new `#random-query-button` button in the `.query-controls` section, styled with the existing `secondary-button` class (same as `#upload-data-button`), positioned apart from the primary group.
- `app/client/src/style.css` - Update `.query-controls` layout (e.g. `justify-content: space-between`) and wrap the existing `Query`/`Upload Data` buttons in a sub-group so the new button visually separates from them without altering their existing styling.
- `app/client/src/main.ts` - Add `initializeRandomQueryButton()` (called from the `DOMContentLoaded` handler alongside `initializeQueryInput`, `initializeFileUpload`, `initializeModal`) that calls the new API method on click, shows a loading state on the button, and overwrites `#query-input`'s value with the returned query text (or shows an error via the existing `displayError` helper).
- `app/client/src/api/client.ts` - Add `generateRandomQuery(): Promise<RandomQueryResponse>` to the `api` object, following the exact pattern of `processQuery`/`getSchema`.
- `app/client/src/types.d.ts` - Add `RandomQueryRequest` and `RandomQueryResponse` interfaces that mirror the new Pydantic models exactly (per the file's existing convention/comment).

**Reference files (for understanding conventions, no changes needed):**
- `README.md` - Project overview, API endpoint list (needs updating to document the new endpoint), and usage instructions.
- `.claude/commands/test_e2e.md` - Explains how the E2E test runner executes an E2E test file with Playwright.
- `.claude/commands/e2e/test_basic_query.md` - Example E2E test file structure/format to copy for the new test.

### New Files
- `.claude/commands/e2e/test_random_query_button.md` - New E2E test file validating the Random Query button's behavior end-to-end (button click populates the input, overwrite behavior, and the "no tables" edge case).

## Implementation Plan
### Phase 1: Foundation
Add the new Pydantic request/response models in `data_models.py`, and add the schema-aware natural-language question generation functions to `llm_processor.py`, mirroring the existing SQL-generation routing logic exactly (OpenAI-key priority, then Anthropic-key, then request preference) so behavior stays consistent with `/api/query`.

### Phase 2: Core Implementation
Wire up the new `POST /api/random-query` endpoint in `server.py`: fetch the current schema via `get_database_schema()`, short-circuit with a friendly error if there are no tables, call the new `generate_random_query` routing function, and return a `RandomQueryResponse`. Add unit tests for the new LLM functions.

### Phase 3: Integration
Build the client side: new TypeScript types, new API client method, new button in `index.html` styled and positioned per the spec, and the `main.ts` click handler that always overwrites the query input on success and surfaces errors via the existing error UI. Update CSS so the new button is visually separated from the primary button group. Add the new E2E test file and update `README.md`'s API endpoint list.

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

### Add Data Models
- In `app/server/core/data_models.py`, add:
  - `RandomQueryRequest(BaseModel)` with `llm_provider: Literal["openai", "anthropic"] = "openai"` (mirrors `QueryRequest`, no `query` field needed since the server generates the question itself).
  - `RandomQueryResponse(BaseModel)` with `query: str` and `error: Optional[str] = None`.

### Add LLM Random Query Generation
- In `app/server/core/llm_processor.py`, add `generate_random_query_with_openai(schema_info: Dict[str, Any]) -> str`:
  - Reuses `format_schema_for_prompt(schema_info)`.
  - Prompt instructs the model to invent one interesting, specific natural language question a user might ask about this exact data (referencing real table/column names), to respond with ONLY the question (no SQL, no preamble, no markdown), and to keep it to a maximum of two sentences.
  - Use a higher `temperature` (e.g. `0.9`) than the SQL-generation calls so repeated clicks produce varied suggestions.
  - Same OpenAI client/model conventions as `generate_sql_with_openai` (`gpt-4.1-mini`, reasonable `max_tokens`, e.g. `150`).
- Add `generate_random_query_with_anthropic(schema_info: Dict[str, Any]) -> str` with the equivalent Anthropic implementation (same model as `generate_sql_with_anthropic`, `max_tokens=150`, `temperature=0.9`).
- Add a small shared helper `_enforce_two_sentence_limit(text: str) -> str` that trims the LLM output down to at most two sentences as a safety net (split on `. `/`? `/`! ` boundaries, rejoin the first two), used by both functions before returning.
- Add `generate_random_query(request: RandomQueryRequest, schema_info: Dict[str, Any]) -> str` that routes exactly like `generate_sql`: OpenAI key present → OpenAI; else Anthropic key present → Anthropic; else fall back to `request.llm_provider`.

### Add Server Endpoint
- In `app/server/server.py`:
  - Import `RandomQueryRequest`, `RandomQueryResponse` from `core.data_models` and `generate_random_query` from `core.llm_processor`.
  - Add `POST /api/random-query` (`response_model=RandomQueryResponse`) that:
    - Calls `get_database_schema()`.
    - If there are no tables (`schema_info.get('tables')` is empty), return `RandomQueryResponse(query="", error="No tables available. Upload data to get a random query suggestion.")` without calling the LLM.
    - Otherwise calls `generate_random_query(request, schema_info)` and returns `RandomQueryResponse(query=question)`.
    - Follows the exact try/except + logging pattern used by `process_natural_language_query` (log `[SUCCESS]`/`[ERROR]`, return an error-populated response instead of raising on failure).

### Add Backend Unit Tests
- In `app/server/tests/core/test_llm_processor.py`, add tests mirroring the existing `TestLLMProcessor` patterns for the new functions:
  - `test_generate_random_query_with_openai_success` (mock `OpenAI`, assert returned text and that `temperature=0.9`/model params are passed).
  - `test_generate_random_query_with_anthropic_success` (equivalent, mock `Anthropic`).
  - `test_generate_random_query_no_api_key` for both providers (expect a raised exception, same as the SQL-generation equivalents).
  - `test_enforce_two_sentence_limit` covering: text with exactly two sentences (unchanged), text with more than two sentences (truncated to two), text with one sentence (unchanged).
  - `test_generate_random_query_openai_key_priority` / `test_generate_random_query_anthropic_fallback` mirroring `test_generate_sql_openai_key_priority` / `test_generate_sql_anthropic_fallback`.

### Add Client Types and API Method
- In `app/client/src/types.d.ts`, add `RandomQueryRequest` and `RandomQueryResponse` interfaces that exactly mirror the new Pydantic models.
- In `app/client/src/api/client.ts`, add:
  ```ts
  async generateRandomQuery(request: RandomQueryRequest = { llm_provider: 'openai' }): Promise<RandomQueryResponse> {
    return apiRequest<RandomQueryResponse>('/random-query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request)
    });
  }
  ```

### Update HTML Structure
- In `app/client/index.html`, restructure `.query-controls` so the existing `#query-button` and `#upload-data-button` remain grouped together, and add a new `#random-query-button` with class `secondary-button` (same visual style as Upload Data) placed so it lands at the opposite end of the row, e.g.:
  ```html
  <div class="query-controls">
    <div class="query-controls-primary">
      <button id="query-button" class="primary-button">Query</button>
      <button id="upload-data-button" class="secondary-button">Upload Data</button>
    </div>
    <button id="random-query-button" class="secondary-button">🎲 Random Query</button>
  </div>
  ```

### Update Styles
- In `app/client/src/style.css`, update `.query-controls` to `justify-content: space-between` (keep existing `display: flex; gap; margin-top; align-items`), and add a `.query-controls-primary` rule with `display: flex; gap: 1rem; align-items: center;` so the primary group keeps its current spacing while the new button is pushed to the far side of the row.

### Add Client Click Handler
- In `app/client/src/main.ts`, add `initializeRandomQueryButton()`:
  - Grabs `#random-query-button` and `#query-input`.
  - On click: disable the button, show the existing `.loading` spinner markup (same pattern as `initializeQueryInput`'s query button), call `api.generateRandomQuery()`.
  - On success: **always** overwrite `queryInput.value` with `response.query` regardless of current content (per spec), even if `response.error` is unset but query happens to be present alongside no error; if `response.error` is set, call `displayError(response.error)` instead of touching the input.
  - On thrown error: call `displayError(...)`.
  - In `finally`: re-enable the button and restore its original label/emoji text.
  - Call `initializeRandomQueryButton()` from the `DOMContentLoaded` listener alongside the existing initializers.

### Create E2E Test File
- Create `.claude/commands/e2e/test_random_query_button.md` following the structure of `.claude/commands/e2e/test_basic_query.md`:
  - User story: as a user, I want to click a button to get a suggested query about my data so I don't have to invent one myself.
  - Test steps: navigate to the app, load the "users" sample data (via the Upload modal sample button) so a table exists, type placeholder text into the query input, click "Random Query", verify the query input's value changed (no longer equals the placeholder text and is non-empty), take a screenshot of the populated input, verify the text is plausible (contains a `?` or reasonable question-like phrasing), verify clicking "Random Query" again while text is already present overwrites it (value changes again), take a final screenshot.
  - Success criteria: button exists and is styled like Upload Data, clicking it always overwrites the input, at least 2 screenshots taken, no console errors.

### Update Documentation
- In `README.md`, add `- POST /api/random-query` - Generate a random natural language query suggestion` to the `## API Endpoints` list, and mention the "Random Query" button in the `## Usage` section next to the existing query instructions.

### Manual and Automated Validation
- Run backend unit tests and confirm no regressions.
- Run frontend type-check and build.
- Read `.claude/commands/test_e2e.md`, then execute the new `.claude/commands/e2e/test_random_query_button.md` E2E test against the running app to validate the feature end-to-end, and also re-run `.claude/commands/e2e/test_basic_query.md` to confirm no regression to the existing query flow.

## Testing Strategy
### Unit Tests
- `generate_random_query_with_openai` / `generate_random_query_with_anthropic`: success cases (mocked client returns a question, verify it's returned as-is when already ≤2 sentences), markdown/whitespace cleanup if the model wraps output oddly, missing API key raises, underlying API error raises with a wrapped message.
- `_enforce_two_sentence_limit`: 1 sentence unchanged, 2 sentences unchanged, 3+ sentences truncated to first 2, empty string handled gracefully.
- `generate_random_query` routing: OpenAI key priority over Anthropic key and over `request.llm_provider`, Anthropic fallback when only Anthropic key set, request-preference fallback when neither key is set.
- Server endpoint (`/api/random-query`) manual/integration validation: empty-database case returns the friendly error without invoking the LLM; happy path returns a `RandomQueryResponse` with a non-empty `query` and no `error`.

### Edge Cases
- No tables in the database yet (fresh install / all tables deleted) → endpoint returns an error message, button click surfaces it via `displayError` and does not touch the query input.
- Neither `OPENAI_API_KEY` nor `ANTHROPIC_API_KEY` set → existing "not set" exception surfaces as a `RandomQueryResponse.error`, handled the same as the existing `/api/query` failure path.
- LLM returns more than two sentences despite the prompt instruction → `_enforce_two_sentence_limit` truncates before the response is returned to the client.
- LLM wraps the question in markdown/quotes → cleaned up the same way `generate_sql_with_*` strips ``` fences (strip stray quote/backtick characters).
- User has existing text (or previous query results) in the input field and clicks "Random Query" → the field is unconditionally overwritten, per the issue's explicit requirement.
- Rapid repeated clicks on "Random Query" → button is disabled while the request is in flight, same pattern as the existing Query button.

## Acceptance Criteria
- A new "Random Query" button is visible in the query section, styled identically to the "Upload Data" button (`secondary-button` class).
- The new button is visually separated from the "Query"/"Upload Data" button group (opposite end of the controls row).
- Clicking the button, when at least one table exists, populates `#query-input` with a new natural-language question generated from the current schema via `llm_processor.py`, of at most two sentences.
- Clicking the button always overwrites any existing text in `#query-input`, regardless of what was there before.
- Clicking the button when no tables exist shows a clear error message and does not modify the query input.
- The generated query is not automatically executed — the user must still click "Query" to run it.
- All existing functionality (query execution, file upload, table management) continues to work without regression.
- Backend unit tests for the new LLM functions pass.
- Frontend type-checks and builds successfully.
- The new E2E test and the existing `test_basic_query` E2E test both pass.

## Validation Commands
Execute every command to validate the feature works correctly with zero regressions.

- `cd app/server && uv run pytest` - Run server tests to validate the feature works with zero regressions
- `cd app/server && uv run pytest tests/core/test_llm_processor.py -v` - Run the new/updated LLM processor unit tests specifically
- `cd app/client && bun tsc --noEmit` - Run frontend type checking to validate the feature works with zero regressions
- `cd app/client && bun run build` - Run frontend build to validate the feature works with zero regressions
- Read `.claude/commands/test_e2e.md`, then read and execute the new `.claude/commands/e2e/test_random_query_button.md` E2E test to validate this functionality works.
- Read `.claude/commands/test_e2e.md`, then read and execute `.claude/commands/e2e/test_basic_query.md` to confirm no regression to the existing query flow.

## Notes
- Reuses the existing OpenAI-priority → Anthropic-priority → request-preference routing convention from `generate_sql` for consistency; no new environment variables or configuration are needed.
- No new third-party libraries are required — `openai` and `anthropic` clients are already dependencies used by `llm_processor.py`.
- Higher `temperature` (0.9) is intentionally used only for the random-query-suggestion path so repeated clicks feel varied; the SQL-generation path is untouched and keeps its low `temperature=0.1` for determinism/accuracy.
- Consider in a future iteration letting the random query focus on a specific table (e.g. round-robin across tables) rather than the whole schema at once, for more variety when many tables exist.
- Consider client-side caching/backoff if users click the button rapidly, though the existing button-disable-while-loading pattern already prevents duplicate in-flight requests.
