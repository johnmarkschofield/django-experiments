from django.conf import settings

import redis
from redis.exceptions import ConnectionError, ResponseError

import logging
logger = logging.getLogger()
logger.debug('Loading counters.py')
print('debug version of loading counters.py')

REDIS_HOST = getattr(settings, 'EXPERIMENTS_REDIS_HOST', 'localhost')
REDIS_PORT = getattr(settings, 'EXPERIMENTS_REDIS_PORT', 6379)
REDIS_PASSWORD = getattr(settings, 'EXPERIMENTS_REDIS_PASSWORD', None)
REDIS_EXPERIMENTS_DB = getattr(settings, 'EXPERIMENTS_REDIS_DB', 0)
logger.debug('Instantiating redis')
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD, db=REDIS_EXPERIMENTS_DB)
logger.debug('Done connecting to redis.')


COUNTER_CACHE_KEY = 'experiments:participants:%s'
COUNTER_FREQ_CACHE_KEY = 'experiments:freq:%s'

def increment(key, participant_identifier, count=1):
    logger.debug('incrementing a record')
    if count == 0:
        return

    try:
        cache_key = COUNTER_CACHE_KEY % key
        freq_cache_key = COUNTER_FREQ_CACHE_KEY % key
        new_value = r.hincrby(cache_key, participant_identifier, count)

        # Maintain histogram of per-user counts
        if new_value > count:
            r.hincrby(freq_cache_key, new_value - count, -1)
        r.hincrby(freq_cache_key, new_value, 1)
    except (ConnectionError, ResponseError):
        # Handle Redis failures gracefully
        logger.debug('django-experiments failure 1')
        pass

def clear(key, participant_identifier):
    try:
        # Remove the direct entry
        cache_key = COUNTER_CACHE_KEY % key
        pipe = r.pipeline()
        freq, _ = pipe.hget(cache_key, participant_identifier).hdel(cache_key, participant_identifier).execute()

        # Remove from the histogram
        freq_cache_key = COUNTER_FREQ_CACHE_KEY % key
        r.hincrby(freq_cache_key, freq, -1)
    except (ConnectionError, ResponseError):
        logger.debug('django-experiments failure 2')
        # Handle Redis failures gracefully
        pass

def get(key):
    try:
        cache_key = COUNTER_CACHE_KEY % key
        return r.hlen(cache_key)
    except (ConnectionError, ResponseError):
        logger.debug('django-experiments failure 3')
        # Handle Redis failures gracefully
        return 0

def get_frequency(key, participant_identifier):
    try:
        cache_key = COUNTER_CACHE_KEY % key
        freq = r.hget(cache_key, participant_identifier)
        return int(freq) if freq else 0
    except (ConnectionError, ResponseError):
        logger.debug('django-experiments failure 4')
        # Handle Redis failures gracefully
        return 0

def get_frequencies(key):
    try:
        freq_cache_key = COUNTER_FREQ_CACHE_KEY % key
        # In some cases when there are concurrent updates going on, there can
        # briefly be a negative result for some frequency count. We discard these
        # as they shouldn't really affect the result, and they are about to become
        # zero anyway.
        return dict((int(k),int(v)) for (k,v) in r.hgetall(freq_cache_key).items() if int(v) > 0)
    except (ConnectionError, ResponseError):
        logger.debug('django-experiments failure 5')
        # Handle Redis failures gracefully
        return tuple()

def reset(key):
    try:
        cache_key = COUNTER_CACHE_KEY % key
        r.delete(cache_key)
        freq_cache_key = COUNTER_FREQ_CACHE_KEY % key
        r.delete(freq_cache_key)
        return True
    except (ConnectionError, ResponseError):
        logger.debug('django-experiments failure 6')
        # Handle Redis failures gracefully
        return False

def reset_pattern(pattern_key):
    #similar to above, but can pass pattern as arg instead
    try:
        cache_key = COUNTER_CACHE_KEY % pattern_key
        for key in r.keys(cache_key):
            r.delete(key)
        freq_cache_key = COUNTER_FREQ_CACHE_KEY % pattern_key
        for key in r.keys(freq_cache_key):
            r.delete(key)
        return True
    except (ConnectionError, ResponseError):
        logger.debug('django-experiments failure 7')
        # Handle Redis failures gracefully
        return False
