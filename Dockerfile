# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Install poetry
RUN pip install poetry

# Copy only pyproject.toml and poetry.lock* first to leverage Docker cache
COPY pyproject.toml poetry.lock* ./

# Install project dependencies
# --no-root: Do not install the project itself as editable, only dependencies
# --no-dev: Do not install development dependencies
# poetry config virtualenvs.create false: install to system python in image
RUN poetry config virtualenvs.create false && \
    poetry install --no-dev --no-interaction --no-ansi --no-root

# Copy the rest of the application code
COPY ./app /app/app
COPY .env.example /app/.env.example
# Note: .env file itself should not be copied into the image for security.
# It should be provided at runtime.

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application using Uvicorn via app/main.py
# For production, consider Gunicorn:
# CMD ["poetry", "run", "gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "app.main:app", "-b", "0.0.0.0:8000"]
CMD ["poetry", "run", "python", "app/main.py"]
