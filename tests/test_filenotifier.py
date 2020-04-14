#!/usr/bin/env python3.6

"""
    FileNotifierService unit tests
"""

import os
import os.path
import queue
import logging

# pylint: disable=import-error, wrong-import-position
import logtracker.filenotifier
from logtracker.event import Service, ServiceHandler
import tests.utils

TEST_NAME = 'test_filenotifier'
tests.utils.setup_logger(TEST_NAME)
LOGGER = tests.utils.get_logger('test_filenotifier')

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
    def change_files(lst_files):
        flname = lst_files[0]
        tests.utils.write_file(flname, "line1\n")
        tests.utils.write_file(flname, "line2\n")

        flname = lst_files[1]
        tests.utils.write_file(flname, "line1\n")
        tests.utils.write_file(flname, "line2\n")
        tests.utils.write_file(flname, "line3\n")

    @staticmethod
    def test_filechange():
        # pylint: disable=attribute-defined-outside-init
        LOGGER.info("start test")
        lst_files = ["f1.txt", "f2.txt"]

        tests.utils.delete_files(lst_files)
        tests.utils.create_files(lst_files)

        runsvc = LoopService()

        fnotifier = logtracker.filenotifier.FileNotifierService(lst_files, runsvc.on_event)
        fnotifier.start()

        runsvc.start()

        TestFileNotifier.change_files(lst_files)

        LOGGER.info('Stop notifier loop %s', str(fnotifier.stop()))
        LOGGER.info('Stop test loop %s', str(runsvc.stop()))

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

        tests.utils.delete_files(lst_files)

    @staticmethod
    def test_filestate():
        file_name = "f1.txt"
        lines = [
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            "Integer a tortor a enim condimentum egestas a eu ex.",
            "Cras euismod libero nec dapibus tincidunt.",
            "Proin sit amet ex et eros iaculis malesuada.",
            "Praesent et quam et eros hendrerit ultricies hendrerit ac odio.",
            "Aliquam luctus augue eu sagittis congue.",
            "Maecenas in sapien varius felis dictum dapibus."
        ]
        tests.utils.delete_files([file_name])
        tests.utils.create_files([file_name])

        tests.utils.write_file(file_name, lines[0])
        tests.utils.end_line(file_name)

        notify_event = logtracker.filenotifier.FileState.CLOSE_WR_EV

        file_event = logtracker.filenotifier.FileNotifierEvent((
            None, notify_event, None, file_name))

        assert file_event.filename == file_name
        assert isinstance(file_event.events, list) and len(file_event.events) == 1

        state = logtracker.filenotifier.FileState(file_name)

        tests.utils.write_file(file_name, lines[1])
        state.on_event(file_event)

        assert state.last_event == notify_event

        barray = bytearray()
        res = state.extract(barray)
        state.move_next()
        assert res == len(lines[1])
        assert barray.decode('utf-8') == lines[1]

        tests.utils.end_line(file_name)
        tests.utils.write_file(file_name, lines[2])
        state.on_event(file_event)

        assert state.last_event == notify_event

        barray.clear()
        assert len(barray) == 0
        res = state.extract(barray)

        assert res == len(lines[2])+1 # extra '\n'
        assert barray.decode('utf-8') == '\n' + lines[2]
        state.move_next()

        tests.utils.delete_files([file_name])
