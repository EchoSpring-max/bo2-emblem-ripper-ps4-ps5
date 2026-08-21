"""The MITM proxy the PS5 points its network proxy setting at.

HTTPS (CONNECT) traffic is tunneled raw and never decrypted, so PSN sign-in
and normal console functionality keep working untouched. Plain HTTP requests
to the Demonware emblem-storage endpoint are the only thing inspected: in
CAPTURE mode the real response is saved, in Show mode it's replaced with
whichever emblem is currently selected (see broadcast.py).
"""
import os
import re
import socket
import threading
import time
import urllib.parse

from . import config
from .state import read_state
from .storage import get_or_create_capture_group, mark_group_profile, slot_path, write_slot_bytes
from .broadcast import read_selected_data, read_selection

# matches ".../u51b08745d269.slot_504?..." -> userhash, slot number
PATH_RE = re.compile(r"/(u[0-9a-fA-F]+)\.slot_(\d+)")


def log(msg):
    print(f"{time.strftime('%H:%M:%S')} {msg}", flush=True)


def pipe(src, dst):
    try:
        while True:
            data = src.recv(65536)
            if not data:
                break
            dst.sendall(data)
    except OSError:
        pass
    finally:
        for s in (src, dst):
            try:
                s.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass


def recv_full_response(sock):
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = sock.recv(4096)
        if not chunk:
            break
        data += chunk
    header_end = data.find(b"\r\n\r\n")
    if header_end == -1:
        return data, b""
    header_end += 4
    headers = data[:header_end]
    body = data[header_end:]
    cl = None
    chunked = False
    connection_close = False
    for line in headers.split(b"\r\n"):
        if line.lower().startswith(b"content-length:"):
            cl = int(line.split(b":", 1)[1].strip())
        elif line.lower().startswith(b"transfer-encoding:"):
            encodings = line.split(b":", 1)[1].strip().lower()
            chunked = b"chunked" in encodings
        elif line.lower().startswith(b"connection:"):
            connection_close = b"close" in line.split(b":", 1)[1].strip().lower()
    if cl is not None:
        while len(body) < cl:
            chunk = sock.recv(4096)
            if not chunk:
                break
            body += chunk
    elif chunked:
        body = _recv_chunked_body(sock, body)
    elif connection_close:
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            body += chunk
    return headers, body


def recv_full_request(initial_data, sock):
    data = initial_data
    while b"\r\n\r\n" not in data:
        chunk = sock.recv(4096)
        if not chunk:
            break
        data += chunk
    header_end = data.find(b"\r\n\r\n")
    if header_end == -1:
        return data
    header_end += 4
    headers = data[:header_end]
    body = data[header_end:]
    content_length = 0
    for line in headers.split(b"\r\n"):
        if line.lower().startswith(b"content-length:"):
            content_length = int(line.split(b":", 1)[1].strip())
            break
    while len(body) < content_length:
        chunk = sock.recv(4096)
        if not chunk:
            break
        body += chunk
    return headers + body


def _recv_chunked_body(sock, initial_body):
    buffered = initial_body
    full_body = b""
    while True:
        size_line, buffered = _read_line(sock, buffered)
        size_token = size_line.split(b";", 1)[0].strip()
        try:
            chunk_size = int(size_token or b"0", 16)
        except ValueError:
            break
        if chunk_size == 0:
            _trailer, buffered = _consume_until(sock, buffered, b"\r\n\r\n")
            return full_body
        chunk, buffered = _read_exact(sock, buffered, chunk_size + 2)
        if len(chunk) < chunk_size + 2:
            break
        full_body += chunk[:-2]
    return full_body + buffered


def _read_exact(sock, buffered, size):
    while len(buffered) < size:
        chunk = sock.recv(4096)
        if not chunk:
            break
        buffered += chunk
    return buffered[:size], buffered[size:]


def _read_line(sock, buffered):
    while b"\r\n" not in buffered:
        chunk = sock.recv(4096)
        if not chunk:
            return buffered, b""
        buffered += chunk
    idx = buffered.index(b"\r\n") + 2
    return buffered[:idx], buffered[idx:]


def _consume_until(sock, buffered, marker):
    while marker not in buffered:
        chunk = sock.recv(4096)
        if not chunk:
            return buffered, b""
        buffered += chunk
    idx = buffered.index(marker) + len(marker)
    return buffered[:idx], buffered[idx:]


def fetch_real(req, host, port):
    upstream = socket.create_connection((host, port))
    upstream.sendall(req)
    headers, body = recv_full_response(upstream)
    upstream.close()
    return headers, body


def forward_raw(req, host, port):
    upstream = socket.create_connection((host, port))
    upstream.sendall(req)
    headers, body = recv_full_response(upstream)
    upstream.close()
    return headers + body


def _req_header(req, name):
    """Return the value of an HTTP request header (case-insensitive) or None."""
    needle = (name.lower() + ":").encode()
    for line in req.split(b"\r\n")[1:]:
        if not line:
            break
        if line.lower().startswith(needle):
            return line.split(b":", 1)[1].strip().decode("latin1", "replace")
    return None


def _parse_http_target(req_line, req_headers):
    parts = req_line.split()
    if len(parts) < 2:
        return None, None, None, None

    method = parts[0].upper()
    raw_target = parts[1]

    if "://" in raw_target:
        parsed = urllib.parse.urlsplit(raw_target)
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        path = urllib.parse.urlunsplit(("", "", parsed.path or "/", parsed.query, ""))
        return method, host, port, path

    host_header = _req_header(req_headers, "Host")
    if not host_header:
        return method, None, None, raw_target

    if ":" in host_header:
        host, port = host_header.rsplit(":", 1)
        try:
            port = int(port)
        except ValueError:
            port = 80
    else:
        host, port = host_header, 80

    return method, host, port, raw_target if raw_target.startswith("/") else f"/{raw_target}"


def _http_blob_from_body(body, status=b"HTTP/1.1 200 OK\r\n"):
    return status + b"Content-Length: " + str(len(body)).encode() + b"\r\n\r\n" + body


def _record_profile_slot(userhash, slot_num, body):
    if userhash is None or slot_num is None:
        return
    group = get_or_create_capture_group(userhash)
    mark_group_profile(group, True)
    write_slot_bytes(group, slot_num, _http_blob_from_body(body))


def handle_target_request(client, req, host, port, path, method):
    mode = read_state()
    m = PATH_RE.search(path)
    slot_num = int(m.group(2)) if m else None
    userhash = m.group(1) if m else None

    if method != "GET":
        raw = forward_raw(req, host, port)
        client.sendall(raw)
        if method in {"PUT", "POST"} and slot_num is not None:
            body = req.split(b"\r\n\r\n", 1)[1] if b"\r\n\r\n" in req else b""
            if body:
                _record_profile_slot(userhash, slot_num, body)
                log(f"  Saved: profile group for {userhash} slot_{slot_num} ({len(body)} bytes)")
        return

    if mode == "INJECT" and slot_num is not None:
        selection = read_selection()
        selected = read_selected_data()
        target_slot = selection.get("target_slot") if selection else None
        if selected is not None and (target_slot is None or target_slot == slot_num):
            client.sendall(selected)
            # A conditional/cache-check request from the console is the main
            # reason Show mode can silently appear to do nothing - your PS5
            # already has a cached copy of one of your slots and may not ask
            # again right away. Nothing to fix here, just worth noting.
            if _req_header(req, "If-None-Match") or _req_header(req, "If-Modified-Since") or _req_header(req, "Range"):
                log(f"  Show: sent selected emblem for slot_{slot_num}, but the console sent a "
                    "cache-check request - it may keep using its cached copy instead")
            else:
                log(f"  Show: sent selected emblem for slot_{slot_num} ({len(selected)} bytes)")
            return
        if selected is not None and target_slot is not None:
            log(f"  Show: target slot set to slot_{target_slot}; passed through slot_{slot_num}")
        else:
            log(f"  Show mode is on but no emblem is selected - passing real data through")

    headers, body = fetch_real(req, host, port)

    if mode == "CAPTURE" and slot_num is not None:
        group = get_or_create_capture_group(userhash)
        write_slot_bytes(group, slot_num, headers + body)
        log(f"  Captured: group {group} slot_{slot_num} ({len(body)} bytes)")
    elif mode == "INJECT" and slot_num is not None:
        _record_profile_slot(userhash, slot_num, body)
        log(f"  Show passthrough: recorded profile slot_{slot_num} ({len(body)} bytes)")

    client.sendall(headers + body)


def handle(client):
    try:
        initial = client.recv(4096)
        if not initial:
            client.close()
            return
        req = recv_full_request(initial, client)
        line, rest_of_req = req.split(b"\r\n", 1)
        line = line.decode("latin1")
        parts = line.split()
        if len(parts) < 2:
            client.close()
            return
        method = parts[0].upper()

        if method == "CONNECT":
            host, _, port = parts[1].partition(":")
            if "demonware" in host.lower() and config.TARGET_HOST_SUBSTR not in host:
                log(f"  note: HTTPS traffic to {host} (not the expected emblem host '{config.TARGET_HOST_SUBSTR}') - tunneled untouched")
            port = int(port or 443)
            upstream = socket.create_connection((host, port))
            client.sendall(b"HTTP/1.1 200 Connection established\r\n\r\n")
            t1 = threading.Thread(target=pipe, args=(upstream, client), daemon=True)
            t2 = threading.Thread(target=pipe, args=(client, upstream), daemon=True)
            t1.start(); t2.start()
            t1.join(); t2.join()
        else:
            _, host, port, path = _parse_http_target(line, req)
            if not host or not port or not path:
                client.close()
                return

            new_line = f"{method} {path} HTTP/1.1\r\n".encode("latin1")
            req_rewritten = new_line + rest_of_req

            if config.TARGET_HOST_SUBSTR in host:
                handle_target_request(client, req_rewritten, host, port, path, method)
            else:
                if "demonware" in host.lower():
                    log(f"  note: HTTP request to {host}{path} (not the expected emblem host '{config.TARGET_HOST_SUBSTR}') - passed through untouched")
                client.sendall(forward_raw(req_rewritten, host, port))
    except Exception as e:
        log(f"  error: {e}")
    finally:
        client.close()


def serve(host=None, port=None):
    """Run the proxy loop. Blocks forever - call from a dedicated thread."""
    from .state import write_state
    if not os.path.exists(config.STATE_FILE):
        write_state("PASSTHROUGH")
    host = host or config.PROXY_HOST
    port = port or config.PROXY_PORT
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, port))
    srv.listen(200)
    log(f"Proxy listening on {host}:{port}  mode={read_state()}")
    while True:
        client, _ = srv.accept()
        threading.Thread(target=handle, args=(client,), daemon=True).start()
