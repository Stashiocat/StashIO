import heapq
import time

class TimedCountQueue():
    def __init__(self):
        self.__queue = []
        self.__count = 0
        
    def add(self, count, time_until_expire):
        self.__count += count
        heapq.heappush(self.__queue, [time.time() + time_until_expire, count])
        
    def get_count(self):
        t = time.time()
        # prune the entires that are expired
        for i in range(len(self.__queue)):
            if self.__queue[0][0] < t:
                self.__count -= self.__queue[0][1]
                heapq.heappop(self.__queue)
                continue
            break
        return self.__count

class DelayQueue():
    def __init__(self):
        self.__queue = []
        
    def add(self, data, time_until_expire):
        heapq.heappush(self.__queue, [time.time() + time_until_expire, data])
        
    def to_list(self):
        return [[self.__queue[i][0], self.__queue[i][1].get()] for i in range(len(self.__queue))]
        
    def pop(self):
        t = time.time()
        out = []
        for i in range(len(self.__queue)):
            if self.__queue[0][0] < t:
                out.append(self.__queue[0][1])
                heapq.heappop(self.__queue)
                continue
            break
        return out

class TimedCountDataQueue():
    def __init__(self):
        self.__queue = []
        self.__count = 0
        
    def add(self, data, count, time_until_expire):
        self.__count += count
        heapq.heappush(self.__queue, [time.time() + time_until_expire, count, data])
        
    def get_count(self, data_match=None):
        t = time.time()
        # prune the entires that are expired
        for i in range(len(self.__queue)):
            if self.__queue[0][0] < t:
                self.__count -= self.__queue[0][1]
                heapq.heappop(self.__queue)
                continue
            break
        
        if data_match:
            data_count = 0
            for i in range(len(self.__queue)):
                if self.__queue[i][2] == data_match:
                    data_count += self.__queue[i][1]
            return data_count
            
        # return the global count if we're not data matching
        return self.__count
