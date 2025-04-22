#!/bin/bash

# Start Kafka backend and frontend, and shut down both on exit

# Start backend
cd backend
uv run uvicorn main:app --port 8000 &
BACKEND_PID=$!
cd ..

# Start frontend
cd frontend
npx serve@latest out &
FRONTEND_PID=$!
cd ..

# Trap script exit and kill both servers
cleanup() {
  echo "Shutting down servers..."
  kill $BACKEND_PID $FRONTEND_PID
  wait $BACKEND_PID $FRONTEND_PID 2>/dev/null
}
trap cleanup EXIT

# Wait for both processes
wait