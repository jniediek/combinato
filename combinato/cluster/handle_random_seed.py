# handle_random_seed.py

import numpy as np
from time import strftime

def handle_random_seed(seed=None):
    
    log_file='session_random_seed.txt'
    
    if(seed is None):
        # Generate a random seed
        random_seed = np.random.random() * 2**32
        print(f"Generated random seed: {random_seed}")
    else:
        random_seed = seed
        print(f"Prompted random seed: {random_seed}")
    
    # Log the random seed to the log file
    with open(log_file, 'a') as f:
        f.write('{} | {}\n'.format(strftime('%Y-%m-%d_%H-%M-%S'), random_seed))
    
    return random_seed
