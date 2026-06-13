import hashlib
class ConsistentHashRing:
    def __init__(self,virtual_nodes=150):
        self.virtual_nodes=virtual_nodes
        self.ring={}
        self.sorted_keys=[]
        self.nodes=set()

    def add_node(self,node_id):
        self.nodes.add(node_id)

        for i in range(self.virtual_nodes):
            virtual_key=f"{node_id}:virtual:{i}"
            position=self._hash(virtual_key)
            self.ring[position]=node_id
            self.sorted_keys.append(position)

        self.sorted_keys.sort()
        print(f"Node {node_id} added with {self.virtual_nodes} virtual positions")

    def remove_node(self,node_id):
        self.nodes.discard(node_id)

        for i in range(self.virtual_nodes):
            virtual_key=f"{node_id}:virtual:{i}"
            position=self._hash(virtual_key)

            if position in self.ring:
                del self.ring[position]

            if position in self.sorted_keys:
                self.sorted_keys.remove(position)
            
        print(f"Node {node_id} removed from ring")

    def _hash(self,key):
        hash_value=hashlib.md5(key.encode()).hexdigest()
        return int(hash_value,16)%(2**32)

    def get_node(self,url):
        if not self.ring:
            return None
        
        position=self._hash(url)

        for ring_position in self.sorted_keys:
            if position<=ring_position:
                return self.ring[ring_position]
            
        return self.ring[self.sorted_keys[0]]
    
    def get_all_nodes(self):
        return list(self.nodes)
    
    def get_node_count(self):
        return len(self.nodes)

