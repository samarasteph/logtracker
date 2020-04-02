#!/usr/bin/env python3.6

"""
    FileNotifier unit tests
"""

import os
import os.path
import queue

# pylint: disable=import-error, wrong-import-position
import logtracker.filenotifier
from logtracker.event import Service, ServiceHandler

LOGFILE = "test_filenotifier.log"
with open(LOGFILE, "w") as _:
    pass

def log(*args):
    """ log msg """
    with open(LOGFILE, "a") as logf:
        for msg in args:
            logf.write(str(msg))
        logf.write('\n')

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
        log('Service start')
        self._loop = True

    @ServiceHandler.onstop
    def stop_loop(self):
        """ Stop loop """
        log('Service stop')
        self._loop = False
        self._queue = queue.Queue()

    @ServiceHandler.run
    def run_loop(self):
        """ Run loop as a service """
        log('Service start looping')
        while self._loop:
            try:
                evlist = self._queue.get(block=True, timeout=1)
                self._lst_events.extend(evlist)
            except queue.Empty:
                pass

    def on_event(self, file_event):
        """ Callback: get inotify events """
        (_, type_name, path, filename) = file_event
        log("INotify", type_name, path)
        if len(path) > 0 and len(filename) == 0:
            filename = path
        elif len(path) > 0 and len(filename) > 0:
            filename = os.path.join(path, filename)

        lst_events = []
        try:
            for evt in iter(type_name):
                lst_events.append((filename, evt))
        except TypeError:
            lst_events.append((filename, type_name))

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

        log('Stop notifier loop', fnotifier.stop())
        log('Stop test loop', runsvc.stop())

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
