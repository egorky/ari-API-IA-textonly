# Asterisk AI Integration

This project integrates AI capabilities with Asterisk using the Asterisk REST Interface (ARI).

## Features

- Connects to Asterisk via ARI.
- Utilizes AI models (OpenAI, Gemini) for various tasks.
- Provides a web UI for interaction and configuration.
- Uses Redis for caching and session management.

## Project Structure

- `app/`: Main application code.
  - `api/`: FastAPI routers and handlers.
  - `core/`: Configuration, security, and core utilities.
  - `models/`: Pydantic models for data structures.
  - `services/`: Business logic for AI, Redis, and tools.
  - `static/`: Static files for the web UI.
  - `templates/`: HTML templates for the web UI.
- `docs/`: Project documentation.
- `tests/`: Unit and integration tests.
- `.env`: Environment variable configuration.
- `pyproject.toml`: Project metadata and dependencies (Poetry).
- `README.md`: This file.

## Setup

1.  **Clone the repository.**
2.  **Install dependencies:**
    ```bash
    poetry install
    ```
3.  **Configure environment variables:**
    Copy `.env.example` to `.env` and update the values.
4.  **Run the application:**
    ```bash
    poetry run uvicorn app.main:app --reload
    ```

## Usage

(Details to be added)
