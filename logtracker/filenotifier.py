#!/usr/bin/env python3.6

import asyncio
# pytest: disable=import-error
import inotify.adapters
from logtracker.event import Service, ServiceHandler

class FileNotifierEvent:
    """
        FileNotifier event to be used with EventManager
        FileNotifier event should be registered with  EventManager.register_event
    """

    def __init__(self, event):
        """ constructor """
        (_, type_name, path, filename) = event
        if len(path) > 0 and len(filename) == 0:
            filename = path
        elif len(path) > 0 and len(filename) > 0:
            filename = os.path.join(path, filename)
        self._filename = filename
        self._file_events = []

        try:
            for evt in iter(type_name):
                self._file_events.append(evt)
        except TypeError:
            self._file_events.append(type_name)

    def get_filename(self):
        """
            filename notified
            :return: name of the file
        """
        return self._filename

    filename = property(get_filename)

    def get_events(self):
        """ return file events list """
        return self._file_events

    events = property(get_events)

class FileNotifier(Service):
    """
        FileNotifier watch files modification using inotify Unix mechanism.
    """
    def __init__(self, file_list, callb):
        """
            Constructor. take file list with file paths to watch.
        """
        super().__init__()
        self._file_list = file_list
        self._running = False
        self._callback = callb

    @ServiceHandler.onstart
    def prepare_start(self):
        """
            Start loop watching files modification
        """
        if not self._running:
            self._running = True
        else:
            raise RuntimeError("Service already running")

    @ServiceHandler.onstop
    def service_stopped(self):
        """
            Stop loop
        """
        if self._running:
            self._running = False

    @ServiceHandler.run
    def runloop(self):
        """
            run event loop for watching files. Do not call directly, use FileNotifier.start()
        """
        i = inotify.adapters.Inotify(self._file_list)
        while self._running:
            try:
                for event in i.event_gen(yield_nones=False, timeout_s=1):
                    if self._callback:
                        self._callback(FileNotifierEvent(event))
            except Exception as ex:
                print ('Exception in loop', str(type(ex)), str(ex), '\n', ex.__traceback__)
                return 1
        del i
        return 0

if __name__ == "__main__":
    import os.path
    import time
    FILES = ["exp.txt", "search.txt", "test-vi.txt", "vimtest.txt"]
    FILES = [os.path.join("/home/albert/temp", file) for file in FILES]
    LOOP = asyncio.new_event_loop()

    def callback(event):
        (_, type_names, path, filename) = event
        print("PATH=[{}] FILENAME=[{}] EVENT_TYPES={}"
                          .format(path, filename, type_names))

    FW = FileNotifier(FILES, LOOP, callback)

    try:
        print('start loop')
        FW.start()
        LOOP.run_forever()
    except KeyboardInterrupt:
        print('CTRL+C pressed')
        FW.stop()
        time.sleep(2)
    finally:
        LOOP.close()
        print('End of main')
