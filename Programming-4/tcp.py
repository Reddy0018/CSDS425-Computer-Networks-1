import packet
import grading
import time
from enum import Enum
import socket
import ipaddress
from scapy.all import Raw


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
            for seq in list(self.unAckedPackets):
                if seq < ack_num:
                    packet, send_time = self.unAckedPackets.pop(seq)
                    sample_rtt = time.time() - send_time
                    if self.ERTT is None:  # Initialize ERTT and DEV
                        self.ERTT = sample_rtt
                        self.DEV = sample_rtt / 2
                    else:
                        self.ERTT = 0.875 * self.ERTT + 0.125 * sample_rtt
                        self.DEV = 0.75 * self.DEV + 0.25 * abs(sample_rtt - self.ERTT)
                    self.RTO = self.ERTT + 4 * self.DEV
            self.sendBase = ack_num
            # Remove acknowledged packets from unAckedPackets
            for seq in list(self.unAckedPackets):
                if seq < ack_num:
                    del self.unAckedPackets[seq]

    def add_packet_to_window(self, seq_num, packet):
        # if not self.is_window_full():
        #     self.unAckedPackets[seq_num] = packet
        #     self.nextSeqNum += len(packet.data)
        payload_length = len(packet[Raw].load) if Raw in packet else 0
        if not self.is_window_full():
            self.unAckedPackets[seq_num] = packet
            self.nextSeqNum += payload_length

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