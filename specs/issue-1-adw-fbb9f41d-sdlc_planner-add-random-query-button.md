# Feature: Random Natural Language Query Button

## Feature Description
Add a "Random Query" button to the query section of the Natural Language SQL Interface. When clicked, the button asks the backend to generate an interesting, natural-language question (not raw SQL) based on the current database schema — the tables that exist and their column structures — and populates the query input textarea with that generated question. The query input is always overwritten with the new suggestion, even if the user had already typed something. The generated query is capped at two sentences. The button is styled like the existing "Upload Data" button (`secondary-button` class) but is visually separated ("justified apart") from the primary Query/Upload Data button group so it reads as a distinct, optional action rather than part of the core query flow.

## User Story
As a user of the Natural Language SQL Interface
I want to click a button that suggests an interesting natural-language question about my uploaded data
So that I can discover what kinds of queries are possible without having to think one up myself or already know the schema

## Problem Statement
Users who upload a new dataset don't always know what questions are interesting or even possible to ask against it — they have to inspect the "Available Tables" section, mentally map out columns and types, and then hand-craft a natural language query. This is friction, especially for first-time users or when exploring an unfamiliar table. There's currently no way to get a starting point or inspiration for a query.

## Solution Statement
Introduce a new backend endpoint that takes the current database schema (via the existing `get_database_schema()` helper), and asks the LLM (via a new function in `core/llm_processor.py`, following the same OpenAI/Anthropic routing pattern already used by `generate_sql`) to produce one interesting, specific natural-language question a user could ask about the data — limited to two sentences. The frontend adds a new "Random Query" button next to the existing query controls, styled like the "Upload Data" button, but separated from the primary button group via layout (`justify-content: space-between`). Clicking it calls the new endpoint and always overwrites the contents of the query input textarea with the generated question, ready for the user to review and execute manually (it does not auto-submit the query).

## Relevant Files
Use these files to implement the feature:

- `app/server/core/llm_processor.py` - Contains `generate_sql_with_openai`, `generate_sql_with_anthropic`, `format_schema_for_prompt`, and the `generate_sql` routing function. The new random-query generation functions must follow this exact same pattern (same API key priority routing, same markdown/code-fence cleanup, same error wrapping) so behavior is consistent and testable the same way.
- `app/server/core/sql_processor.py` - Contains `get_database_schema()`, which is already used by `/api/query` to fetch table/column metadata. Reuse this unchanged to build the prompt context for the random query generator.
- `app/server/core/data_models.py` - Contains all Pydantic request/response models (e.g. `QueryRequest`/`QueryResponse`). Add new `RandomQueryRequest`/`RandomQueryResponse` models here following the same style.
- `app/server/server.py` - Contains all FastAPI route handlers (`/api/query`, `/api/upload`, `/api/schema`, etc.), each wrapped in try/except with `logger.info`/`logger.error` on success/failure. Add the new `POST /api/random-query` endpoint here following the exact same error-handling and logging conventions as `process_natural_language_query`.
- `app/server/tests/core/test_llm_processor.py` - Existing unit test suite for `llm_processor.py` covering OpenAI/Anthropic success, markdown cleanup, missing API key, API errors, and provider routing/priority. Add an equivalent test class for the new random query functions, mirroring these exact test cases.
- `app/client/index.html` - Contains the `.query-controls` div with `#query-button` (`primary-button`) and `#upload-data-button` (`secondary-button`). Add the new `#random-query-button` here using the `secondary-button` class, restructured so it's justified apart from the other two buttons.
- `app/client/src/style.css` - Contains `.query-controls` (`display: flex; gap: 1rem; align-items: center;`) and the `.primary-button`/`.secondary-button`/`.toggle-button` styles. Update `.query-controls` layout (e.g. `justify-content: space-between`) so the new button visually separates from the primary/secondary button group, without altering existing button visuals.
- `app/client/src/main.ts` - Contains `initializeQueryInput()` (wires up `#query-button` and `#query-input`) and `initializeFileUpload()`/`initializeModal()`, all called from the `DOMContentLoaded` listener. Add a new `initializeRandomQueryButton()` following the same loading-state/error-handling pattern as `initializeQueryInput()`, and register it in `DOMContentLoaded`.
- `app/client/src/api/client.ts` - Contains the `api` object with `uploadFile`, `processQuery`, `getSchema`, `generateInsights`, `healthCheck`, all built on the shared `apiRequest<T>()` helper. Add a `generateRandomQuery` method here following the same pattern as `processQuery`.
- `app/client/src/types.d.ts` - Contains TypeScript interfaces mirroring the Pydantic models exactly (e.g. `QueryRequest`/`QueryResponse`). Add matching `RandomQueryRequest`/`RandomQueryResponse` interfaces.
- `.claude/commands/test_e2e.md` - Read this to understand how E2E tests are structured and executed (Playwright MCP, screenshot conventions, output format) before writing the new E2E test file.
- `.claude/commands/e2e/test_basic_query.md` - Read this as the reference example for E2E test file structure (User Story, Test Steps, Success Criteria) when writing the new E2E test file.
- `README.md` - Contains the "Usage" section documenting the query/upload workflow; update this to mention the new Random Query button.

### New Files
- `.claude/commands/e2e/test_random_query_button.md` - New E2E test file validating the Random Query button populates the query input with a generated question, following the structure of `test_basic_query.md` and `test_complex_query.md`.

## Implementation Plan
### Phase 1: Foundation
Add the new Pydantic request/response models (`RandomQueryRequest`, `RandomQueryResponse`) to `data_models.py`, and add the corresponding TypeScript interfaces to `types.d.ts`. These are shared contracts the backend endpoint and frontend API client both depend on.

### Phase 2: Core Implementation
Implement the LLM-backed random query generation in `core/llm_processor.py` (OpenAI + Anthropic variants plus a routing function reusing the existing priority logic and `format_schema_for_prompt`), expose it via a new `POST /api/random-query` FastAPI endpoint in `server.py`, and add unit tests covering success, markdown cleanup, missing API keys, API errors, provider routing, and the two-sentence cap.

### Phase 3: Integration
Wire up the frontend: add the `generateRandomQuery` API client method, add the "Random Query" button to `index.html` (Upload Data button style, justified apart from the primary button group via `style.css` layout changes), and add the click handler in `main.ts` that calls the endpoint and always overwrites `#query-input`'s value. Add an E2E test validating the full flow, update the README, and run all validation commands to confirm zero regressions.

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

### 1. Add shared request/response contracts
- In `app/server/core/data_models.py`, add (near the existing Query Models section):
  ```python
  class RandomQueryRequest(BaseModel):
      llm_provider: Literal["openai", "anthropic"] = "openai"

  class RandomQueryResponse(BaseModel):
      query: str
      error: Optional[str] = None
  ```
- In `app/client/src/types.d.ts`, add matching interfaces near the existing Query Types section:
  ```ts
  interface RandomQueryRequest {
    llm_provider: "openai" | "anthropic";
  }

  interface RandomQueryResponse {
    query: string;
    error?: string;
  }
  ```

### 2. Implement random query generation in the LLM processor
- In `app/server/core/llm_processor.py`, add `generate_random_query_with_openai(schema_info: Dict[str, Any]) -> str` and `generate_random_query_with_anthropic(schema_info: Dict[str, Any]) -> str`, mirroring `generate_sql_with_openai`/`generate_sql_with_anthropic`:
  - Reuse `format_schema_for_prompt(schema_info)` to build the schema description.
  - Prompt the model to produce exactly one interesting, specific natural-language question a user could ask about the data (not SQL), based on the actual tables/columns present, with a strict instruction: "Respond with at most two sentences total. Return ONLY the question text, no explanations, no quotes, no markdown."
  - Reuse the same markdown/code-fence stripping logic used for SQL cleanup (strip ` ```sql`, ` ``` ` fences) in case the model wraps its answer.
  - Add a small helper `_limit_to_two_sentences(text: str) -> str` that splits on sentence-ending punctuation (`.`, `?`, `!`) and truncates to the first two sentences, then use it in both functions before returning, as a safety net on top of the prompt instruction.
  - Wrap errors the same way as `generate_sql_with_openai`/`generate_sql_with_anthropic` (e.g. `raise Exception(f"Error generating random query with OpenAI: {str(e)}")`).
- Add `generate_random_query(request: RandomQueryRequest, schema_info: Dict[str, Any]) -> str` that routes exactly like `generate_sql`: OpenAI key present → OpenAI; else Anthropic key present → Anthropic; else fall back to `request.llm_provider`.
- Import `RandomQueryRequest` in `llm_processor.py` alongside the existing `QueryRequest` import.

### 3. Add the backend endpoint
- In `app/server/server.py`:
  - Import `RandomQueryRequest`, `RandomQueryResponse` from `core.data_models`.
  - Import `generate_random_query` from `core.llm_processor`.
  - Add a new endpoint:
    ```python
    @app.post("/api/random-query", response_model=RandomQueryResponse)
    async def generate_random_query_endpoint(request: RandomQueryRequest) -> RandomQueryResponse:
        """Generate a random natural language query suggestion based on the current schema"""
        try:
            schema_info = get_database_schema()
            if not schema_info.get('tables'):
                raise Exception("No tables available. Upload data first.")

            query = generate_random_query(request, schema_info)

            response = RandomQueryResponse(query=query)
            logger.info(f"[SUCCESS] Random query generated: {query}")
            return response
        except Exception as e:
            logger.error(f"[ERROR] Random query generation failed: {str(e)}")
            logger.error(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
            return RandomQueryResponse(query="", error=str(e))
    ```
  - Place it logically near `process_natural_language_query` (after `/api/query`, before `/api/schema`).

### 4. Unit test the LLM processor changes
- In `app/server/tests/core/test_llm_processor.py`, add a `TestRandomQueryGeneration` class (or extend `TestLLMProcessor`) covering, mirroring the existing SQL generation tests:
  - `generate_random_query_with_openai` success case (mock `OpenAI`, assert the returned text and that `chat.completions.create` was called with expected model/temperature/max_tokens).
  - `generate_random_query_with_openai` markdown/code-fence cleanup.
  - `generate_random_query_with_openai` missing API key raises with expected message.
  - `generate_random_query_with_openai` API error wraps with expected message.
  - Same four cases for `generate_random_query_with_anthropic`.
  - A test that a long, multi-sentence mocked response gets truncated to two sentences by `_limit_to_two_sentences` (call it directly or via the wrapping functions).
  - `generate_random_query` provider routing/priority tests mirroring `test_generate_sql_openai_key_priority`, `test_generate_sql_anthropic_fallback`, `test_generate_sql_request_preference_openai`, `test_generate_sql_request_preference_anthropic`.

### 5. Add the E2E test file
- Read `.claude/commands/test_e2e.md` and `.claude/commands/e2e/test_basic_query.md` to understand the required structure and conventions.
- Create `.claude/commands/e2e/test_random_query_button.md` with:
  - A User Story about discovering interesting queries via the Random Query button.
  - Test Steps: navigate to the app, upload sample data (e.g. the "Users Data" sample) so a table exists, screenshot the initial state, type some placeholder text into the query input, click the "Random Query" button, verify the query input's value changed and is non-empty (overwriting the placeholder text), verify it is a plausible question (ends with reasonable punctuation, not empty), screenshot the populated query input, then verify clicking "Query" with the populated text still runs successfully.
  - Success Criteria: button is present and styled like Upload Data, clicking it always overwrites the input, generated text is non-empty and reasonably short (two sentences max), no errors occur, and the required screenshots are captured.

### 6. Wire up the API client
- In `app/client/src/api/client.ts`, add to the `api` object:
  ```ts
  async generateRandomQuery(request: RandomQueryRequest): Promise<RandomQueryResponse> {
    return apiRequest<RandomQueryResponse>('/random-query', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(request)
    });
  }
  ```

### 7. Add the button to the UI
- In `app/client/index.html`, restructure the `.query-controls` section so the new button is visually separated from the primary Query/Upload Data group, e.g.:
  ```html
  <div class="query-controls">
    <div class="query-controls-primary">
      <button id="query-button" class="primary-button">Query</button>
      <button id="upload-data-button" class="secondary-button">Upload Data</button>
    </div>
    <button id="random-query-button" class="secondary-button">🎲 Random Query</button>
  </div>
  ```
- In `app/client/src/style.css`, update `.query-controls` to `justify-content: space-between;` (keeping `display: flex; align-items: center;`), and add a `.query-controls-primary { display: flex; gap: 1rem; align-items: center; }` rule so the first two buttons keep their existing spacing/appearance while the new button is pushed apart from them. Do not modify `.primary-button`/`.secondary-button` visual styles — the new button reuses `.secondary-button` as-is.

### 8. Wire up the click handler
- In `app/client/src/main.ts`, add a new function:
  ```ts
  function initializeRandomQueryButton() {
    const randomQueryButton = document.getElementById('random-query-button') as HTMLButtonElement;
    const queryInput = document.getElementById('query-input') as HTMLTextAreaElement;

    randomQueryButton.addEventListener('click', async () => {
      randomQueryButton.disabled = true;
      const originalText = randomQueryButton.innerHTML;
      randomQueryButton.innerHTML = '<span class="loading"></span>';

      try {
        const response = await api.generateRandomQuery({ llm_provider: 'openai' });

        if (response.error) {
          displayError(response.error);
        } else {
          // Always overwrite whatever is currently in the input
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
- Register it in the `DOMContentLoaded` listener alongside `initializeQueryInput()`, `initializeFileUpload()`, `initializeModal()`.

### 9. Update documentation
- In `README.md`, under the "Usage" section, add a bullet describing the Random Query button (e.g. between steps 1 and 2): clicking "Random Query" generates and fills in an example natural-language question based on the current tables, always replacing whatever is currently in the query input.

### 10. Run validation
- Run all commands in `Validation Commands` below and confirm zero regressions, including the new E2E test.

## Testing Strategy
### Unit Tests
- `core/llm_processor.py`: OpenAI and Anthropic random-query generation success, markdown cleanup, missing API key error, API error wrapping, two-sentence truncation, and provider routing/priority (OpenAI priority when both keys present, Anthropic fallback, request-preference fallback when no keys present) — mirroring the existing `generate_sql` test coverage exactly.
- Manual/E2E: new `.claude/commands/e2e/test_random_query_button.md` validates the button end-to-end against the running app and a real LLM call.

### Edge Cases
- No tables exist in the database yet (empty schema) — endpoint should return a clear `error` message (e.g. "No tables available. Upload data first.") rather than calling the LLM with empty schema context; frontend should surface this via `displayError` and leave the query input untouched.
- Query input already contains user-typed text — clicking Random Query must always overwrite it, per the feature requirement.
- LLM returns a response wrapped in markdown/code fences or quotes — must be stripped before displaying.
- LLM returns more than two sentences despite the prompt instruction — must be truncated client-side-safe via `_limit_to_two_sentences` on the backend before it ever reaches the client.
- Neither `OPENAI_API_KEY` nor `ANTHROPIC_API_KEY` is set — falls back to `request.llm_provider` exactly like `generate_sql`, and if the chosen provider also fails, the missing-API-key error message is surfaced via the `error` field.
- Multiple tables exist — the generated question should be answerable using the available schema (best-effort; not deterministically verified in unit tests, but the prompt includes full schema context so the LLM has what it needs).
- Rapid repeated clicks — button is disabled with a loading indicator while the request is in flight, matching the existing Query button's UX pattern.

## Acceptance Criteria
- A new "Random Query" button appears in the query section, styled identically to the "Upload Data" button (`secondary-button` class), and is visually separated ("justified apart") from the Query/Upload Data button group.
- Clicking the button calls a new `POST /api/random-query` endpoint that generates a natural-language question using `llm_processor.py`, based on the real current database schema (tables and columns).
- The generated question always overwrites the current contents of the query input textarea, regardless of what was there before.
- The generated question is at most two sentences.
- If no tables exist, the user sees a clear error instead of a broken/empty request.
- Clicking "Query" after Random Query populates the field still works normally (no regression to existing query flow).
- All existing tests continue to pass with zero regressions.

## Validation Commands
Execute every command to validate the feature works correctly with zero regressions.

- `cd app/server && uv run pytest` - Run server tests to validate the feature works with zero regressions
- `cd app/server && uv run pytest tests/core/test_llm_processor.py -v` - Run the specific unit tests for the new random query generation logic
- `cd app/client && bun tsc --noEmit` - Run frontend type checking to validate the feature works with zero regressions
- `cd app/client && bun run build` - Run frontend build to validate the feature works with zero regressions
- Read `.claude/commands/test_e2e.md`, then read and execute the new `.claude/commands/e2e/test_random_query_button.md` E2E test to validate this functionality works end-to-end (button styling/placement, overwrite behavior, two-sentence limit, no errors).

## Notes
- No new third-party libraries are required — this feature reuses the existing `openai`/`anthropic` SDK clients already used by `generate_sql`, and the existing `get_database_schema()` helper.
- The endpoint deliberately does not accept a `table_name` filter in this iteration — it always considers the full current schema, consistent with how `/api/query` already builds its prompt context. This could be extended later to target a specific table if desired.
- The response only ever contains a natural-language question, never SQL — this keeps a clean separation from `/api/query`'s responsibility of converting NL to SQL, and matches the issue's requirement to populate the input for the user to "execute manually."
