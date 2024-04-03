# Importing necessary libraries
import os
import sys
import argparse
import socket, select
import http_header as HttpHeader
from http_header import Request
sys.path.append('./backend/')
from parse_http import parse_http_request, serialize_http_response
import re
from datetime import datetime

# Define global constants
BUF_SIZE = 1024
HTTP_PORT = 20080
CONCURRENCY_LIMIT = 100
EOL1 = b'\n\n'
EOL2 = b'\r\n\r\n'

# Main function
def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(dest="www_folder",action='store', help='www folder')
    args = parser.parse_args()

    wwwFolder = args.www_folder
    if not os.path.exists(wwwFolder):
        print("Unable to open www folder ", wwwFolder)
        sys.exit(os.EX_OSFILE)

    # Create a socket and bind it to the specified port
    serverSock = socket.socket()
    serverSock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    serverSock.bind(('0.0.0.0', HTTP_PORT))
    serverSock.listen(CONCURRENCY_LIMIT)

    # Create an epoll object to handle multiple connections
    read_only = select.EPOLLIN | select.EPOLLPRI | select.EPOLLHUP | select.EPOLLERR
    read_write = read_only | select.EPOLLOUT
    biterrs = [25,24,8,16,9,17,26,10,18]
    epoll = select.epoll()
    epoll.register(serverSock.fileno(), read_only)

    # Generate HTTP responses for various error conditions
    msgs = []
    generate_response('503', wwwFolder + '/503.html', msgs)
    unavailable_resp = msgs.pop()

    generate_response('400', wwwFolder + '/400.html', msgs)
    bad_request_resp = msgs.pop()

    generate_response('404', wwwFolder + '/404.html', msgs)
    not_found_resp = msgs.pop()

    # Handle incoming connections
    try:
        connections = {}
        totalConns = 0
        requests = {}
        responses = {}
        overloadedConns = {}
        postReqMsgs = {}
        postRespMsgs = {}
        alive = {}
        while True:
            events = epoll.poll(1)
            for fileNo, event in events:
                if fileNo == serverSock.fileno():
                    connection, addr = serverSock.accept()
                    if totalConns == CONCURRENCY_LIMIT:
                        overloadedConns[connection.fileno()] = connection
                        epoll.register(connection.fileno(), read_only)
                    else:
                        connection.setblocking(0)
                        fileNo = connection.fileno()
                        epoll.register(fileNo, read_only)
                        connections[fileNo] = connection
                        requests[fileNo] = b''
                        responses[fileNo] = b''
                        postReqMsgs[fileNo] = []
                        postRespMsgs[fileNo] = b'' 
                        alive[fileNo] = False
                        totalConns += 1
                elif (event & select.EPOLLIN) or (event & select.EPOLLPRI):
                    try:
                        # Handle incoming data
                        if fileNo in overloadedConns:
                            recvdata = overloadedConns[fileNo].recv(BUF_SIZE)
                            overloadedConns[fileNo].send(unavailable_resp)
                            overloadedConns[fileNo].close()
                            del overloadedConns[fileNo]
                            continue
                        revdata = connections[fileNo].recv(BUF_SIZE)
                        #print(revdata)
                        if not revdata:
                            # connections[fileNo].close()
                            # epoll.unregister(fileNo)
                            # totalConns -= 1
                            # del connections[fileNo], requests[fileNo], responses[fileNo], alive[fileNo]
                            continue
                        requests[fileNo] += revdata
                        if len(postReqMsgs[fileNo]) != 0:
                            contentLength = int(postReqMsgs[fileNo][0].headers['Content-Length'])
                            if len(requests[fileNo]) >= contentLength:
                                postRespMsgs[fileNo] = requests[fileNo][:contentLength]
                                filePath = wwwFolder + postReqMsgs[fileNo][0].HttpURI
                                msgs = []
                                generate_response('200', filePath, msgs, postRespMsgs[fileNo].decode())
                                responses[fileNo] += msgs.pop()
                                postReqMsgs[fileNo].pop()
                                postRespMsgs[fileNo] = b''

                        elif EOL1 in requests[fileNo] or EOL2 in requests[fileNo]:
                            rawMsg = requests[fileNo].decode()
                            indices = [m.end() for m in re.finditer(r'(POST|GET|HEAD).*?('+EOL1.decode()+'|'+EOL2.decode()+')', rawMsg, re.MULTILINE|re.DOTALL)]
                            start = 0
                            for index in indices:
                                end = index
                                requestMsg = rawMsg[start:end]
                                request = Request()
                                parse_http_request(requestMsg, len(requestMsg), request)
                                msgs = []
                                statusCode = '400'
                                if request.Valid:
                                    if request.HttpMethod == 'POST':
                                        contentLength = int(request.headers['Content-Length'])
                                        if  contentLength > len(rawMsg) - end:
                                            postReqMsgs[fileNo].append(request)
                                            requests[fileNo] = requests[fileNo][end:]
                                        else:
                                            request.HttpBody = rawMsg[end:contentLength]
                                            requests[fileNo] = requests[fileNo][end+contentLength:]
                                    else:
                                        requests[fileNo] = rawMsg[end:].encode()
                                    if "Connection" in request.headers and request.headers["Connection"] == HttpHeader.CONNECTION_VAL:
                                        alive[fileNo] = True
                                    if request.HttpURI != '':
                                        filePath = wwwFolder + request.HttpURI
                                        if os.path.exists(filePath) and os.path.isfile(filePath):
                                            statusCode = '200'
                                            if request.HttpMethod == 'GET':
                                                generate_response(statusCode, filePath, msgs)
                                            elif request.HttpMethod == 'POST' and len(postReqMsgs[fileNo]) == 0:
                                                generate_response(statusCode, filePath, msgs, request.HttpBody)
                                            elif request.HttpMethod == 'HEAD':
                                                generate_response(statusCode, filePath, msgs, '')
                                            if len(msgs):
                                                responses[fileNo] += msgs.pop()
                                        else:
                                            statusCode = '404'
                                            responses[fileNo] += not_found_resp
                                if statusCode == '400':
                                    responses[fileNo] += bad_request_resp
                                start = end

                            # Register the file descriptor for writing if the HTTP response is ready
                            epoll.modify(fileNo, read_write)
                    except ConnectionResetError:
                        epoll.unregister(fileNo)
                        connections[fileNo].close()
                        del connections[fileNo], requests[fileNo], responses[fileNo], alive[fileNo]
                        totalConns -= 1
    
                elif event & select.EPOLLOUT:
                    try:
                        # Send the HTTP response
                        byteswritten = connections[fileNo].send(responses[fileNo])
                        responses[fileNo] = responses[fileNo][byteswritten:]
                        if len(responses[fileNo]) == 0:
                            if alive[fileNo]:
                                epoll.modify(fileNo, read_only)
                            else:
                                epoll.unregister(fileNo)
                                connections[fileNo].close()
                                del connections[fileNo], requests[fileNo], responses[fileNo], alive[fileNo]
                                totalConns -= 1
                    except ConnectionResetError:
                        epoll.unregister(fileNo)
                        connections[fileNo].close()
                        del connections[fileNo], requests[fileNo], responses[fileNo], alive[fileNo]
                        totalConns -= 1
                elif event in biterrs:
                    epoll.unregister(fileNo)
                    connections[fileNo].close()
                    del connections[fileNo], requests[fileNo], responses[fileNo], alive[fileNo]
                    totalConns -= 1

    finally:
        # Clean up
        epoll.unregister(serverSock.fileno())
        epoll.close()
        serverSock.close()

    sys.exit(os.EX_OK)

# Function to generate an HTTP response
def generate_response(statusCode, filePath, msgs, msgBody=None):
    # Generate the appropriate HTTP headers based on the status code
    if statusCode == '200':
        prepopulatedHeaders = HttpHeader.OK
    if statusCode == '404':
        prepopulatedHeaders = HttpHeader.NOT_FOUND
    if statusCode == '400':
        prepopulatedHeaders = HttpHeader.BAD_REQUEST
    if statusCode == '503':
        prepopulatedHeaders = HttpHeader.SERVICE_UNAVAILABLE

    # Read the file and set the Content-Type and Content-Length headers
    if not msgBody:
        f = open(filePath, 'rb')
        body = f.read()
        f.close()
        contentType = get_content_type(filePath.split('/')[-1])
    else:
        body = msgBody.encode()
        contentType = HttpHeader.HTML_MIME
    contentLength = str(len(body))

    # Set the Last-Modified header to the current time
    lastModified = get_current_time()

    # Serialize the HTTP response
    serialize_http_response(msgs, prepopulatedHeaders, contentType, contentLength, lastModified, body)

# Function to get the Content-Type of a file based on its extension
def get_content_type(fileName):
    ext = fileName.rsplit('.',1)[-1]
    if ext == HttpHeader.HTML_EXT:
        return HttpHeader.HTML_MIME
    elif ext == HttpHeader.CSS_EXT:
        return HttpHeader.CSS_MIME
    elif ext == HttpHeader.PNG_EXT:
        return HttpHeader.PNG_MIME
    elif ext == HttpHeader.JPG_EXT:
        return HttpHeader.JPG_MIME
    elif ext == HttpHeader.GIF_EXT:
        return HttpHeader.GIF_MIME
    else:
        return HttpHeader.OCTET_MIME

# Function to get the current time
def get_current_time():
    currentDateAndTime = datetime.now()
    currentTime = currentDateAndTime.strftime("%a, %d %b %Y %H:%M:%S GMT")
    return currentTime

# Call the main function
if __name__ == '__main__':
    main()