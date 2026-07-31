import socket
import os
import json
from threading import Thread
import subprocess

PORT = 5000
NEEDS_REFRESH = False

# Directory paths relative to where this app executes
BASE_DIR = os.getcwd()
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')
PHOTOS_DIR = os.path.join(BASE_DIR, 'photos')
SENSOR_FILE = os.path.join(BASE_DIR, 'sensors.json')

def get_content_type(filepath):
    """Determine MIME types to make browsers render files accurately."""
    if filepath.endswith('.html'): return 'text/html'
    if filepath.endswith('.css'): return 'text/css'
    if filepath.endswith('.js'): return 'application/javascript'
    if filepath.endswith('.json'): return 'application/json'
    if filepath.endswith(('.jpg', '.jpeg')): return 'image/jpeg'
    if filepath.endswith('.png'): return 'image/png'
    if filepath.endswith('.gif'): return 'image/gif'
    return 'application/octet-stream'

def build_http_response(status_code, content_type, body_bytes):
    """Packages standard raw binary string packets with HTTP/1.1 headers."""
    status_text = "OK" if status_code == 200 else "Not Found"
    header = f"HTTP/1.1 {status_code} {status_text}\r\n"
    header += f"Content-Type: {content_type}\r\n"
    header += f"Content-Length: {len(body_bytes)}\r\n"
    header += "Access-Control-Allow-Origin: *\r\n" # Safe network sharing
    header += "Connection: close\r\n\r\n"
    return header.encode('utf-8') + body_bytes

def send_ok(client_socket):
    response = (
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: text/plain\r\n"
        "\r\n"
        "OK"
    )
    client_socket.sendall(response.encode())

def display_on():
    subprocess.run(["wlr-randr", "--output", "HDMI-A-2", "--on"],check=False)

def display_off():
    subprocess.run(["wlr-randr", "--output", "HDMI-A-2", "--off"],check=False)

def handle_client(client_socket):
    """Parses incoming traffic requests and dispatches targeted asset data."""
    try:
        raw_data = client_socket.recv(1024)
        if not raw_data:
            return
        try:
            request_data = raw_data.decode('utf-8')
        except UnicodeDecodeError:
            print(f"Ignoring non-UTF8 request: {raw_data[:20]}")
            return
        if not request_data:
            return
        
        # Simple extraction of target path line (e.g., GET /static/style.css HTTP/1.1)
        lines = request_data.split('\r\n')
        request_line = lines[0].split(' ')
        if len(request_line) < 2:
            return
        
        path = request_line[1]
        #print(f"Request path: {path}")
        # Router Dispatcher Matrix
        if path == '/api/check-refresh':
            # The browser loops here every 3 seconds to see if it should reload
            global NEEDS_REFRESH
            if NEEDS_REFRESH:
                body = b"true"
                NEEDS_REFRESH = False # Reset the flag once a client reads it
            else:
                body = b"false"
            response = build_http_response(200, 'text/plain', body)
            client_socket.sendall(response)
            return
        elif path == '/api/trigger-refresh':
            # Typing this URL on your remote PC will flip the flag to True
            NEEDS_REFRESH = True
            body = b"Refresh command sent to display"
            response = build_http_response(200, 'text/plain', body)
            client_socket.sendall(response)
            return
        elif path == '/' or path == '/index.html':
            target_file = os.path.join(TEMPLATES_DIR, 'index.html')
        elif path == '/config':
            target_file = os.path.join(TEMPLATES_DIR, 'config.html')
        elif path.startswith('/static/'):
            filename = path.replace('/static/', '')
            target_file = os.path.join(STATIC_DIR, filename)
        elif path.startswith('/photos/'):
            filename = path.replace('/photos/', '')
            target_file = os.path.join(PHOTOS_DIR, filename)
        elif path == '/sensors.json':
            target_file = SENSOR_FILE
        elif path == '/api/photos':
            # Dynamic API endpoint: Scans target photos directory and sends down JSON array
            try:
                files = os.listdir(PHOTOS_DIR)
                photo_list = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]
                body = json.dumps(photo_list).encode('utf-8')
                response = build_http_response(200, 'application/json', body)
            except Exception as e:
                response = build_http_response(500, 'application/json', b'{"error":"Photos error"}')
            client_socket.sendall(response)
            return
        elif path == "/api/display/on":
            display_on()
            send_ok(client_socket)
            return
        elif path == "/api/display/off":
            display_off()
            send_ok(client_socket)
            return
        else:
            target_file = None

        # Serve static file requests from target storage directories
        if target_file and os.path.exists(target_file) and os.path.isfile(target_file):
            with open(target_file, 'rb') as f:
                body = f.read()
            response = build_http_response(200, get_content_type(target_file), body)
        else:
            response = build_http_response(404, 'text/plain', b'File Not Found')
            
        client_socket.sendall(response)
    except Exception as e:
        print(f"Network handling exception: {e}")
    finally:
        client_socket.close()

def start_server():
    """Binds persistent low-level server socket listeners to port framework allocation."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('0.0.0.0', PORT))
    server.listen(5)
    print(f"Native server running on all interfaces via port {PORT}...")
    
    while True:
        client_sock, addr = server.accept()
        # Thread handles every asset request concurrently (prevents video/image loading lag)
        t = Thread(target=handle_client, args=(client_sock,))
        t.daemon = True
        t.start()

if __name__ == '__main__':
    # Build folders automatically if missing on deployment boot
    for d in [TEMPLATES_DIR, STATIC_DIR, PHOTOS_DIR]:
        if not os.path.exists(d): os.makedirs(d)
        
    if not os.path.exists(SENSOR_FILE):
        with open(SENSOR_FILE, 'w') as f: f.write('{"CPU_Temp": "45 C", "System_Load": "Minimal"}')
        
    start_server()
