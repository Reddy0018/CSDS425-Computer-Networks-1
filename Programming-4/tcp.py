import packet
import grading
from enum import Enum
import socket
import ipaddress


class Window(object):
    def __init__(self, window_size=1024):
        self.windowSize = window_size
        self.sendBase = 0
        self.nextSeqNum = 0
        self.unAckedPackets = {}

    def is_window_full(self):
        return (self.nextSeqNum - self.sendBase) >= self.windowSize

    def slide_window(self, ack_num):
        if ack_num > self.sendBase:
            self.sendBase = ack_num
            # Remove acknowledged packets from unAckedPackets
            for seq in list(self.unAckedPackets):
                if seq < ack_num:
                    del self.unAckedPackets[seq]

    def add_packet_to_window(self, seq_num, packet):
        if not self.is_window_full():
            self.unAckedPackets[seq_num] = packet
            self.nextSeqNum += len(packet.data)

class SocketType(Enum):
    TCP_INITIATOR = 0
    TCP_LISTENER = 1

class SockaddrIn(object):
    sinFamily = socket.AF_INET
    sinPort = 0
    sinAddr = '0.0.0.0'

    def __init__(self, addr=None, port=None):
        if addr is not None:
            self.sinAddr = addr
        if port is not None:
            self.sinPort = port

class Socket(object):
    sockFd = None
    thread = None
    myPort = None
    conn = None
    receivedBuf = b""
    receivedLen = 0
    recvLock = None
    waitCond = None
    sendingBuf = b""
    sendingLen = 0
    sockType = None
    sendLock = None
    dying = 0
    deathLock = None
    window = None

class ReadMode(Enum):
    NO_FLAG = 0
    NO_WAIT = 1
    TIMEOUT = 2