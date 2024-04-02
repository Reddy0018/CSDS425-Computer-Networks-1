import socket
import os
import csv
import argparse
import ipaddress
from util import TestErrorCode
#TODO import necessary library


HTTP_PORT = 20080
BUF_SIZE = 4096

parser = argparse.ArgumentParser()
parser.add_argument(dest="server_ip",action='store', help='server ip address')
args = parser.parse_args()

def read_csv_data(file_path):
    dependencies = []
    with open(file_path, newline='') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            # Assuming every row has exactly two elements: file and its dependency
            if len(row) >=1 :  # To ensure the row has two elements
                dependencies.append((row[0].strip()))
            else:  # For rows that might not have a dependency or are formatted differently
                dependencies.append((row[0].strip(), None))
    return dependencies

def main():
    try:
        clientSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except socket.error as e:
        return TestErrorCode.TEST_ERROR_HTTP_CONNECT_FAILED

    try:
        ipaddress.ip_address(args.server_ip)
    except ValueError:
        print("ip address is invalid, ", args.server_ip)

    try:
        clientSock.connect((args.server_ip, HTTP_PORT))
    except socket.error as e:
        return TestErrorCode.TEST_ERROR_HTTP_CONNECT_FAILED
    clientSock.setblocking(0)

    uri = "/test_dependency"
    dependencyPath = os.getcwd() + "www" + uri

    method = "GET"
    dependencies = read_csv_data(dependencyPath+"/dependency.csv")
    for dep in dependencies:
        request = method+" " + uri+ "/"+dep + " HTTP/1.1\r\nContent-Length: 0\r\n\r\n"
        print("req: "+request)
        sendReq(request,clientSock)

    #request = method+" " + uri + " HTTP/1.1\r\nContent-Length: 0\r\n\r\n"
    #clientSock.send(request.encode())
    

    #TODO: send HTTP requests

def sendReq(request,clientSock):
    clientSock.send(request.encode())
    recvData = b''  # Initialize empty bytes object to store received data
    total_received = 0
    delimiter_found = False
    while True:
        chunk = clientSock.recv(BUF_SIZE)
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
        if args.method == "HEAD" and b'\r\n\r\n' in recvData:
            break
    
    header_data, content_data = split_header_content(recvData)
    
    with open(args.output + ".head", 'wb') as f:
        f.write(header_data)
    
    with open(args.output, 'wb') as f:
        f.write(content_data)
    
    clientSock.close()

def split_header_content(data):
    header_end = data.find(b'\r\n\r\n') + 4  # Find the end of header (including \r\n\r\n)
    return data[:header_end], data[header_end:]

if __name__ == '__main__':
    main()
