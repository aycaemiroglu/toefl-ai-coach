# TOEFL Writing Analyzer — Web UI Design

Minimal, academic-style single-page UI for an AI-powered TOEFL Independent Writing analyzer (portfolio / research demo).

---

## 1. UI Layout

### Overall structure

- **Single column**, max-width ~720px, centered. Plenty of whitespace; no sidebar or multi-column layout.
- **Top:** App title + short subtitle (e.g. “AI-powered TOEFL Independent Writing feedback”).
- **Input block:** Prompt selector → Essay textarea → “Analyze Essay” button.
- **Results block:** Shown only after analysis; clearly separated from input (e.g. divider or card). Contains: score, strengths, weaknesses, suggestions, revised paragraph.

### Section hierarchy

1. **Header**  
   - Title: “TOEFL Writing Analyzer”  
   - Subtitle: one line describing the tool (research/portfolio context).

2. **Prompt selector**  
   - Dropdown (native `<select>`) with 8–10 TOEFL Independent Writing prompts (same topics as in your data/scripts).  
   - Label: “Essay topic” or “Prompt”.  
   - Ensures the model and user share the same task definition.

3. **Essay input**  
   - Large `<textarea>`, placeholder: “Paste your essay here (about 250–300 words)…”  
   - Optional helper: “~X words” under the textarea (client-side count).  
   - Single, clear focus: one essay, one analysis.

4. **Primary action**  
   - One button: “Analyze Essay”.  
   - Disabled when textarea is empty; shows loading state while the request is in progress (e.g. “Analyzing…”).

5. **Results panel**  
   - Visible only when the backend has returned a result.  
   - **Estimated score:** Prominent but not oversized (e.g. “Estimated score: 24 / 30” with a short note that this is AI-estimated).  
   - **Strengths:** Bullet list or short paragraphs.  
   - **Weaknesses:** Same format.  
   - **Improvement suggestions:** Numbered or bullet list, concrete and actionable.  
   - **Revised first paragraph:** Block quote or distinct typography so it’s clear this is “suggested revision,” not the original.  
   - No tabs or accordions; all sections in one scrollable block so the full feedback is visible and comparable at once.

### Visual style (academic, minimal)

- **Fonts:** One readable serif or neutral sans (e.g. Georgia, Lora, or system-ui). No decorative fonts.
- **Colors:** Near-neutral background (e.g. #fafafa or #f5f5f4), dark text (#1a1a1a), muted secondary text (#555). One subtle accent for the primary button and maybe score (e.g. dark blue or gray-blue), no bright or marketing-style colors.
- **Borders / cards:** Light borders or very subtle shadows to separate prompt + essay from results; no heavy shadows or gradients.
- **Spacing:** Consistent vertical rhythm (e.g. 16px / 24px) and comfortable line height (1.5–1.6) for long text.

This layout supports **interpretability and evaluation transparency** by:

- Making the **prompt** explicit and fixed per run (user sees exactly which task the model is evaluating).
- Keeping **input (essay)** and **output (score + strengths/weaknesses/suggestions/revised paragraph)** strictly separated, so it’s clear what is human-written vs model-generated.
- Showing **all dimensions of feedback** in one place (score, strengths, weaknesses, suggestions, revision), so researchers or users can judge whether the model’s reasoning is consistent and credible.
- Avoiding UI elements that hide or collapse feedback (e.g. no “show more” that obscures weaknesses or suggestions), so the system’s behavior is fully visible.

---

## 2. Component Structure

The UI is implemented in `frontend/` (Vite + React).

### React (frontend/)

- **App:** Single page; state: `promptId`, `essay`, `loading`, `result` (or `error`).
- **Components:**  
  - `Header` (title + subtitle).  
  - `PromptSelect` (dropdown, controlled).  
  - `EssayInput` (textarea + word count, controlled).  
  - `AnalyzeButton` (disabled when no essay; loading state).  
  - `ResultsPanel` (only when `result` exists):  
    - `ScoreBlock` (estimated score + short disclaimer).  
    - `FeedbackList` (strengths / weaknesses / suggestions — same component, different title and list).  
    - `RevisedParagraph` (first-paragraph revision in a distinct block).
- **Data flow:** User changes prompt/essay → state updates → button enabled/disabled. Submit → set loading → POST to FastAPI → set result → render `ResultsPanel`.

---

## 3. Why This UI Supports Interpretability and Evaluation Transparency

- **Explicit task (prompt):** The dropdown makes the exact TOEFL task visible. Anyone reviewing the demo can see which question the model answered and can replicate or audit the setup.
- **Clear input/output boundary:** The essay is the only variable input; the results block is clearly “model output.” That makes it easy to reason about what the system is judging and to spot inconsistencies (e.g. score vs listed weaknesses).
- **Full feedback visible:** By showing score, strengths, weaknesses, suggestions, and revised paragraph in one view, the UI avoids “black box” behavior. Users and researchers can check whether strengths/weaknesses align with the score and whether the revised paragraph reflects the stated suggestions.
- **Minimal, academic look:** Reduces distraction and frames the tool as an analysis/feedback device rather than a product pitch, which fits a research or portfolio context and keeps focus on the quality of the model’s feedback.

---

## 4. Backend contract (for implementation)

Assume FastAPI exposes something like:

- **POST** `/analyze`  
  - Body: `{ "prompt_id": "p01" | ... , "essay": "..." }`  
  - Response:  
    - `score` (0–30),  
    - `strengths` (string[]),  
    - `weaknesses` (string[]),  
    - `suggestions` (string[]),  
    - `revised_first_paragraph` (string).

The React app in `frontend/` can mock this JSON for development and use Vite proxy to the real API when the backend is ready.
