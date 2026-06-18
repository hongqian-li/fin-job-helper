import requests  # library used to send HTTP requests to Ollama's local API

# Ollama runs a local web server at this address once it's started
OLLAMA_URL = "http://localhost:11434/api/generate"

# the model we want to talk to (must already be pulled with `ollama pull llama3.2`)
MODEL_NAME = "llama3.2"

# a hardcoded message we send to the model, just to test the connection
prompt = "Hello! Can you tell me a fun fact about Finland?"

# the JSON payload Ollama's /api/generate endpoint expects
payload = {
    "model": MODEL_NAME,
    "prompt": prompt,
    "stream": False,  # ask Ollama to send back one full response instead of streaming chunks
}

# send the POST request to the local Ollama server and wait for the response
response = requests.post(OLLAMA_URL, json=payload)

# parse the JSON body of the response into a Python dict
data = response.json()

# the model's reply text is stored under the "response" key
print(data["response"])
