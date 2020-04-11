#!/usr/bin/env python3.6

"""
    FileNotifier unit tests
"""

import os
import os.path
import queue
import logging

# pylint: disable=import-error, wrong-import-position
import logtracker.filenotifier
from logtracker.event import Service, ServiceHandler


HANDLER = logging.FileHandler("test_filenotifier.log")
LOGGER = logging.getLogger('test.filenotifier')
LOGGER.addHandler(HANDLER)
LOGGER.setLevel(logging.INFO)

# pylint: disable=abstract-method
class LoopService(Service):
    """ Service for file notification """
    def __init__(self):
        super().__init__()
        self._lst_events = []
        self._loop = False
        self._queue = queue.Queue()

    @property
    def events(self):
        """ get file events """
        return self._lst_events

    @ServiceHandler.onstart
    def start_loop(self):
        """ Before running service """
        LOGGER.info('Service start')
        self._loop = True

    @ServiceHandler.onstop
    def stop_loop(self):
        """ Stop loop """
        LOGGER.info('Service stop')
        self._loop = False
        self._queue = queue.Queue()

    @ServiceHandler.run
    def run_loop(self):
        """ Run loop as a service """
        LOGGER.info('Service start looping')
        while self._loop:
            try:
                evlist = self._queue.get(block=True, timeout=1)
                self._lst_events.extend(evlist)
            except queue.Empty:
                pass

    def on_event(self, file_event):
        """ Callback: get inotify events """

        LOGGER.info("INotify Event=%s File=%s", file_event.events, file_event.filename)

        lst_events = []

        for evt in iter(file_event.events):
            lst_events.append((file_event.filename, evt))

        self._queue.put_nowait(lst_events)


#pylint: disable=too-few-public-methods, missing-function-docstring
class TestFileNotifier:
    """ Test class """

    @staticmethod
    def create_files(lst_files):
        for flname in lst_files:
            with open(flname, "w") as _:
                pass

    @staticmethod
    def delete_files(lst_files):
        for flname in lst_files:
            if os.path.exists(flname):
                os.unlink(flname)

    @staticmethod
    def change_files(lst_files):
        flname = lst_files[0]

        with open(flname, "w") as fdesc:
            fdesc.write("line1\n")

        with open(flname, "w") as fdesc:
            fdesc.write("line2\n")

        flname = lst_files[1]
        with open(flname, "w") as fdesc:
            fdesc.write("line1\n")
        with open(flname, "w") as fdesc:
            fdesc.write("line2\n")
        with open(flname, "w") as fdesc:
            fdesc.write("line3\n")

    @staticmethod
    def test_filechange():
        # pylint: disable=attribute-defined-outside-init
        print("start test")
        lst_files = ["f1.txt", "f2.txt"]

        TestFileNotifier.delete_files(lst_files)
        TestFileNotifier.create_files(lst_files)

        runsvc = LoopService()

        fnotifier = logtracker.filenotifier.FileNotifier(lst_files, runsvc.on_event)
        fnotifier.start()

        runsvc.start()

        TestFileNotifier.change_files(lst_files)

        LOGGER.info('Stop notifier loop', fnotifier.stop())
        LOGGER.info('Stop test loop', runsvc.stop())

        results = dict()

        for file_ev in runsvc.events:
            filename, type_name = file_ev
            if not filename in results:
                results[filename] = {}
            if not type_name in results[filename]:
                results[filename][type_name] = 0

            results[filename][type_name] += 1

        assert len(results) == 2

        for filename in results:
            for events_name in results[filename]:
                assert   results[filename][events_name] > 1

        TestFileNotifier.delete_files(lst_files)
