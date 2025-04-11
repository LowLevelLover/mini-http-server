[![progress-banner](https://backend.codecrafters.io/progress/http-server/d59c0b8c-d80e-4a0e-9858-6edb555962d2)](https://app.codecrafters.io/users/codecrafters-bot?r=2qF)

This is a starting point for Python solutions to the
["Build Your Own HTTP server" Challenge](https://app.codecrafters.io/courses/http-server/overview).

[HTTP](https://en.wikipedia.org/wiki/Hypertext_Transfer_Protocol) is the
protocol that powers the web. In this challenge, you'll build a HTTP/1.1 server
that is capable of serving multiple clients.

Along the way you'll learn about TCP servers,
[HTTP request syntax](https://www.w3.org/Protocols/rfc2616/rfc2616-sec5.html),
and more.

**Note**: If you're viewing this repo on GitHub, head over to
[codecrafters.io](https://codecrafters.io) to try the challenge.

-----

# Simple HTTP Server

A basic asynchronous HTTP server implemented in Python using the `asyncio` library. The server handles GET and POST requests for echoing text, retrieving user-agent information, and managing files in a specified directory.

## Features

- **Root Endpoint (`/`)**: Returns a `200 OK` response.
- **Echo Endpoint (`/echo/{text}`)**: Echoes back the provided text with optional gzip compression if supported by the client.
- **User-Agent Endpoint (`/user-agent`)**: Returns the client's `User-Agent` header value.
- **File Endpoints (`/files/{filename}`)**:
  - **GET**: Retrieves a file from the specified directory, with optional gzip compression.
  - **POST**: Creates or overwrites a file in the specified directory with the request body content.
- **Error Handling**: Returns `404 Not Found` for invalid endpoints or missing files.
- **Logging**: Logs client connections, requests, and errors with timestamps.

## Requirements

- Python 3.10+
- No external dependencies required (uses standard library modules: `asyncio`, `socket`, `gzip`, `pathlib`, `logging`)

## Installation

1. Clone or download the repository.
2. Ensure Python 3.10 or higher is installed.

## Usage

Run the server using the command below. Optionally, specify a directory for file operations:

```bash
python server.py [--directory <path>]
```

- **Without directory**: The `/files/*` endpoints will return `404` for GET requests and raise an error for POST requests.
- **With directory**: Provide a path for file storage/retrieval (e.g., `/tmp/files`).

Example:

```bash
python server.py --directory /tmp/files
```

The server listens on `localhost:4221` by default.

### Example Requests

- **Root**:
  ```bash
  curl http://localhost:4221/
  ```
  Response: `HTTP/1.1 200 OK`

- **Echo**:
  ```bash
  curl http://localhost:4221/echo/hello
  ```
  Response: `hello` (with `Content-Type: text/plain`)

  With compression:
  ```bash
  curl -H "Accept-Encoding: gzip" http://localhost:4221/echo/hello --compressed
  ```

- **User-Agent**:
  ```bash
  curl -A "Mozilla/5.0" http://localhost:4221/user-agent
  ```
  Response: `Mozilla/5.0`

- **File GET** (with `--directory /tmp/files`):
  ```bash
  curl http://localhost:4221/files/example.txt
  ```
  Response: Contents of `/tmp/files/example.txt` or `404` if not found.

- **File POST** (with `--directory /tmp/files`):
  ```bash
  curl -X POST --data "Hello, World!" http://localhost:4221/files/example.txt
  ```
  Response: `HTTP/1.1 201 Created` (creates `/tmp/files/example.txt`).

## Code Structure

- **HttpReqLine**: Parses the HTTP request line (e.g., `GET /path HTTP/1.1`).
- **HttpHeaders**: Handles HTTP headers as a dictionary-like object.
- **HttpRequest**: Represents a parsed HTTP request with method, path, headers, and body.
- **HttpResponse**: Constructs HTTP responses with status, headers, and body (supports gzip compression).
- **Handlers**:
  - `echo_handler`: Returns the provided text.
  - `user_agent_handler`: Returns the client's User-Agent.
  - `files_get_handler`: Retrieves a file.
  - `files_post_handler`: Saves a file.
- **Main Loop**: Uses `asyncio` to handle client connections concurrently.

## Configuration

- **HOST**: `localhost` (default)
- **PORT**: `4221` (default)
- **BUFF_SIZE**: `1024` bytes for receiving data
- **Directory**: Optional, specified via `--directory` argument

## Logging

The server logs:
- Client connections and disconnections
- Received requests
- Errors (with stack traces)

Example log output:
```
2025-04-11 18:09:10,420 [SERVER STARTED] Listening on localhost:4221
2025-04-11 18:09:21,940 [CONNECTED] 127.0.0.1:47920
2025-04-11 18:09:21,940 [RECEIVED from 127.0.0.1:47920] b'GET /echo/abc HTTP/1.1\r\nHost: localhost:4221\r\nUser-Agent: curl/8.12.1\r\nAccept: */*\r\nAccept-Encoding: invalid-encoding\r\n\r\n'
2025-04-11 18:09:21,941 [DISCONNECTED] 127.0.0.1:47920
```

## Limitations

- Minimal error handling for malformed requests.
- No support for advanced HTTP features (e.g., chunked encoding, keep-alive).
- File operations are synchronous and may block the event loop for large files.
- Single-threaded; relies on `asyncio` for concurrency.

## Testing

Test the server using tools like `curl`, `wget`, or a browser. For automated testing, consider a framework like `pytest` with an HTTP client library (e.g., `aiohttp`).

Example test command:
```bash
curl http://localhost:4221/echo/test
```

## Contributing

Contributions are welcome! Please:
1. Fork the repository.
2. Create a feature branch.
3. Submit a pull request with clear descriptions.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
