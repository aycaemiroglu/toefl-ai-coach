# TOEFL Writing Analyzer — React Frontend

Minimal React frontend for the TOEFL Writing Analyzer. One page: prompt dropdown, essay textarea, submit button, loading state, and AI feedback display.

## Setup

```bash
cd frontend
npm install
```

## Run (dev)

```bash
npm run dev
```

Opens at http://localhost:3000. API requests to `/writing/feedback` are proxied to `http://localhost:8000` (see `vite.config.js`). Start your FastAPI backend on port 8000 so the button works.

## Backend contract

- **POST** `/writing/feedback`
  - Request body: `{ "prompt": "...", "essay": "..." }`
  - Response: `{ "model": "...", "feedback": "..." }`

The UI sends the **selected prompt text** (not the prompt id) in `prompt`. Feedback is shown as plain text with `white-space: pre-wrap` so newlines and formatting are preserved.

## Build

```bash
npm run build
```

Output is in `dist/`. Serve with any static host or mount under your FastAPI app.

## Env (optional)

- `VITE_API_URL` — Base URL for the API (e.g. `http://localhost:8000`). If unset, the dev server uses the proxy and requests go to `/writing/feedback`.
