# Import necessary modules
import socket
import os
import csv
import argparse
import ipaddress
import select
from time import sleep
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
    half_length = len(request) // 2
    first_half = request[:half_length]
    second_half = request[half_length:]
    clientSock.send(first_half.encode())
    sleep(0.5)
    clientSock.send(second_half.encode())
        
    recvData = b''
    total_received = 0
    delimiter_found = False
    while True:
        chunk = clientSock.recv(BUF_SIZE)
        # print(chunk)
        if not chunk:
            break
        recvData += chunk
        if not delimiter_found:
            delimiter_index = recvData.find(b'\r\n\r\n')  # Find the position of the delimiter
            if delimiter_index != -1:
                total_received = len(recvData) - (delimiter_index + len(b'\r\n\r\n'))  # Update total received bytes counter
                delimiter_found = True
        else:
            total_received += len(chunk)

        # Check if the received data contains the Content-Length header
        if b'Content-Length:' in recvData:
            # Find the position of the Content-Length header
            content_length_index = recvData.find(b'Content-Length:')
            # Find the end of the line after the Content-Length header
            end_of_line_index = recvData.find(b'\r\n', content_length_index)
            if end_of_line_index >= 0:
                # Extract the substring containing the value of Content-Length
                content_length_str = recvData[content_length_index:end_of_line_index]
                # Split the string to get the value after the colon
                content_length_value = content_length_str.split(b':')[1].strip()
                # Convert the value to an integer
                content_length = int(content_length_value)

                # Check if total received bytes is greater than or equal to content length
                if total_received >= content_length:
                    break  # Exit the loop once enough data has been received

    # Split header and content
    header_data, content_data = split_header_content(recvData)
    
    with open(dep + ".head", 'wb') as f:
        f.write(header_data)
    
    with open(dep, 'wb') as f:
        f.write(content_data)
    
    clientSock.close()

# Function to split received data into HTTP header and content
def split_header_content(data):
    header_end = data.find(b'\r\n\r\n') + 4  # Find the end of the header
    return data[:header_end], data[header_end:]

# Entry point of the script
if __name__ == '__main__':
    main()
