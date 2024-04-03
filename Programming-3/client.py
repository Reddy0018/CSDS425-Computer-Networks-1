import socket
import os
import csv
import argparse
import ipaddress
import select
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
    #clientSock.setblocking(0)

    uri = "/test_dependency"
    dependencyPath = os.getcwd() + "/www" + uri

    method = "GET"
    dependencies = read_csv_data(dependencyPath+"/dependency.csv")
    sendReq(clientSock,dependencies,method,uri)
    clientSock.close()


import select  # Import the select module

def sendReq(clientSock, dependencies, method, uri):
    for dep in dependencies:
        #request = f"{method} {uri}/{dep} HTTP/1.1\r\nHost: {args.server_ip}\r\nConnection: close\r\n\r\n"
        request = method+" " + uri+ "/"+dep + " HTTP/1.1\r\nContent-Length: 0\r\n\r\n"
        print("req: "+request)
        
        # Reconnect if necessary (for each dependency if the connection is not kept alive)
        try:
            clientSock.send(request.encode())
        except BrokenPipeError:
            clientSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            clientSock.connect((args.server_ip, HTTP_PORT))
            clientSock.send(request.encode())
        
        recvData = b''
        while True:
            try:
                chunk = clientSock.recv(BUF_SIZE)
                if not chunk:
                    break  # No more data, stop reading
                recvData += chunk
            except socket.error as e:
                print(f"Socket error: {e}")
                break
        
        if recvData:
            header_data, content_data = split_header_content(recvData)
            with open(dep + ".head", 'wb') as f:
                f.write(header_data)
            with open(dep, 'wb') as f:
                f.write(content_data)


def split_header_content(data):
    header_end = data.find(b'\r\n\r\n') + 4  # Find the end of header (including \r\n\r\n)
    return data[:header_end], data[header_end:]

if __name__ == '__main__':
    main()
