import socket
import threading
import os
import time
from datetime import datetime

SERVER_HOST = '127.0.0.1'
SERVER_PORT = 8080
BASE_DIR = 'htdocs'
LOG_FILE = 'server.log'

MIME_TYPES = {
    '.html': 'text/html',
    '.htm': 'text/html',
    '.txt': 'text/plain',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.gif': 'image/gif',
    '.ico': 'image/x-icon',
}

def log_message(client_ip, method, filename, status_code):
    access_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f'{client_ip} [{access_time}] "{method} {filename}" {status_code}\n'
    with open(LOG_FILE, 'a') as f:
        f.write(log_line)
    print(log_line.strip())

def get_mime_type(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    return MIME_TYPES.get(ext, 'application/octet-stream')

def handle_client(client_socket, client_addr):
    client_ip = client_addr[0]
    client_socket.settimeout(5)
    
    try:
        while True:
            try:
                request_data = client_socket.recv(4096).decode('utf-8', errors='ignore')
                if not request_data:
                    break
            except socket.timeout:
                break
            
            lines = request_data.split('\r\n')
            if not lines:
                break
            
            first_line = lines[0].split()
            if len(first_line) < 2:
                response = b'HTTP/1.1 400 Bad Request\r\n\r\n<h1>400 Bad Request</h1>'
                client_socket.sendall(response)
                log_message(client_ip, 'UNKNOWN', 'unknown', 400)
                break
            
            method = first_line[0].upper()
            filename = first_line[1]
            
            if filename == '/':
                filename = '/index.html'
            filepath = BASE_DIR + filename
            
            if '..' in filepath:
                response = b'HTTP/1.1 403 Forbidden\r\n\r\n<h1>403 Forbidden</h1>'
                client_socket.sendall(response)
                log_message(client_ip, method, filename, 403)
                if connection_header == 'close':
                    break
                continue
            
            if_modified_since = None
            connection_header = 'close'
            for line in lines[1:]:
                if line.lower().startswith('if-modified-since:'):
                    if_modified_since = line.split(':', 1)[1].strip()
                elif line.lower().startswith('connection:'):
                    connection_header = line.split(':', 1)[1].strip().lower()
            
            content_type = get_mime_type(filepath)
            
            if not os.path.exists(filepath):
                response = b'HTTP/1.1 404 Not Found\r\nContent-Type: text/html\r\n\r\n<h1>404 Not Found</h1>'
                client_socket.sendall(response)
                log_message(client_ip, method, filename, 404)
                if connection_header == 'close':
                    break
                continue
            
            if not os.access(filepath, os.R_OK):
                response = b'HTTP/1.1 403 Forbidden\r\n\r\n<h1>403 Forbidden</h1>'
                client_socket.sendall(response)
                log_message(client_ip, method, filename, 403)
                if connection_header == 'close':
                    break
                continue
            
            stat = os.stat(filepath)
            last_modified = time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime(stat.st_mtime))
            content_length = stat.st_size
            
            if if_modified_since and if_modified_since == last_modified:
                response = b'HTTP/1.1 304 Not Modified\r\n\r\n'
                client_socket.sendall(response)
                log_message(client_ip, method, filename, 304)
                if connection_header == 'close':
                    break
                continue
            
            with open(filepath, 'rb') as f:
                body = f.read()
            
            headers = f'HTTP/1.1 200 OK\r\nContent-Type: {content_type}\r\nContent-Length: {content_length}\r\nLast-Modified: {last_modified}\r\nConnection: {connection_header}\r\n\r\n'
            
            if method == 'HEAD':
                response = headers.encode()
            else:
                response = headers.encode() + body
            
            client_socket.sendall(response)
            log_message(client_ip, method, filename, 200)
            
            if connection_header == 'close':
                break
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client_socket.close()

def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((SERVER_HOST, SERVER_PORT))
    server_socket.listen(10)
    print(f'Server running at http://{SERVER_HOST}:{SERVER_PORT}')
    print(f'Log file: {LOG_FILE}')
    print('Press Ctrl+C to stop\n')
    
    while True:
        client_socket, client_addr = server_socket.accept()
        thread = threading.Thread(target=handle_client, args=(client_socket, client_addr))
        thread.daemon = True
        thread.start()

if __name__ == '__main__':
    try:
        start_server()
    except KeyboardInterrupt:
        print('\nServer stopped.')