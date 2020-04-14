#!/usr/bin/env python3.6

"""
    Service base class impl and events associated
"""

import concurrent.futures
import asyncio
import logging

# pylint: disable=invalid-name, too-few-public-methods, useless-super-delegation

class ServiceHandler:
    """
        class decorator to define handlers to be called when service start and stop are called
    """

    def __init__(self, fnc):
        """
            constructor

            :param cls: class type deriving from service
        """
        self._fnc = fnc

    def __set_name__(self, owner, name):
        #print('__set_name__', owner, name, self)
        if not issubclass(owner, Service):
            raise TypeError(f"Class {owner.__name__} is not a child of Service")

        setattr(owner, name, self._fnc)

    @classmethod
    def set_service_method(cls, owner, func):
        """ set class function name with name of decorator """
        setattr(owner, cls.__name__, func)

class onstart(ServiceHandler):
    """
        decorator to indicate function must be called in Service.start
        :return: decorated method
    """

    def __init__(self, fnc):
        super().__init__(fnc)

    def __set_name__(self, owner, name):
        super().__set_name__(owner, name)
        type(self).set_service_method(owner, self._fnc)

class onstop(ServiceHandler):
    """
        decorator to indicate function must be called in Service.stop
        :return: decorated method
    """

    def __init__(self, fnc):
        super().__init__(fnc)

    def __set_name__(self, owner, name):
        super().__set_name__(owner, name)
        type(self).set_service_method(owner, self._fnc)

class run(ServiceHandler):
    """
        decorator of method to be ran when service is running as background task
        :return: decorated method
    """
    def __init__(self, fnc):
        super().__init__(fnc)

    def __set_name__(self, owner, name):
        super().__set_name__(owner, name)
        type(self).set_service_method(owner, self._fnc)

ServiceHandler.onstart = onstart
ServiceHandler.onstop = onstop
ServiceHandler.run = run


class Service:
    """
    	Base class for service implementation: a service run a background method which gets
        inputs or to output events. These mechanism are achieved with asyncio loops
	"""
    THREAD_POOL = concurrent.futures.ThreadPoolExecutor(max_workers=10)

    def __init__(self):
        """
            constructor
        """
        self._future = None

    # pylint: disable=missing-function-docstring
    def onstart(self, *args):
        pass

    def onstop(self):
        pass

    def start(self, *args):
        """
            start the service
        """
        self.onstart(*args)
        self._future = Service.THREAD_POOL.submit(self.run, *args)

    def stop(self):
        """
            stop the service
        """
        self.onstop()
        return self._future.result()

    def run(self, *args):
        """
            default method to execute as service background task
            should be overriden by child class
        """
        raise NotImplementedError("methode run has to be overriden by child class")

class Manager:
    """
        run event loop. components can register callbacks with particular event types then
        post messages to be consumed in the event loop
    """

    LOOP = asyncio.get_event_loop()
    LOGGER = logging.getLogger('logtracker.event.Manager')

    def __init__(self):
        """
           Constructor
        """
        self._event_registry = dict()
        self._queue = asyncio.Queue()
        self._loop = False

    def stop(self):
        """ Stop manager when running """
        self._loop = False
        Manager.LOGGER.info('Stop Event Manager')
        self.post_event(None)

    def post_event(self, event_obj: object):
        """ post event asynchronously in event queue """
        self._queue.put_nowait(event_obj)

    async def run(self):
        """
            run method: start event loop as coroutine (async)
        """
        if self._loop:
            raise "Event Manager Already started\n"

        self._loop = True

        Manager.LOGGER.info('Start Manager run loop')
        while self._loop:
            event_obj = await self._queue.get()

            Manager.LOGGER.info('Event: %s', event_obj)

            if type(event_obj) in self._event_registry:
                for callback in self._event_registry[type(event_obj)]:
                    if asyncio.iscoroutine(callback):
                        callback.send(event_obj)
                    else:
                        callback(event_obj)

            self._queue.task_done()

    def register_event(self, event_type, callback):
        """
            register event and associated callback
            :param event_type: type object representing event (class object, built-in type)
            :param callback: callback associated with event_type to be called at runtime
        """
        if event_type and event_type not in self._event_registry:
            self._event_registry[event_type] = []

        self._event_registry[event_type].append(callback)

    def unregister_event(self, event_type, callback):
        """
            unregister event_type and its callback associated
            :param event_type: type of the event
        """
        if event_type in self._event_registry:
            l = self._event_registry[event_type]
            if callback in l:
                l.remove(callback)
                if len(l) == 0:
                    del self._event_registry[event_type]
