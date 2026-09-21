# Feature: Random Natural Language Query Button

## Feature Description
Add a "Random Query" button to the main query interface that uses the LLM (via `llm_processor.py`) to inspect the current database schema (tables, columns, types, row counts) and generate an interesting, ready-to-run natural language query. Clicking the button always overwrites the contents of the query input textarea with the newly generated query text, which is capped at two sentences. The button is visually styled like the existing "Upload Data" button but is placed separately (justified apart) from the primary `Query` / `Upload Data` button group so it reads as a distinct, secondary action.

## User Story
As a user exploring a newly uploaded dataset
I want to click a button that suggests an interesting natural language query based on my current tables
So that I can quickly discover useful questions to ask my data without having to think of one myself

## Problem Statement
Users who upload data (via the Upload Data modal or drag-and-drop) are presented with an empty query box and have to invent their own natural language question from scratch. First-time users or users unfamiliar with the uploaded schema don't know what interesting questions are even possible to ask (e.g., which columns exist, whether there are multiple joinable tables, etc.). This creates friction and reduces the "wow" moment of trying the natural-language-to-SQL feature.

## Solution Statement
Introduce a new backend endpoint that reuses the existing `get_database_schema()` schema introspection and a new LLM-backed generator function in `core/llm_processor.py` (following the same OpenAI/Anthropic routing pattern as `generate_sql`) that produces a single, interesting, schema-grounded natural language query limited to two sentences. The frontend adds a "Random Query" button styled like `Upload Data` (`.secondary-button`), positioned apart from the primary `Query`/`Upload Data` group via a flex `justify-content: space-between` layout. Clicking it calls the new endpoint and always overwrites the `#query-input` textarea value with the returned query text, ready for the user to review and execute manually.

## Relevant Files
Use these files to implement the feature:

- `app/server/server.py` - FastAPI route definitions; add new `POST /api/random-query` endpoint here following the exact same try/except/logging pattern as `/api/query` and `/api/insights`.
- `app/server/core/llm_processor.py` - Contains `generate_sql_with_openai`, `generate_sql_with_anthropic`, `format_schema_for_prompt`, and the `generate_sql` routing function. Add new sibling functions here (`generate_random_query_with_openai`, `generate_random_query_with_anthropic`, `generate_random_query`) that reuse `format_schema_for_prompt` for consistency and follow the identical API-key-priority routing logic.
- `app/server/core/data_models.py` - Pydantic request/response models. Add `RandomQueryRequest` and `RandomQueryResponse` following the existing `InsightsRequest`/`InsightsResponse` and `DatabaseSchemaRequest`/`DatabaseSchemaResponse` pattern (empty request model since no input is needed, response model has `query: str` and `error: Optional[str]`).
- `app/server/core/sql_processor.py` - Contains `get_database_schema()`, already used by `/api/query` and `/api/schema`; reuse directly, no changes needed here.
- `app/server/tests/core/test_llm_processor.py` - Existing unit test suite for `llm_processor.py`; add new test cases here for the random query generator functions, mirroring the mocking patterns already used for `generate_sql_with_openai`/`generate_sql_with_anthropic`/`generate_sql`.
- `app/client/index.html` - Contains the `#query-section` markup with `.query-controls` div wrapping `#query-button` (`.primary-button`) and `#upload-data-button` (`.secondary-button`). Restructure so the new `#random-query-button` (styled `.secondary-button`) sits apart from the primary group.
- `app/client/src/main.ts` - Contains `initializeQueryInput()`, `initializeFileUpload()`, `initializeModal()`, and `displayError()`. Add a new `initializeRandomQuery()` function following the same loading-state/error-handling pattern as `initializeQueryInput()`, and call it from the `DOMContentLoaded` listener.
- `app/client/src/api/client.ts` - Contains the `api` object with `uploadFile`, `processQuery`, `getSchema`, `generateInsights`, `healthCheck` methods. Add a `generateRandomQuery()` method following the same `apiRequest<T>()` pattern as `generateInsights`.
- `app/client/src/types.d.ts` - TypeScript interfaces mirroring the Pydantic models exactly. Add `RandomQueryResponse` interface matching the new `RandomQueryResponse` Pydantic model.
- `app/client/src/style.css` - Contains `.query-controls` (currently `display: flex; gap: 1rem;`) and `.primary-button`/`.secondary-button`/`.toggle-button` shared button styles. Update `.query-controls` to justify the new button apart from the primary group, and add a small wrapper class for the existing left-hand button pair.
- `.claude/commands/e2e/test_basic_query.md` and `.claude/commands/e2e/test_complex_query.md` - Read these to understand the exact E2E test file format/conventions (User Story, Test Steps, Success Criteria) before authoring the new E2E test file.
- `.claude/commands/test_e2e.md` - Read this to understand how E2E tests are executed (Playwright MCP, screenshot conventions, setup requirements like `scripts/reset_db.sh`) so the new E2E test file is structured correctly for the test runner.

### New Files
- `app/server/tests/core/test_llm_processor.py` is **not** new (modified only), but if desired a dedicated `app/server/tests/core/test_random_query.py` could be created; this plan keeps tests co-located in the existing `test_llm_processor.py` file to match current conventions (no new file needed).
- `.claude/commands/e2e/test_random_query_button.md` - New E2E test file validating the Random Query button end-to-end, modeled after `test_basic_query.md`.

## Implementation Plan
### Phase 1: Foundation
Add the new Pydantic request/response models (`RandomQueryRequest`, `RandomQueryResponse`) to `core/data_models.py` and the corresponding TypeScript interface to `types.d.ts`. These are the shared contracts both backend and frontend will build on.

### Phase 2: Core Implementation
Implement the LLM-backed random query generator in `core/llm_processor.py` (OpenAI + Anthropic variants plus a routing function reusing the existing API-key-priority logic and `format_schema_for_prompt`), wire it into a new `POST /api/random-query` endpoint in `server.py` that fetches the current schema via `get_database_schema()`, handles the "no tables yet" edge case, and returns the generated query or an error.

### Phase 3: Integration
Wire the frontend: add the `generateRandomQuery()` API client method, add the "Random Query" button to `index.html` styled like `Upload Data` but justified apart from the primary button group via updated `.query-controls` CSS, and implement `initializeRandomQuery()` in `main.ts` to call the endpoint on click and unconditionally overwrite `#query-input`'s value with the returned query (or show an error via the existing `displayError()` helper). Add unit tests for the new backend logic and an E2E test for the full UI flow.

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

### 1. Add backend request/response models
- In `app/server/core/data_models.py`, add (near the `Insights Models` section, in a new `# Random Query Models` section):
  ```python
  class RandomQueryRequest(BaseModel):
      pass  # No input needed

  class RandomQueryResponse(BaseModel):
      query: str
      error: Optional[str] = None
  ```

### 2. Add matching TypeScript interface
- In `app/client/src/types.d.ts`, add a `RandomQueryResponse` interface after `InsightsResponse`:
  ```ts
  interface RandomQueryResponse {
    query: string;
    error?: string;
  }
  ```

### 3. Implement the LLM random query generator
- In `app/server/core/llm_processor.py`, add three new functions after `generate_sql_with_anthropic` and before `format_schema_for_prompt` (or after it, reusing it):
  - `generate_random_query_with_openai(schema_info: Dict[str, Any]) -> str`: builds a prompt instructing the model to look at the schema (via `format_schema_for_prompt`) and produce ONE interesting, specific natural language question a user could ask about this data, referencing real table/column names, answerable via SQL, **maximum two sentences**, no SQL/explanations/quotes in the output. Calls OpenAI `gpt-4.1-mini` similarly to `generate_sql_with_openai` (temperature can be higher, e.g. 0.8, for variety), strips whitespace/quotes.
  - `generate_random_query_with_anthropic(schema_info: Dict[str, Any]) -> str`: same prompt/behavior using the Anthropic client, matching the model/params style of `generate_sql_with_anthropic` (temperature ~0.8 for variety).
  - `generate_random_query(schema_info: Dict[str, Any], llm_provider: str = "openai") -> str`: routing function mirroring `generate_sql`'s priority logic (OpenAI key first, then Anthropic key, then `llm_provider` fallback), but without needing a `QueryRequest` since there's no user-provided query text — accepts an optional `llm_provider` default fallback parameter instead of a request object.
  - Ensure the prompt explicitly asks for plain text output only (strip leading/trailing quotation marks and markdown code fences the same way `generate_sql_with_openai`/`generate_sql_with_anthropic` do).
- Raise a clear exception if `schema_info['tables']` is empty (no point asking the LLM with no schema) — actually, prefer handling the "no tables" case in the endpoint (Step 4) so the LLM functions stay simple and focused on prompt/response handling, matching the separation of concerns already used for `generate_sql`.

### 4. Add the `/api/random-query` endpoint
- In `app/server/server.py`:
  - Import `RandomQueryResponse` from `core.data_models` and `generate_random_query` from `core.llm_processor`.
  - Add a new endpoint:
    ```python
    @app.post("/api/random-query", response_model=RandomQueryResponse)
    async def generate_random_query_endpoint() -> RandomQueryResponse:
        """Generate a random interesting natural language query based on the current database schema"""
        try:
            schema_info = get_database_schema()
            if not schema_info.get('tables'):
                return RandomQueryResponse(
                    query="",
                    error="No tables available. Upload data first to generate a query."
                )
            query = generate_random_query(schema_info)
            logger.info(f"[SUCCESS] Random query generated: {query}")
            return RandomQueryResponse(query=query)
        except Exception as e:
            logger.error(f"[ERROR] Random query generation failed: {str(e)}")
            logger.error(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
            return RandomQueryResponse(query="", error=str(e))
    ```
  - Place it logically near `/api/query` and `/api/insights` in the file.

### 5. Add backend unit tests
- In `app/server/tests/core/test_llm_processor.py`, add a new test class (or extend `TestLLMProcessor`) covering:
  - `generate_random_query_with_openai` success case (mock OpenAI response, assert result matches mocked content, assert model/temperature/max_tokens passed).
  - `generate_random_query_with_openai` markdown/quote cleanup.
  - `generate_random_query_with_openai` no API key raises.
  - `generate_random_query_with_anthropic` success case (mirroring the OpenAI test).
  - `generate_random_query_with_anthropic` no API key raises.
  - `generate_random_query` routing: OpenAI key priority, Anthropic fallback, and `llm_provider` fallback when neither key is set (mirroring `test_generate_sql_openai_key_priority`, `test_generate_sql_anthropic_fallback`, etc., but calling `generate_random_query(schema_info)` / `generate_random_query(schema_info, llm_provider="anthropic")` instead of passing a `QueryRequest`).
- Run `cd app/server && uv run pytest tests/core/test_llm_processor.py -v` to confirm all new and existing tests pass.

### 6. Update the query controls layout (HTML)
- In `app/client/index.html`, restructure the `.query-controls` div inside `#query-section`:
  ```html
  <div class="query-controls">
    <div class="query-controls-primary">
      <button id="query-button" class="primary-button">Query</button>
      <button id="upload-data-button" class="secondary-button">Upload Data</button>
    </div>
    <button id="random-query-button" class="secondary-button">🎲 Random Query</button>
  </div>
  ```

### 7. Update styles for the new layout
- In `app/client/src/style.css`, update `.query-controls` to justify content apart:
  ```css
  .query-controls {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 1rem;
  }
  ```
- Add a new `.query-controls-primary` rule to preserve the existing grouped spacing for `Query`/`Upload Data`:
  ```css
  .query-controls-primary {
    display: flex;
    gap: 1rem;
    align-items: center;
  }
  ```
- No changes needed to `.secondary-button` itself — the new `#random-query-button` reuses that class as instructed.

### 8. Add the API client method
- In `app/client/src/api/client.ts`, add a new method to the `api` object (after `generateInsights`):
  ```ts
  async generateRandomQuery(): Promise<RandomQueryResponse> {
    return apiRequest<RandomQueryResponse>('/random-query', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({})
    });
  },
  ```

### 9. Wire up the button behavior
- In `app/client/src/main.ts`, add a new function:
  ```ts
  function initializeRandomQuery() {
    const randomQueryButton = document.getElementById('random-query-button') as HTMLButtonElement;
    const queryInput = document.getElementById('query-input') as HTMLTextAreaElement;

    randomQueryButton.addEventListener('click', async () => {
      randomQueryButton.disabled = true;
      const originalText = randomQueryButton.innerHTML;
      randomQueryButton.innerHTML = '<span class="loading"></span>';

      try {
        const response = await api.generateRandomQuery();

        if (response.error) {
          displayError(response.error);
        } else {
          // Always overwrite whatever is currently in the field
          queryInput.value = response.query;
        }
      } catch (error) {
        displayError(error instanceof Error ? error.message : 'Failed to generate random query');
      } finally {
        randomQueryButton.disabled = false;
        randomQueryButton.innerHTML = originalText;
      }
    });
  }
  ```
- Call `initializeRandomQuery();` inside the existing `document.addEventListener('DOMContentLoaded', ...)` block alongside `initializeQueryInput()`, `initializeFileUpload()`, `initializeModal()`, `loadDatabaseSchema()`.

### 10. Create the E2E test file
- Read `.claude/commands/test_e2e.md`, `.claude/commands/e2e/test_basic_query.md`, and `.claude/commands/e2e/test_complex_query.md` to confirm the exact format conventions.
- Create `.claude/commands/e2e/test_random_query_button.md` with:
  - A User Story describing a user wanting a suggested query after uploading data.
  - Test Steps: navigate to the app, open the Upload Data modal, load the "Users Data" sample (so a table exists), close the modal, take a screenshot of the initial state, click the "Random Query" button, **verify** the query input textarea is no longer empty after the click, take a screenshot of the populated query input, **verify** clicking "Random Query" again overwrites the field with new content (type placeholder text first, click the button, verify the placeholder text is gone), take a screenshot, then click the "Query" button to execute the generated query and **verify** results or a graceful error appear (since generated queries should be valid given the schema), take a final screenshot.
  - Success Criteria: button is present next to Upload Data but visually separated, clicking it always overwrites the input, generated text is non-empty and reasonably short (two sentences), no unhandled errors occur, and screenshots are captured at each key step.

### 11. Manual verification and full validation
- Start the app locally (`./scripts/start.sh` or manual backend/frontend start per `README.md`), upload sample data, click "Random Query", confirm the field is overwritten with a sensible two-sentence-max question, then click "Query" to confirm the generated query executes successfully.
- Run every command in `Validation Commands` below and fix any regressions found.

## Testing Strategy
### Unit Tests
- `generate_random_query_with_openai` / `generate_random_query_with_anthropic`: success path (mocked client response used verbatim), markdown/code-fence cleanup, missing API key raises a clear exception, and API error propagation raises a wrapped exception — mirroring the existing `generate_sql_with_openai`/`generate_sql_with_anthropic` tests.
- `generate_random_query` routing: verifies OpenAI-key priority, Anthropic-key fallback, and `llm_provider` parameter fallback when neither key is present — mirroring the existing `generate_sql` routing tests.
- Existing test suites (`test_file_processor.py`, `test_sql_processor.py`, `test_sql_injection.py`) must continue to pass unmodified, confirming no regressions.

### Edge Cases
- **No tables in the database**: clicking "Random Query" before any data is uploaded should surface a clear, friendly error (e.g., "No tables available. Upload data first to generate a query.") instead of calling the LLM or crashing.
- **LLM returns extra formatting**: the generator strips markdown code fences and wrapping quotation marks so the text placed into the input is clean, plain natural language.
- **Both API keys missing**: `generate_random_query` should raise the same kind of clear `ValueError`/exception as `generate_sql` does today (surfaced to the user via the existing error-display mechanism).
- **Overwrite behavior**: if the user has already typed something into the query input, clicking "Random Query" must always replace it (never append or merge).
- **Rapid double-click**: the button is disabled and shows a loading state while the request is in flight, preventing duplicate concurrent requests (mirrors the existing `Query` button behavior).
- **Very large schema**: `format_schema_for_prompt` (already used by `generate_sql`) is reused as-is, so behavior for large schemas is consistent with existing query generation.

## Acceptance Criteria
- A new "Random Query" button appears in the query section, styled identically to the "Upload Data" button (`.secondary-button`), but visually separated ("justified apart") from the `Query`/`Upload Data` button group.
- Clicking the button calls a new backend endpoint that generates a natural language query based on the live database schema using `llm_processor.py`, and the returned query is limited to a maximum of two sentences.
- The query input textarea is always overwritten with the new query text when the button succeeds, regardless of prior content.
- If no tables exist yet, clicking the button shows a clear error instead of failing silently or crashing.
- All new backend logic has unit test coverage following existing test conventions, and all existing tests continue to pass.
- A new E2E test file validates the button's behavior end-to-end with screenshots.
- `cd app/client && bun tsc --noEmit` and `cd app/client && bun run build` succeed with no type errors.

## Validation Commands
Execute every command to validate the feature works correctly with zero regressions.

- `cd app/server && uv run pytest` - Run server tests to validate the feature works with zero regressions
- `cd app/server && uv run pytest tests/core/test_llm_processor.py -v` - Specifically validate the new random query generator unit tests pass
- `cd app/client && bun tsc --noEmit` - Run frontend type checking to validate the feature works with zero regressions
- `cd app/client && bun run build` - Run frontend build to validate the feature works with zero regressions
- Read `.claude/commands/test_e2e.md`, then read and execute the new `.claude/commands/e2e/test_random_query_button.md` test file to validate this functionality works end-to-end.

## Notes
- No new third-party libraries are required; the feature reuses the existing `openai` and `anthropic` SDK clients already declared in `app/server/pyproject.toml`.
- The random query generator intentionally uses a higher `temperature` (e.g. 0.8) than `generate_sql` (0.1) to encourage variety across repeated clicks, while `generate_sql` itself remains untouched and low-temperature for deterministic SQL generation.
- Consider in a future iteration adding a small "dice" animation or rotating through several schema-derived query templates client-side as an instant fallback while the LLM call is in flight, to make the button feel more responsive — out of scope for this feature.
- The endpoint is a `POST` (like `/api/query` and `/api/insights`) rather than a `GET` (like `/api/schema`) because it triggers a generative LLM call as a side-effecting action each time it's invoked, matching the existing convention in this codebase for LLM-backed endpoints.
