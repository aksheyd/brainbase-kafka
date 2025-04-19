# Kafka: Vibe-code Agents

Kafka is a next-generation platform for "vibe-coding" AI agents, inspired by tools like Cursor and Windsurf. It enables users—technical or not—to create, iterate, and validate AI agents through natural language and code diffs, powered by a robust Python backend and a modern React/Next.js frontend.

---

## Project Structure

```
.
├── backend/         # Python FastAPI backend (stateful, websocket-enabled)
│   ├── agent/       # Core agent logic (LLM, validation, diffing)
│   ├── validation/  # Validation utilities
│   ├── tests/       # Backend tests (milestone-driven)
│   ├── main.py      # Backend entrypoint (FastAPI app)
│   ├── pyproject.toml  # Python project metadata and dependencies
│   ├── uv.lock      # uv dependency lockfile
│   └── ...          # Other backend modules
├── frontend/        # Next.js/React frontend (modern, feature-rich UI)
│   ├── app/         # Main app pages and layout
│   ├── components/  # UI and workspace components (shadcn/ui, Monaco, etc.)
│   ├── hooks/       # Custom React hooks (e.g., websocket)
│   ├── lib/         # Utilities (e.g., Monaco setup)
│   └── ...          # Other frontend modules
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
- **Milestone-Driven Tests**: Comprehensive backend tests for each milestone in `backend/tests/`.
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
   uv venv --python 3.13
   source .venv/bin/activate
   uv sync --locked
   ```

3. **Set up environment variables:**
   - Copy `.env.example` to `.env` and fill in your `GOOGLE_API_KEY` and any other required secrets.

4. **Run the backend server:**
   ```sh
   uv run fastapi run main.py
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
- **Communication Protocol**: See [backend/COMM_PROTOCOL.md](backend/COMM_PROTOCOL.md) for full websocket/REST API details.

---

## Frontend: Next.js, React, Tailwind CSS, shadcn/ui, Monaco Editor

The frontend is a fully functional, modern web app inspired by Cursor/Windsurf, providing a seamless UI for agent creation and iteration.

### Features

- **Modern UI**: Built with Next.js 15, React 19, Tailwind CSS, shadcn/ui, and Radix UI for a beautiful, accessible experience.
- **File Explorer**: Browse, create, and select agent files in the workspace.
- **Monaco-based Editor**: Rich code editing with syntax highlighting and custom theming.
- **Diff Viewer**: Visualize and review code diffs before applying changes.
- **Prompt Panel**: Send prompts and context to the agent, with real-time feedback.
- **Websocket Integration**: Real-time, session-based communication with the backend agent.
- **Custom Hooks**: Includes `useWebSocket` and `use-toast` for robust state and notification management.

### Requirements

- Node.js 18+
- pnpm (recommended), npm, or yarn

### Setup & Running the Frontend

1. **Install dependencies:**
   ```sh
   cd frontend
   pnpm install # or npm install or yarn install
   ```

2. **Run the frontend app:**
   ```sh
   pnpm dev # or npm run dev or yarn dev
   ```
   - The app will be available at [http://localhost:3000](http://localhost:3000)

### Key Frontend Components

- **`app/page.tsx`**: Main UI logic, state management, and websocket integration.
- **`components/workspace/`**: Workspace, FileExplorer, Editor, DiffViewer, PromptPanel, etc.
- **`components/ui/`**: shadcn/ui and Radix UI components for consistent design.
- **`hooks/useWebSocket.ts`**: Handles websocket connection and messaging.
- **`lib/monacoSetup.ts`**: Monaco Editor configuration and theming.

---

## Backend/Frontend Communication Protocol

Kafka uses a documented JSON-based websocket protocol for all agent interactions. See [`backend/COMM_PROTOCOL.md`](backend/COMM_PROTOCOL.md) for full details. Key actions include:
- `prompt`: Generate Based code from a user prompt
- `generate_diff`: Generate a code diff for a requested change
- `apply_diff`: Apply a diff to a file
- `upload_file`, `list_files`, `read_file`: File management
- `update_context`: Update session context

All actions and responses are per websocket session, enabling real-time, multi-step agent development.

---

## Professional Practices

- **Dependency Management**: All Python dependencies are locked with `uv`; Node dependencies are managed with pnpm/npm/yarn.
- **Environment Variables**: Sensitive keys are never committed; use `.env.example` as a template.
- **Testing**: Backend logic is covered by milestone-driven unit tests in `backend/tests/`.
- **Milestone-Driven Development**: See `SPEC.md` for milestone breakdown and progress tracking.
- **Readable Commits**: Please split changes into logical, well-described commits for review.

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
