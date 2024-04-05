import socket
from icecream import ic

BUF_SIZE = 1024

def split_header_content(data):
    header_end = data.find(b'\r\n\r\n') + 4  # Find the end of header (including \r\n\r\n)
    return data[:header_end], data[header_end:]

def main():

    server_ip = '127.0.0.1'
    server_port = 20080

    try: 
        clientSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
    except socket.error as err: 
        print ("socket creation failed with error %s" %(err))


    clientSock.connect((server_ip, server_port))

    request = "POST /bigfile.test HTTP/1.1\r\nContent-Length: 10\r\n\r\nname=Ethan"
    # request = "GET/test_visual/index.htmlHTTP/1.1\r\n\r\n"

    clientSock.send(request.encode())

    recvData = b''  # Initialize empty bytes object to store received data
    total_received = 0  # Initialize total received bytes counter
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
            # ic(end_of_line_index)
            if end_of_line_index >= 0:
                # Extract the substring containing the value of Content-Length
                content_length_str = recvData[content_length_index:end_of_line_index]
                # print(content_length_str)
                # Split the string to get the value after the colon
                content_length_value = content_length_str.split(b':')[1].strip()
                # Convert the value to an integer
                content_length = int(content_length_value)

                # Check if total received bytes is greater than or equal to content length
                if total_received >= content_length:
                    break  # Exit the loop once enough data has been received
        if "HEAD" in request and b'\r\n\r\n' in recvData:
            break
        print(recvData)

    # Split header and content
    header_data, content_data = split_header_content(recvData)

    with open("fired.head", 'wb') as f:
        f.write(header_data)
    
    with open("fired.out", 'wb') as f:
        f.write(content_data)
    
    clientSock.close()

if __name__ == "__main__":
    main()