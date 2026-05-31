# handle_random_seed.py

import logging
import numpy as np

logger = logging.getLogger(__name__)


def handle_random_seed(seed=None):

    if seed is None:
        random_seed = np.random.random() * 2**32
        logger.info('Generated random seed: %s', random_seed)
    else:
        random_seed = seed
        logger.info('Prompted random seed: %s', random_seed)

    return random_seed
