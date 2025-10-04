# Ragtify

Ragtify is a concept RAG (Retrieval-Augmented Generation) application that uses Ollama for LLM inference. It demonstrates a modular architecture combining a FastAPI backend, a React frontend, and supporting infrastructure for rapid development and experimentation with RAG workflows.

## Project Structure

```
├── api/           # FastAPI backend application
├── frontend/      # React frontend application
├── infra/         # Infrastructure scripts, data, and WordPress plugins
├── .docker/       # Dockerfiles and Docker Compose configurations
├── .gitignore     # Git ignore rules
├── README.md      # Project documentation
```

## Features
- **FastAPI** backend for APIs and business logic
- **React** frontend for user interface
- **WordPress** integration for e-commerce (WooCommerce)
- **Qdrant** vector database for AI/ML features
- **Ollama** for LLM inference
- **Docker Compose** for easy orchestration

## Getting Started

### Prerequisites
- [Docker](https://www.docker.com/get-started)
- [Docker Compose](https://docs.docker.com/compose/)

### Quick Start (Recommended)
1. Clone the repository:
   ```sh
   git clone <your-repo-url>
   cd ragtify
   ```
2. Copy and edit the `.env` file as needed for secrets and API keys.
3. Build and start all services:
   ```sh
   docker compose -f .docker/docker-compose.yml up -d --build
   ```
4. Access the services:
   - **Backend API:** http://localhost:8000/api/v1/
   - **Frontend:** http://localhost:3001/
   - **WordPress:** http://localhost:8080/
   - **Ollama API:** http://localhost:11434/

### Directory Details
- `api/` — FastAPI app, models, schemas, services, and DB setup
- `frontend/` — React app (Node.js, Nginx for production)
- `infra/` — Scripts, CSVs, WordPress plugins, and infra helpers
- `.docker/` — All Dockerfiles and Compose files

### Development
- Backend: edit code in `api/`, restart the backend container as needed
- Frontend: edit code in `frontend/`, restart the frontend container as needed
- Infrastructure: use scripts in `infra/` for data and WordPress management

## Ollama & Llama Model Usage

This project sets up a local Llama instance (via Ollama) with optional web-based UI using Docker Compose.

### How to Run Ollama

1. **Start the services:**
   ```sh
   docker compose -f .docker/docker-compose.yml up -d --build
   ```
   This will start the `ollama` server and all other services in the background.

2. **Pull a Llama model:**
   After the containers are running, you may need to pull a model for Ollama to use. For example, to pull the `llama3` model:
   ```sh
   docker exec -it ollama ollama run llama3
   ```
   This may take some time depending on your internet connection. You can replace `llama3` with other models available on [Ollama's model library](https://ollama.com/library).

3. **Access the Web UI (if enabled):**
   If you have the web UI enabled, you can access it at:
   [http://localhost:8080](http://localhost:8080)

### How to Stop
To stop the services, run:
```sh
   docker compose -f .docker/docker-compose.yml down --remove-orphans
```
This will stop and remove the containers. Downloaded models are preserved in the `ollama_data` Docker volume.

### How to See Progress
- To monitor model download progress:
  ```sh
  docker compose -f .docker/docker-compose.yml logs -f ollama
  ```
- If you only see `pulling manifest` for a long time:
  - There may be a network issue, or the registry is slow.
  - Try restarting the container:
    ```sh
    docker compose -f .docker/docker-compose.yml restart ollama
    ```
  - Or try pulling a smaller model for testing (e.g., `llama2` or `phi3`).

#### Summary
- Progress is shown automatically in the logs once the download starts.
- If you only see `pulling manifest`, the download hasn't started yet.
- You can't force more detailed progress until the actual download begins.

## Useful Commands
- Start all services:  
  `docker compose -f .docker/docker-compose.yml up -d --build`
- Stop all services:  
  `docker compose -f .docker/docker-compose.yml down --remove-orphans`
- View logs:  
  `docker compose -f .docker/docker-compose.yml logs <service>`

### Notes
- All Docker volumes and generated data are ignored by Git (see `.gitignore`).
- For local development, you can run backend/frontend outside Docker if you prefer, but Docker is recommended for consistency.
- Environment variables are managed via `.env` and passed to containers by Docker Compose.

## License
MIT (or your license here) 