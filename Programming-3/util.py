from enum import Enum

class TestErrorCode(Enum):
    TEST_ERROR_NONE = 0
    TEST_ERROR_HTTP_CONNECT_FAILED = 1
    TEST_ERROR_HTTP_SEND_FAILED = 2
    TEST_ERROR_PARSE_PARTIAL = 3
    TEST_ERROR_PARSE_FAILED = 4

class GraphNode:
    def __init__(self, data):
        self.data = data
        self.children = []

class Graph:
    def __init__(self):
        self.root = GraphNode("")

    def findNode(self, node, data):
        if node.data == data:
            return node
        for t in node.children:
            foundNode = self.findNode(t, data)
            if foundNode is not None:
                return foundNode
        return None
                
    def insertNode(self, parent, childNode):
        parentNode = self.findNode(self.root, parent)
        exists = False
        for child in parentNode.children:
            if child.data == childNode.data:
                exists = True
                break
        if not exists:
            parentNode.children.append(childNode)

    def bfs_traverse(self):
        output = []
        queue = [self.root]

        while len(queue) > 0:
            curNode = queue.pop(0)
            if curNode != self.root:
                output.append(curNode.data)

            if len(curNode.children):
                for childNode in curNode.children:
                    queue.append(childNode)
        return output
