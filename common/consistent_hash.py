import hashlib
import bisect


class ConsistentHashRing:
    def __init__(self, virtual_nodes=150):
        self.virtual_nodes = virtual_nodes
        self.ring = {}           # position -> node_id
        self.sorted_keys = []    # sorted list of positions
        self.nodes = set()

    def add_node(self, node_id):
        self.nodes.add(node_id)
        for i in range(self.virtual_nodes):
            virtual_key = f"{node_id}:virtual:{i}"
            position = self._hash(virtual_key)
            self.ring[position] = node_id
            bisect.insort(self.sorted_keys, position)   # O(log n) insert
        print(f"[ring] Node {node_id} added with {self.virtual_nodes} virtual positions")

    def remove_node(self, node_id):
        if node_id not in self.nodes:
            return
        self.nodes.discard(node_id)
        for i in range(self.virtual_nodes):
            virtual_key = f"{node_id}:virtual:{i}"
            position = self._hash(virtual_key)
            if position in self.ring:
                del self.ring[position]
                # O(log n) search + O(n) removal — acceptable for infrequent node changes
                idx = bisect.bisect_left(self.sorted_keys, position)
                if idx < len(self.sorted_keys) and self.sorted_keys[idx] == position:
                    self.sorted_keys.pop(idx)
        print(f"[ring] Node {node_id} removed from ring")

    def get_node(self, url):
        if not self.ring:
            return None
        position = self._hash(url)
        # Find the first ring position >= url's position (clockwise lookup)
        idx = bisect.bisect_left(self.sorted_keys, position)
        if idx == len(self.sorted_keys):
            idx = 0   # wrap around
        return self.ring[self.sorted_keys[idx]]

    def _hash(self, key):
        hash_value = hashlib.md5(key.encode()).hexdigest()
        return int(hash_value, 16) % (2 ** 32)

    def get_all_nodes(self):
        return list(self.nodes)

    def get_node_count(self):
        return len(self.nodes)