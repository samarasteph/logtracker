#!/usr/bin/env python3.6

"""
    Test for logtracker.event.Service
"""

import time
import asyncio
import logging
import pytest
from logtracker.event import Service, ServiceHandler, Manager as EventManager

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

HANDLER = logging.FileHandler("test_service.log")
LOGGER = logging.getLogger('test.service')
LOGGER.addHandler(HANDLER)
LOGGER.setLevel(logging.WARNING)

class Event1:
    """ event type for testing event.Manager """

    def __init__(self, msg: str):
        self._msg = msg

    @property
    def msg(self) -> str:
        return self._msg

    def __str__(self):
        return 'Event1(msg="%s")' % self._msg

    def __repr__(self):
        return str(self)

class Event2:
    """ other event type for testing event.Manager """

    def __init__(self, msg: str, number: int):
        self._msg = msg
        self._number = number

    @property
    def msg(self) -> str:
        return self._msg

    @property
    def number(self) -> int:
        return self._number

    def __str__(self):
        return 'Event2(msg="%s", number=%d)' % (self._msg, self._number)

    def __repr__(self):
        return str(self)

class EventStop:
    """ final event tot stop Manager from its loop """
    def __init__(self, event_manager):
        self._event_manager = event_manager

    @property
    def manager(self):
        return self._event_manager

async def send_event1(manager):
    LOGGER.info('send_event1 starting')
    ev1 = Event1("First msg")
    manager.post_event(ev1)
    LOGGER.info('\tEvent1 %s sent', str(ev1))
    await asyncio.sleep(1)
    ev1 = Event1("Second msg")
    manager.post_event(ev1)
    LOGGER.info('\tEvent1 %s sent', str(ev1))
    await asyncio.sleep(1)
    ev1 = Event1("Third msg")
    manager.post_event(ev1)
    LOGGER.info('\tEvent1 %s sent', str(ev1))
    LOGGER.info('send_event1 done')

async def send_event2(manager):
    LOGGER.info('send_event2 starting')
    await asyncio.sleep(1)
    ev2 = Event2("First msg", 10)
    manager.post_event(ev2)
    LOGGER.info('\tEvent2 %s sent', str(ev2))
    await asyncio.sleep(1)
    ev2 = Event2("Second msg", 20)
    manager.post_event(ev2)
    LOGGER.info('\tEvent2 %s sent', str(ev2))
    await asyncio.sleep(1)
    ev2 = Event2("Third msg", 30)
    manager.post_event(ev2)
    LOGGER.info('\tEvent2 %s sent', str(ev2))
    LOGGER.info('send_event2 done')

async def send_stop(manager):
    LOGGER.info('send_stop starting')
    ev_stop = EventStop(manager)
    await asyncio.sleep(4)
    manager.post_event(ev_stop)
    LOGGER.info('send_stop done')

def call_stop(event_stop):
    event_stop.manager.stop()
    LOGGER.info('call_stop done')

def test_manager():
    """ test event.Manager """

    lst_events1 = []
    lst_events2 = []

    class Callb:
        def __init__(self, lst_events):
            self.lst_events = lst_events
        def __call__(self, event):
            self.lst_events.append(event)

    event_manager = EventManager()
    event_manager.register_event(Event1, Callb(lst_events1))
    event_manager.register_event(Event2, Callb(lst_events2))
    event_manager.register_event(EventStop, call_stop)

    asyncio.get_event_loop().run_until_complete(
        asyncio.gather(
            send_event1(event_manager),
            send_event2(event_manager),
            send_stop(event_manager),
            event_manager.run()))

    assert len(lst_events1) == 3
    assert len(lst_events2) == 3

    assert lst_events1[0].msg == "First msg"
    assert lst_events1[1].msg == "Second msg"
    assert lst_events1[2].msg == "Third msg"

    assert lst_events2[0].msg == "First msg"  and lst_events2[0].number == 10
    assert lst_events2[1].msg == "Second msg" and lst_events2[1].number == 20
    assert lst_events2[2].msg == "Third msg"  and lst_events2[2].number == 30

if __name__ == "__main__":
    sc = ServiceChild()
    sc.docall_onrun()
    print(sc._started, sc._stopped, sc._ran)
    print('end main')