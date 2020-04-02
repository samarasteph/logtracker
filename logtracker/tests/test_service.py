#!/usr/bin/env python3.6

"""
    Test for logtracker.event.Service
"""

import time
import pytest
from logtracker.event import Service, ServiceHandler

# pylint: disable=missing-function-docstring, missing-class-docstring, too-few-public-methods

class NotServiceDerived:
    def docall_onstart(self):
        pass

    def docall_onstop(self, res):
        pass

    def docall_run(self):
        pass

class ServiceChild(Service):
    def __init__(self):

        super().__init__()
        self._nb = 0
        self._started = 0
        self._stopped = 0
        self._ran = 0
        self._res = None
        self._args = None
        self._onstart_args = None

    @ServiceHandler.onstart
    def docall_onstart(self, *args):
        self._nb += 1
        self._started = self._nb
        self._onstart_args = args

    @ServiceHandler.onstop
    def docall_onstop(self):
        self._nb += 1
        self._stopped = self._nb

    @ServiceHandler.run
    def docall_run(self, *args):
        self._nb += 1
        self._ran = self._nb
        self._args = args
        time.sleep(1)
        return self._ran ** 2

class ServiceChildWithArgs(ServiceChild):

    def __init__(self):
        super().__init__()
        self._args = None
        self._run_method_called = False

    @ServiceHandler.run
    def run_method(self, *args):
        self._run_method_called = True
        self.docall_run(*args)
        return " ".join(args)

    def get_args(self):
        return self._args

def test_exception():
    svc = Service()
    with pytest.raises(NotImplementedError):
        svc.run()

    with pytest.raises(TypeError):
        # pylint: disable=too-few-public-methods, unused-variable
        shandler = ServiceHandler.onstart(NotServiceDerived.docall_onstart)
        shandler.__set_name__(NotServiceDerived, 'docall_onstart')

    with pytest.raises(TypeError):
        # pylint: disable=too-few-public-methods, unused-variable
        shandler = ServiceHandler.onstop(NotServiceDerived.docall_onstop)
        shandler.__set_name__(NotServiceDerived, 'docall_onstop')

    with pytest.raises(TypeError):
        # pylint: disable=too-few-public-methods, unused-variable
        shandler = ServiceHandler.run(NotServiceDerived.docall_run)
        shandler.__set_name__(NotServiceDerived, 'docall_run')


def test_service_handler():
    svc = ServiceChild()
    svc.start()
    res = svc.stop()
    #pylint: disable=protected-access
    assert svc._started == 1
    assert svc._ran == 2
    assert svc._stopped == 3
    assert svc._args is not None and len(svc._args) == 0
    assert res == 4

def test_service_handler_with_args():
    svc = ServiceChildWithArgs()
    svc.start("asinus", "stultus", "est")
    res = svc.stop()
#pylint: disable=protected-access
    assert svc._started == 1
    assert svc._ran == 2
    assert svc._stopped == 3
    assert svc._run_method_called
    assert svc._args is not None and len(svc._args) == 3
    assert svc._onstart_args is not None and len(svc._onstart_args) == 3
    assert res == "asinus stultus est"


if __name__ == "__main__":
    sc = ServiceChild()
    sc.docall_onrun()
    print(sc._started, sc._stopped, sc._ran)
    print('end main')