from pritunl.plugins.utils import *
from pritunl.plugins import example

from pritunl import callqueue
from pritunl import settings
from pritunl import logger

import imp
import os

_queue = None
_has_plugins = False
_handlers = {}

def init():
    global _queue
    global _has_plugins
    global _handlers

    _queue = callqueue.CallQueue(maxsize=settings.app.plugin_queue_size)
    _queue.start(settings.app.plugin_queue_threads)
    _has_plugins = True
    call_types = set(get_functions(example).keys())

    modules = []
    plugin_dir = settings.app.plugin_directory

    if not os.path.exists(plugin_dir):
        return

    for file_name in os.listdir(plugin_dir):
        file_path = os.path.join(plugin_dir, file_name)
        file_name, file_ext = os.path.splitext(file_name)
        if file_ext != '.py':
            continue
        modules.append(imp.load_source('plugin_' + file_name, file_path))

    for module in modules:
        for call_type, handler in get_functions(module).iteritems():
            if call_type not in call_types:
                continue
            if call_type not in _handlers:
                _handlers[call_type] = [handler]
            else:
                _handlers[call_type].append(handler)

def _event(event_type, **kwargs):
    for handler in _handlers[event_type]:
        try:
            handler(**kwargs)
        except:
            logger.exception('Error in plugin handler', 'plugins',
                event_type=event_type,
            )

def event(event_type, **kwargs):
    if settings.local.sub_plan != 'enterprise':
        return
    if not _has_plugins or event_type not in _handlers:
        return
    _queue.put(_event, event_type, **kwargs)

def caller(caller_type, **kwargs):
    if not _has_plugins or caller_type not in _handlers:
        return

    returns = []
    for handler in _handlers[caller_type]:
        returns.append(handler(**kwargs))
    return returns
