#!/bin/sh

set -e

# Start the ollama server in the background
/bin/ollama serve &
pid=$!

echo "Ollama server starting..."

# Wait for the server to be ready
while ! curl -s -f http://localhost:11434/ > /dev/null
do
  echo "Waiting for Ollama server to be ready..."
  sleep 1
done

echo "Ollama server is ready."
echo "Pulling llama3 model. This may take a few minutes..."
/bin/ollama pull llama3
echo "Model pull complete."

echo "Ollama is now running with the llama3 model."
echo "You can access the web UI at http://localhost:8080"

# Wait for the server process to exit
wait $pid 