# Import necessary modules
import socket
import os
import csv
import argparse
import ipaddress
import select
from util import TestErrorCode

# Define constants for HTTP port and buffer size for socket communication
HTTP_PORT = 20080
BUF_SIZE = 4096

# Setup command-line argument parsing
parser = argparse.ArgumentParser()
parser.add_argument(dest="server_ip", action='store', help='server IP address')
args = parser.parse_args()

# Function to read data from a CSV file, expecting each row to have at least one column
def read_csv_data(file_path):
    dependencies = []
    with open(file_path, newline='') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if len(row) >= 1:  # Ensure the row has at least one element
                dependencies.append((row[0].strip()))
            else:  # Handle rows that might be formatted differently or lack a dependency
                dependencies.append((row[0].strip(), None))
    return dependencies

# Main function where the script starts executing
def main():
    try:
        # Attempt to create a socket object
        clientSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except socket.error as e:
        return TestErrorCode.TEST_ERROR_HTTP_CONNECT_FAILED

    try:
        # Validate the provided server IP address
        ipaddress.ip_address(args.server_ip)
    except ValueError:
        print("IP address is invalid, ", args.server_ip)

    try:
        # Connect to the server using the provided IP address and HTTP port
        clientSock.connect((args.server_ip, HTTP_PORT))
    except socket.error as e:
        return TestErrorCode.TEST_ERROR_HTTP_CONNECT_FAILED
    #clientSock.setblocking(0)

    uri = "/test_dependency"  # Hardcoding the path as requirement is unclear
    dependencyPath = os.getcwd() + "/www" + uri

    method = "GET"
    dependencies = read_csv_data(dependencyPath + "/dependency.csv")
    sendReq(clientSock, dependencies, method, uri)
    clientSock.close()

# Function to send HTTP requests for each dependency
def sendReq(clientSock, dependencies, method, uri):
    for dep in dependencies:
        request = method+" " + uri+ "/"+dep + " HTTP/1.1\r\nContent-Length: 0\r\n\r\n"
        print("req: "+request)
        
        # Reconnect if necessary and send the request
        try:
            clientSock.send(request.encode())
        except BrokenPipeError:
            # If the connection is broken, create a new socket and reconnect
            clientSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            clientSock.connect((args.server_ip, HTTP_PORT))
            clientSock.send(request.encode())
        
        recvData = b''
        while True:
            try:
                # Receive data from the server
                chunk = clientSock.recv(BUF_SIZE)
                if not chunk:
                    break  # Stop reading if no more data
                recvData += chunk
            except socket.error as e:
                print(f"Socket error: {e}")
                break
        
        # If data was received, split it into header and content, and save to files
        if recvData:
            header_data, content_data = split_header_content(recvData)
            with open(dep + ".head", 'wb') as f:
                f.write(header_data)
            with open(dep, 'wb') as f:
                f.write(content_data)

# Function to split received data into HTTP header and content
def split_header_content(data):
    header_end = data.find(b'\r\n\r\n') + 4  # Find the end of the header
    return data[:header_end], data[header_end:]

# Entry point of the script
if __name__ == '__main__':
    main()
