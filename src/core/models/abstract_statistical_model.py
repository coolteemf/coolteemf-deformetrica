import logging
import time

import torch.multiprocessing as mp

from core import default

logger = logging.getLogger(__name__)

# used as a global variable when processes are initially started.
process_initial_data = None


def _initializer(*args):
    """
    Process initializer function that is called when mp.Pool is started.
    :param args:    arguments that are to be copied to the target process. This can be a tuple for convenience.
    """
    global process_initial_data
    process_initial_data = args


class AbstractStatisticalModel:
    """
    AbstractStatisticalModel object class.
    A statistical model is a generative function, which tries to explain an observed stochastic process.
    """

    ####################################################################################################################
    ### Constructor:
    ####################################################################################################################

    def __init__(self, name='undefined', number_of_threads=default.number_of_threads):
        self.name = name
        self.fixed_effects = {}
        self.priors = {}
        self.population_random_effects = {}
        self.individual_random_effects = {}
        self.has_maximization_procedure = None

        self.number_of_threads = number_of_threads
        self.pool = None

    def _setup_multiprocess_pool(self, initargs=None):
        if self.number_of_threads > 1:
            logger.info('Starting multiprocess pool with ' + str(self.number_of_threads) + ' processes')
            start = time.perf_counter()
            self.pool = mp.Pool(processes=self.number_of_threads, maxtasksperchild=None,
                                initializer=_initializer, initargs=initargs)
            logger.info('Multiprocess pool started in: ' + str(time.perf_counter()-start) + ' seconds')

    def _cleanup_multiprocess_pool(self):
        if self.number_of_threads > 1:
            assert self.pool is not None
            self.pool.close()

    ####################################################################################################################
    ### Common methods, not necessarily useful for every model.
    ####################################################################################################################

    def cleanup(self):
        self._cleanup_multiprocess_pool()

    def clear_memory(self):
        pass

    def preoptimize(self, individual_RER):
        pass


