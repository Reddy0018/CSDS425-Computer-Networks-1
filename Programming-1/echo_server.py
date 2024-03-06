import socket
import select
import os

ECHO_PORT = 9999
BUF_SIZE = 4096

def main():
    print("----- Echo Server (with epoll function to handle concurrent requests!) -----")
    try:
        serverSock = socket.socket() # Initializing server socket.
    except socket.error as err: # Exception handling block while trying to create a socket object.
        print ("socket creation failed with error %s" %(err))
        exit(1)
    serverSock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    serverSock.bind(('0.0.0.0', ECHO_PORT)) #Binds the socket with given IP and PORT
    serverSock.listen(5) # Will listen for incommimg requests with 5 backlog requests

    
    epoll = select.epoll() # Createing an epoll object.
    epoll.register(serverSock.fileno(), select.EPOLLIN)

    clientSocks = {} # Mapping of client sockets to their corresponding file descriptors

    while True:
        events = epoll.poll(100)

        for fileno, event in events:
            if fileno == serverSock.fileno():
                connection, addr = serverSock.accept() # Accepts new connections.
                print(f"Accepted connection from {addr}")
                connection.setblocking(False)
                epoll.register(connection.fileno(), select.EPOLLIN)
                clientSocks[connection.fileno()] = connection
            elif event & select.EPOLLIN:
                connection = clientSocks[fileno]
                data = connection.recv(BUF_SIZE) # Receives data from a client.
                if not data:
                    print(f"Closed connection from {clientSocks[fileno].getpeername()}")
                    epoll.unregister(fileno)
                    del clientSocks[fileno] # deletes the socket connection.
                else:
                    connection.send(data) # Sending data to the client.

if __name__ == '__main__':
    main()