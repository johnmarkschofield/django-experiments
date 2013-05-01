import logging

from django.conf import settings

from modeldict import ModelDict
from djangofu.general import get_env_variable

from experiments.models import Experiment

logger = logging.getLogger(get_env_variable('LOGROOT') + '.' + __name__)

logger.debug('Creating experiment_manager')
experiment_manager = ModelDict(Experiment, key='name', value='value', instances=True, auto_create=getattr(settings, 'EXPERIMENTS_AUTO_CREATE', True))
logger.debug('Done creating experiment_manager')
