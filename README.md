# Brainbase – Kafka: Vibe-code Agents

Kafka is a next-generation platform for "vibe-coding" AI agents, inspired by tools like Cursor and Windsurf. It enables users—technical or not—to create, iterate, and validate AI agents through natural language and code diffs, powered by a robust Python backend and a modern React/Next.js frontend.

---

## Project Structure

```
.
├── backend/         # Python FastAPI backend (stateful, websocket-enabled)
│   ├── agent/       # Core agent logic (LLM, validation, diffing)
│   ├── validation/  # Validation utilities
│   ├── tests/       # Backend tests
│   ├── main.py      # Backend entrypoint (FastAPI app)
│   ├── pyproject.toml  # Python project metadata and dependencies
│   ├── uv.lock      # uv dependency lockfile
│   └── ...          # Other backend modules
├── frontend/        # Next.js/React frontend (see below)
├── SPEC.md          # Full product and milestone specification
├── .env.example     # Example environment variables
└── README.md        # This file
```

---

## Backend: Python (FastAPI, LangChain, Websockets)

### Features

- **Stateful AI Agent**: Iteratively generates and validates Based code or diffs, using LLMs and a remote validation endpoint.
- **Unified Diff Application**: Applies code changes using a robust, tested unified diff engine.
- **Websocket API**: Supports real-time, session-based communication for interactive agent development.
- **Modern Dependency Management**: Uses [`uv`](https://github.com/astral-sh/uv) for fast, reliable Python dependency management.

### Requirements

- Python `3.13.3` (see `.python-version`)
- [`uv`](https://github.com/astral-sh/uv) (recommended for dependency management)
- Google API key for LLM access (see `.env.example`)

### Setup & Running the Backend

1. **Install `uv` (if not already installed):**
   ```sh
   pip install uv
   ```

2. **Install dependencies:**
   ```sh
   cd backend
   uv pip install -r pyproject.toml
   ```

3. **Set up environment variables:**
   - Copy `.env.example` to `.env` and fill in your `GOOGLE_API_KEY` and any other required secrets.

4. **Run the backend server:**
   ```sh
   uvicorn main:app --reload
   ```
   - The server will be available at [http://localhost:8000](http://localhost:8000)
   - For websocket interaction, connect to `ws://localhost:8000/ws`

5. **Run tests:**
   ```sh
   uv pip install pytest
   pytest
   ```

### Key Backend Components

- **`main.py`**: FastAPI app exposing REST and websocket endpoints for agent interaction.
- **`agent/agent.py`**: Core agent logic—handles LLM prompts, validation, and diff generation.
- **`unified_diff.py`**: Unified diff/patch application engine (public domain, robust against malformed diffs).
- **Validation**: All Based code is validated via the remote endpoint before being accepted.

---

## Frontend: Next.js, React, Tailwind CSS (Coming Soon)

> **Note:** The frontend is scaffolded in the `frontend/` directory and will provide a modern, Cursor-inspired UI for interacting with the backend agent. See SPEC.md for design references and planned features.

---

## Professional Practices

- **Dependency Management**: All Python dependencies are locked with `uv` for reproducible builds.
- **Environment Variables**: Sensitive keys are never committed; use `.env.example` as a template.
- **Testing**: Backend logic is covered by unit tests in `backend/tests/`.
- **Milestone-Driven Development**: See `SPEC.md` for milestone breakdown and progress tracking.

---

## Contributing

1. Fork the repo and create your feature branch (`git checkout -b feature/your-feature`)
2. Commit your changes with clear, conventional messages
3. Push to the branch and open a Pull Request

---

## License

This project is licensed under the MIT License.

---

## Contact

For questions or demo requests, please open an issue or contact the maintainers.
