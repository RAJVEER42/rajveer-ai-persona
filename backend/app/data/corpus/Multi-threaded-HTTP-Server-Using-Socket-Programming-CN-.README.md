# Multi-threaded-HTTP-Server-Using-Socket-Programming-CN-

# ⚡ Multi-threaded HTTP Server

A **from-scratch, high-performance HTTP/1.1 web server** written in **pure Python**, developed for a **Computer Networks assignment**.  
It demonstrates the core principles of **network programming**, **multi-threading**, and **secure file handling** — all implemented using only Python’s standard library.

---

## 👨‍💻 Author Information

**Author:** Rajveer Bishnoi  
**Roll No:** 10404  
**Batch:** A  

---

## 🚀 Features

- 🧵 **Multi-threading:** Efficient thread pool for concurrent client handling (default: 10 threads).  
- 🌐 **HTTP/1.1 Support:** Full header parsing, persistent (keep-alive) connections, and proper response formatting.  
- 📂 **Static & Binary File Serving:** Serves `.html`, `.txt`, `.png`, `.jpg`, and `.jpeg` files directly from the `resources/` directory.  
- 📦 **JSON Upload API:** Accepts `POST` requests with JSON payloads and securely writes them to the `resources/uploads/` folder.  
- 🔒 **Security Built-in:** Path traversal prevention and Host header validation for request integrity.  
- ⚙️ **Error Handling:** Graceful HTTP responses for all major error codes — `400`, `403`, `404`, `405`, `415`, `500`, and `503`.  
- 🧾 **Detailed Logging:** Logs every connection, request, and error with timestamps and thread info.  
- 🧱 **No Dependencies:** 100% built with Python’s standard library — **no frameworks required**.

---

## 🧰 Requirements

- Python **3.7** or newer  
- Works on **Windows**, **macOS**, and **Linux**

---

## ⚙️ Usage

### ▶️ Start the Server

```bash
# Default (host: 127.0.0.1, port: 8080, threads: 10)
python server.py
````

### 🧩 Custom Configurations

```bash
# Run on a custom port
python server.py 8000

# Run on all interfaces (useful for LAN testing)
python server.py 8080 0.0.0.0

# Specify custom port, host, and thread pool size
python server.py 8080 127.0.0.1 20
```

To **stop the server**, press `Ctrl + C` for a graceful shutdown.

---

## 🧪 Testing the Server

### 🌐 HTML Endpoints

| URL                                  | Description         |
| ------------------------------------ | ------------------- |
| `http://localhost:8080/`             | Serves `index.html` |
| `http://localhost:8080/about.html`   | Serves About page   |
| `http://localhost:8080/contact.html` | Serves Contact page |

---

### 📦 Binary File Downloads

| URL                                | File Type  |
| ---------------------------------- | ---------- |
| `http://localhost:8080/sample.txt` | Text file  |
| `http://localhost:8080/logo.png`   | PNG image  |
| `http://localhost:8080/photo.jpg`  | JPEG image |

---

### 💾 JSON Upload Endpoint

Upload JSON data securely using the `/upload` route.

```bash
curl -X POST http://localhost:8080/upload \
  -H "Content-Type: application/json" \
  -H "Host: localhost:8080" \
  -d '{"message": "Hello Server", "timestamp": "2025-10-10"}'
```

#### ✅ Example Response (201 Created)

```json
{
  "status": "success",
  "message": "File created successfully",
  "filepath": "/uploads/upload_20251010_212200_abcd.json"
}
```

---

## 📁 Project Structure

```bash
project/
├── server.py            # Main server implementation
├── test_server.py       # Automated test script
├── README.md            # Project documentation
├── requirements.md      # Assignment requirements
└── resources/           # Static and uploaded files
    ├── index.html       # Default home page
    ├── about.html       # About page
    ├── contact.html     # Contact page
    ├── sample.txt       # Sample text file
    ├── logo.png         # Sample PNG image
    ├── photo.jpg        # Sample JPEG image
    └── uploads/         # Directory for uploaded JSON files
```

---

## 🧠 Implementation Details

### 🧵 Thread Pool

* A **fixed-size thread pool** manages client connections efficiently.
* Uses a **thread-safe queue** to store incoming connections.
* Ensures **controlled concurrency** and avoids resource starvation under load.

### 🔄 Persistent Connections (Keep-Alive)

* Supports **multiple requests per TCP connection** for efficiency.
* Automatically closes idle connections after a timeout period.

### 🧩 File Handling

* Serves **text and binary files** correctly with proper headers.
* Uses `sendall()` to ensure complete data transfer.
* Sets accurate `Content-Length` and `Content-Type` headers.

### 🔒 Security Features

* **Path Traversal Protection:**
  Prevents access to files outside the `resources/` directory using `os.path.abspath`.
* **Host Header Validation:**
  Rejects requests with invalid or spoofed Host headers.

### ⚙️ Error Handling

Comprehensive support for standard HTTP status codes:

| Code | Meaning                | Description                            |
| ---- | ---------------------- | -------------------------------------- |
| 400  | Bad Request            | Malformed request syntax               |
| 403  | Forbidden              | Invalid Host or path traversal attempt |
| 404  | Not Found              | Requested resource missing             |
| 405  | Method Not Allowed     | Unsupported HTTP method                |
| 415  | Unsupported Media Type | Invalid Content-Type in POST           |
| 500  | Internal Server Error  | Unexpected server error                |
| 503  | Service Unavailable    | Thread pool saturation or overload     |

---

## 🧾 Logging System

Every server event is logged in real-time.

Example log:

```
[2025-10-10 21:30:05] [Thread-3] 127.0.0.1 GET /index.html → 200 OK (5321 bytes)
```

**Logs include:**

* Timestamp
* Thread name
* Client IP address
* HTTP method & request path
* Response status and size

---

## 📋 Assignment Requirements — ✅ Completed

| Requirement                             | Implemented |
| --------------------------------------- | ----------- |
| Multi-threaded server using thread pool | ✅           |
| TCP socket-based HTTP communication     | ✅           |
| HTTP request parsing                    | ✅           |
| GET for HTML and binary files           | ✅           |
| POST for JSON uploads                   | ✅           |
| Path traversal and host validation      | ✅           |
| Connection management (keep-alive)      | ✅           |
| Full error code support                 | ✅           |
| Logging and security                    | ✅           |
| Binary file transfer                    | ✅           |

---

## ⚠️ Limitations

* Entire files are read into memory — not suitable for files >100MB.
* No support for **HTTPS/TLS** (unencrypted HTTP).
* Missing advanced HTTP features like:

  * Chunked Transfer Encoding
  * GZIP Compression
  * Caching Headers (ETag, Last-Modified)
* MIME types are hardcoded for simplicity.

---

## 🚧 Future Enhancements

* Implement **asynchronous I/O (asyncio)** for non-blocking scalability.
* Add **HTTPS** via Python’s `ssl` module.
* Improve **MIME type detection** using `mimetypes` library.
* Enable **directory listing** for resource browsing.
* Add **API routes** for PUT/DELETE requests.

---

## 🏁 Summary

This project demonstrates:

* Core concepts of **multi-threaded network programming**
* Manual **HTTP/1.1 protocol handling**
* **Secure and concurrent** request management
* Educational understanding of **how web servers work internally**


---



