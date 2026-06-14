import redis
import hashlib

class DistributedBloomFilter:
    def __init__(self,redis_host='localhost', redis_port=6379,capacity=1000000,error_rate=0.01):
        self.redis=redis.Redis(host=redis_host,port=redis_port,decode_responses=True, protocol=2)
        self.capacity=capacity
        self.error_rate=error_rate
        self.bit_size=self._get_bit_size(capacity,error_rate)
        self.hash_count=self._get_hash_count(self.bit_size,capacity)
        self.key="nightcrawler:bloom_filter"
        print(f"Bloom filter ready - {self.bit_size} bits, {self.hash_count} hash functions")

    def _get_bit_size(self,capacity,error_rate):
        import math
        return int(-capacity*math.log(error_rate)/(math.log(2)**2))

    def _get_hash_count(self,bit_size,capacity):
        import math
        return max(1, int((bit_size/capacity)*math.log(2)))

    def _get_bit_positions(self,url):
        positions=[]
        for i in range(self.hash_count):
            hash_input=f"{url}:{i}".encode()
            hash_value=int(hashlib.md5(hash_input).hexdigest(),16)
            position=hash_value%self.bit_size
            positions.append(position)
        return positions
    
    def add(self,url):
        positions=self._get_bit_positions(url)
        pipe=self.redis.pipeline()
        for position in positions:
            pipe.setbit(self.key,position,1)
        pipe.execute()

    def might_exist(self,url):
        positions=self._get_bit_positions(url)
        pipe=self.redis.pipeline()
        for position in positions:
            pipe.getbit(self.key,position)
        results=pipe.execute()
        return all(results)
    
    def clear(self):
        self.redis.delete(self.key)
        print("Bloom filter cleared")

if __name__ == "__main__":
    bf = DistributedBloomFilter()
    
    print("\nAdding URLs to bloom filter...")
    urls_to_add = [
        "https://arxiv.org/abs/1706.03762",
        "https://arxiv.org/abs/2005.14165",
        "https://arxiv.org/abs/1810.04805",
    ]
    
    for url in urls_to_add:
        bf.add(url)
        print(f"Added: {url[-20:]}")
    
    print("\nChecking URLs...")
    test_urls = [
        "https://arxiv.org/abs/1706.03762",  # added — should return True
        "https://arxiv.org/abs/2005.14165",  # added — should return True
        "https://arxiv.org/abs/9999.99999",  # never added — should return False
        "https://google.com",                # never added — should return False
    ]
    
    for url in test_urls:
        exists = bf.might_exist(url)
        status = "SEEN BEFORE — skip" if exists else "NEW — scrape this"
        print(f"{url[-20:]} → {status}")
    
    bf.clear()