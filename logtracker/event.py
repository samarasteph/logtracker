#!/usr/bin/env python3.6

"""
    Service base class impl and events associated
"""

import concurrent.futures

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
        print('__set_name__', owner, name, self)
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
            should be derived by inherited class
        """
        raise NotImplementedError("methode run has to be overriden by child class")
