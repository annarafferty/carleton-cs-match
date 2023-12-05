import hashlib
import random

class PriorityDictionary:
    '''
    A PriorityDictionary P allows for the mapping of keys to priority values,
    which are consistent from call to call.  That is,
       P.getPriority(x) returns a priority for a hashable object x
    where the same priority is returned if x's priority is re-queried.
    
    When debugging is on, priority is computed via md5.
    When debugging is off, priority is assigned truly randomly.
    '''
    def __init__(self, debug=True, seed=None):
        self.priorityDictionary = {}
        if debug:
            self.priorityCalculator = lambda x : hashlib.md5(x.encode('utf-8')).hexdigest()
        else:
            self.priorityCalculator = lambda _ : random.random()

        if (seed):
            random.seed(seed)
        
    def getPriority(self, s):
        if s not in self.priorityDictionary:
            self.priorityDictionary[s] = self.priorityCalculator(s)
        return self.priorityDictionary[s]


