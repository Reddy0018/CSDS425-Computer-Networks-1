import os
import sys
import argparse
import socket
import errno
import select

BUF_SIZE = 4096  # Allowed Buffer Size.
HTTP_PORT = 20080  # Port Number for HTTP Connection.
MAX_EVENTS = 100  # Maximum events that epoll can handle at a time.
MAX_CONNECTIONS = 100  # Maximum no of parallel allowed connections.

def main():
    parser = argparse.ArgumentParser()  # Command Line Args parser.
    parser.add_argument(dest="www_folder", action='store', help='www folder')
    args = parser.parse_args()

    wwwFolder = args.www_folder
    if not os.path.exists(wwwFolder):  # Checks if the file path provided exists or not.
        print("Unable to open www folder ", wwwFolder)
        sys.exit(os.EX_OSFILE)

    serverSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Creating TCP socket object.
    serverSock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    serverSock.bind(('0.0.0.0', HTTP_PORT))  # Port & IP to connect to the WEB server.
    serverSock.listen(MAX_CONNECTIONS)
    serverSock.setblocking(False)

    epoll = select.epoll()  # Creating epoll object for efficient I/O events.
    epoll.register(serverSock.fileno(), select.EPOLLIN)  # registering epoll events.

    try:
        connections = {}  # empty Dictionaries to track the active connections, req, res.
        requests = {}
        responses = {}

        while True:
            events = epoll.poll(MAX_EVENTS)  # Waiting for an event to occur.
            for fileno, event in events:
                if fileno == serverSock.fileno():
                    try:
                        while True:
                            client_socket, _ = serverSock.accept()  # Accepts the new connections.
                            client_socket.setblocking(False)
                            epoll.register(client_socket.fileno(), select.EPOLLIN)
                            connections[client_socket.fileno()] = client_socket
                            requests[client_socket.fileno()] = b''
                            responses[client_socket.fileno()] = b''

                            if len(connections) > MAX_CONNECTIONS:  # Handles maximum no:of connections allowed condition.
                                response = "HTTP/1.1 503 Service Unavailable\r\nContent-Type: text/plain\r\n\r\n503 Service Unavailable"
                                responses[client_socket.fileno()] = response.encode()
                                epoll.modify(client_socket.fileno(), select.EPOLLOUT)
                    except socket.error as e:  # Exception handling block
                        if e.errno != errno.EAGAIN:
                            raise
                        continue
                elif event & select.EPOLLIN:
                    data = connections[fileno].recv(BUF_SIZE)  # Receives and read data from client.
                    if data:
                        requests[fileno] += data
                        try:
                            responses[fileno] = handleHttpRequest(requests[fileno].decode(), wwwFolder).encode()  # prepares HTTP response
                        except:
                            responses[fileno] = handleHttpRequest(requests[fileno].decode(), wwwFolder)
                        epoll.modify(fileno, select.EPOLLOUT)
                    else:
                        epoll.unregister(fileno)  # Clean up after connection get's closed.
                        connections[fileno].close()
                        del connections[fileno], requests[fileno], responses[fileno]
                elif event & select.EPOLLOUT:
                    bytes_written = connections[fileno].send(responses[fileno])  # Sends response data to the client.
                    if len(responses[fileno]) == bytes_written:
                        epoll.modify(fileno, select.EPOLLIN)  # Modify to listen for new requests after responding.
                        if b'\r\n\r\n' in requests[fileno]: # Close connection for pipelining optimization
                            epoll.unregister(fileno)
                            connections[fileno].close()
                            del connections[fileno], requests[fileno], responses[fileno]
                        else:
                            requests[fileno] = b''  # Reset request buffer for new requests.

    finally:
        epoll.unregister(serverSock.fileno())  # closes the server connections on exit.
        epoll.close()
        serverSock.close()


# Parse the HTTP request, identifies the request, and generates a valid response.
def handleHttpRequest(data, wwwFolder):
    lines = data.splitlines()
    if lines:
        request_line = lines[0]
        parts = request_line.split()

        if len(parts) > 1:
            if 'index.html' in parts[1]:  # Process different types of requests (PNG, HTML, CSS, JS)
                try:
                    with open(os.getcwd() + '/' + wwwFolder + parts[1], 'r') as file:
                        content = file.read()
                    return "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n" + content
                except:
                    return "HTTP/1.1 404 Not Found\r\nContent-Type: text/plain\r\n\r\n404 Not Found.."
            elif ".png" in parts[1] or ".jpg" in parts[1] or ".mp4" in parts[1]:
                with open(os.getcwd() + '/' + wwwFolder + parts[1], 'rb') as file:
                    content = file.read()
                headers = "HTTP/1.1 200 OK\r\nContent-Type: image/png\r\n\r\n"
                return headers.encode() + content
            elif ".jpg" in parts[1] or ".JPG" in parts[1] or ".jpeg" in parts[1]:
                with open(os.getcwd() + '/' + wwwFolder + parts[1], 'rb') as file:
                    content = file.read()
                headers = "HTTP/1.1 200 OK\r\nContent-Type: image/jpeg\r\n\r\n"
                return headers.encode() + content
            elif ".mp4" in parts[1]:
                with open(os.getcwd() + '/' + wwwFolder + parts[1], 'rb') as file:
                    content = file.read()
                headers = "HTTP/1.1 200 OK\r\nContent-Type: video/mp4\r\n\r\n"
                return headers.encode() + content
            elif ".html" in parts[1]:
                try:
                    with open(os.getcwd() + '/' + wwwFolder + parts[1], 'r') as file:
                        content = file.read()
                    return "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n" + content
                except:
                    return "HTTP/1.1 404 Not Found\r\nContent-Type: text/plain\r\n\r\n404 Not Found.."
            elif ".css" in parts[1]:
                with open(os.getcwd() + '/' + wwwFolder + parts[1], 'rb') as file:
                    content = file.read()
                return "HTTP/1.1 200 OK\r\nContent-Type: text/css\r\n\r\n".encode() + content
            elif ".js" in parts[1]:
                with open(os.getcwd() + '/' + wwwFolder + parts[1],'r') as file:
                    content = file.read()
                return "HTTP/1.1 200 OK\r\nContent-Type: application/javascript\r\n\r\n" + content
            else: # Default response for unhandled resources.
                return "HTTP/1.1 404 Not Found\r\nContent-Type: text/plain\r\n\r\n404 Not Found.."
    return "HTTP/1.1 400 Bad Request\r\nContent-Type: text/plain\r\n\r\n400 Bad Request"

if __name__ == '__main__':
    main()
