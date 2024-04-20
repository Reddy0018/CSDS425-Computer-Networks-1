from tcp import Socket, Window, SocketType, SockaddrIn, ReadMode
from backend import begin_backend, single_send
import socket
from packet import create_packet
from threading import Thread, Lock, Condition
from scapy.all import Raw
import time

EXIT_SUCCESS = 0
EXIT_ERROR = 1
EXIT_FAILURE = 1

def case_socket(sock, sockType, port, serverIP):
    sockfd = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sockFd = sockfd
    sock.recvLock = Lock()
    sock.sendLock = Lock()
    sock.deathLock = Lock()
    sock.sockType = sockType
    sock.window = Window()
    # TODO: to be updated
    sock.window.nextSeqExpected = 0
    sock.window.lastAckReceived = 0

    sock.waitCond = Condition(sock.recvLock)

    if sockType == SocketType.TCP_INITIATOR:
        sock.conn = SockaddrIn(serverIP, socket.ntohs(port))
        sockfd.bind(('', 0))

    elif sockType == SocketType.TCP_LISTENER:
        sock.conn = SockaddrIn(socket.INADDR_ANY, socket.htons(port))
        sockfd.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sockfd.bind(('', port))

    else:
        print("Unknown Flag")
        return EXIT_ERROR

    myAddr, myPort = sockfd.getsockname()
    sock.myPort = socket.ntohs(myPort)

    t = Thread(target=begin_backend, args=(sock,), daemon=True)
    sock.thread = t
    t.start()
    return EXIT_SUCCESS

def case_close(sock):
    sock.deathLock.acquire()
    try:
        sock.dying = 1
    finally:
        sock.deathLock.release()

    sock.thread.join()

    if sock is not None:
        sock.receivedBuf = b""
        sock.sendingBuf = b""

    else:
        print("Error null socket")
        return EXIT_ERROR
    
    sock.sockFd.close()
    return EXIT_SUCCESS

def case_read(sock, buf, length, flags):
    readLen = 0
    if length < 0:
        print("ERROR negative length")
        return EXIT_ERROR

    if flags == ReadMode.NO_FLAG:
        with sock.waitCond:
            while sock.receivedLen == 0:
                sock.waitCond.wait()

    sock.recvLock.acquire()
    if flags == ReadMode.NO_WAIT or flags == ReadMode.NO_FLAG:
        if sock.receivedLen > 0:
            if sock.receivedLen > length:
                readLen = length
            else:
                readLen = sock.receivedLen

            buf[0] = sock.receivedBuf

            if readLen < sock.receivedLen:
                sock.receivedLen -= readLen
                sock.receivedBuf = sock.receivedBuf[readLen:]

            else:
                sock.receivedBuf = b""
                sock.receivedLen = 0
    elif flags != ReadMode.NO_FLAG and flags != ReadMode.NO_WAIT:
        print("ERROR Unknown flag")
        readLen = EXIT_ERROR

    sock.recvLock.release()
    return readLen

def case_write(sock, buf, length):
    with sock.sendLock:
        while length > 0 and not sock.window.is_window_full():
            packet_size = min(length, sock.window.windowSize - (sock.window.nextSeqNum - sock.window.sendBase))
            packet_data = buf[:packet_size]
            send_time = time.time()
            packet = create_packet(
                src=sock.myPort,  # Source port
                dst=socket.ntohs(sock.conn.sinPort),  # Destination port
                seq=sock.window.nextSeqNum,  # Sequence number
                ack=sock.window.lastAckReceived,  # Ack number
                hLen=20,  # Header length
                pLen=20 + len(packet_data),  # Total packet length
                flags=0,  # TCP flags
                advWin=sock.window.windowSize,  # Advertised window size
                extData=None , # No extension data
                payload=packet_data,  # Payload
                payloadLen=len(packet_data)  # Payload length
            )
            sock.receivedLen=20 + len(packet_data)
            sock.receivedBuf+=bytes(packet_data,encoding='utf8')

            sock.window.unAckedPackets[sock.window.nextSeqNum] = (packet, send_time)  # Store packet and send time
            if packet is None:
                advWin=sock.window.windowSize,  # Advertised window
                extData=None,  # Extension data if any
                payload=packet_data,  # Payload
                payloadLen=len(packet_data)  # Payload length
            if packet is None:
                print("Failed to create packet.")
                return EXIT_FAILURE  # Define EXIT_FAILURE if not already defined

            print("Packet created successfully:", packet)  # Optional: Remove after debugging

            sock.window.add_packet_to_window(sock.window.nextSeqNum, packet)
            single_send(sock, packet,sock.sendingLen)
            length -= packet_size
            buf = buf[packet_size:]
    return EXIT_SUCCESS

def add_packet_to_window(self, seq_num, packet):
    # Check for Raw layer and get payload length
    payload_length = len(packet[Raw].load) if Raw in packet else 0
    if not self.is_window_full():
        self.unAckedPackets[seq_num] = packet
        self.nextSeqNum += payload_length

def handle_ack(sock, ack_num):
    sock.window.slide_window(ack_num)