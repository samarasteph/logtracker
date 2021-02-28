#!/usr/bin/env python3.6

"""
    filenotifier module: notify registered client about changes on files
    (see Unix inotify for more information)
"""

import os.path
import io
import logging
import traceback
import re

# pylint: disable=import-error
import inotify.adapters
import logtracker
from logtracker.event import Service, ServiceHandler

class FileNotifierWarning(Exception):
    """ FileNotifierWarning: non critical error  """
    def __init__(self, obj, msg):
        super().__init__(msg)
        self._source = obj

    def get_source(self):
        return self._source

    source = property(fget=get_source)

class FileDeleted(FileNotifierWarning):
    """ file deleted """
    def __init__(self, obj, msg):
        super().__init__(obj, msg)

class FileNotifierEvent:
    """
        FileNotifierService event to be used with EventManager
        FileNotifierEvent should be registered with  EventManager.register_event
    """

    def __init__(self, event):
        """ constructor """
        (_, type_name, path, filename) = event

        path = "" if path is None else path

        if len(path) > 0 and len(filename) == 0:
            filename = path
        elif len(path) > 0 and len(filename) > 0:
            filename = os.path.join(path, filename)
        self._filename = filename
        self._file_events = []
        self._file_state = None

        if isinstance(type_name, list):
            for evt in type_name:
                self._file_events.append(evt)
        else:
            self._file_events.append(type_name)

    def get_filename(self):
        """
            filename notified
            :return: name of the file
        """
        return self._filename

    filename = property(fget=get_filename)

    def get_events(self):
        """ return file events list """
        return self._file_events

    events = property(fget=get_events)

    def get_state(self):
        """ getter property state """
        return self._file_state

    def set_state(self, state):
        """ setter property state """
        self._file_state = state

    state = property(fget=get_state, fset=set_state)

class FileState:
    """
        FileState records notification sent by FileNotifierService to be able
        to retrieve relevant information about file modifications.
    """
    LOGGER = logging.getLogger('logtracker.filenotifier.FileState')
    INIT_EV = "IN_INIT"
    MODIFY_EV = "IN_MODIFY"
    CLOSE_WR_EV = "IN_CLOSE_WRITE"
    CLOSE_NO_WRITE_EV = "IN_CLOSE_NO_WRITE"
    OPEN_EV = "IN_OPEN"
    ACCESS_EV = "IN_ACCESS"
    MOVE_SELF_EV = "IN_MOVE_SELF"
    ATTRIB_EV = "IN_ATTRIB"
    DELETE_SELF_EV = "IN_DELETE_SELF"
    IGNORED_EV = "IN_IGNORED"
    BUFFER_MIN_SIZE = 1024

    def __init__(self, file_obj: object):
        self._file_path = file_obj.path
        #line separator
        self._line_sep = file_obj.pattern
        self._start = self.update_pos()
        self._pos = self._start
        self._state = FileState.INIT_EV
        self._dirty = False
        self._buffer = bytearray(FileState.BUFFER_MIN_SIZE)

        self._start -= 256 if  self._pos > 256 else self._pos
        self._buffer = self._pos



    def update_pos(self) -> int:
        """ return current position in file stream """

        if not os.path.exists(self._file_path):
            raise FileNotFoundError('File %s not found' % self._file_path)
        pos = 0
        with open(self._file_path, 'r') as fdesc:
            fdesc.seek(0, 2)
            pos = fdesc.tell()

        return pos

    def on_event(self, file_event: FileNotifierEvent):
        """ get events from FileNotifierService """
        for ev_item in file_event.events:
            if ev_item == FileState.MODIFY_EV:
                self._state = FileState.MODIFY_EV
                self._dirty = True

            elif ev_item == FileState.CLOSE_WR_EV:
                self._state = FileState.CLOSE_WR_EV
                pos = self.update_pos()
                if pos > self._pos:
                    self._pos = pos
                else:
                    FileState.LOGGER.warning("File '%s' current pos(%d) < previous pos(%d)",
                                             self._file_path, pos, self._pos)
            elif ev_item == FileState.DELETE_SELF_EV:
                self._state = FileState.DELETE_SELF_EV
                self._pos = -1 # file deleted, no more watched
                FileState.LOGGER.warning("File %s has been deleted", self._file_path)
                raise FileDeleted("File deleted", self)

    def extract(self, byte_obj: bytearray) -> int:
        """
            read current mofification and copy it in the byte_obj
            :param byte_obj: bytearray
            :return: number of bytes read
        """

        file = io.FileIO(self._file_path)
        file.seek(self._start, io.SEEK_SET)
        buf = io.BufferedReader(file)
        byte_obj.extend(buf.read(self._pos-self._start))

        return len(byte_obj)

    def split(self, content: bytearray):
        """ split the bytes using pattern as separator"""
        try:
            rx = re.compile(self._line_sep)
            
        except:
            FileState.LOGGER.error("RegExp '%s' raise error. check syntax.", self._line_sep)
            return


    def move_next(self):
        """ update start cursor with head position """
        self._start = self._pos

    @property
    def last_event(self):
        """ get last event from FileNotifyService """
        return self._state

    @property
    def file_path(self):
        """ return file path of registered file """
        return self._file_path


# pylint: disable=abstract-method
class FileNotifierService(Service):
    """
        FileNotifierService watch files modification using inotify Unix mechanism.
    """
    LOGGER = logging.getLogger('logtracker.event.FileNotifierService')

    def __init__(self, file_list, callb):
        """
            Constructor. take file list with file paths to watch.
        """
        super().__init__()
        self._file_list = file_list
        self._running = False
        self._callback = callb
        self._states = {file.path: FileState(file) for file in file_list}

    @ServiceHandler.onstart
    def prepare_start(self):
        """
            Start loop watching files modification
        """
        if not self._running:
            self._running = True
            FileNotifierService.LOGGER.info("Starting file FileNotifierService")
            FileNotifierService.LOGGER.info("file list: %s",
                                            str([file.path for file in self._file_list]))
        else:
            raise RuntimeError("Service already running")

    @ServiceHandler.onstop
    def service_stopped(self):
        """
            Stop loop
        """
        if self._running:
            self._running = False
            FileNotifierService.LOGGER.info("Stopping file FileNotifierService")
        else:
            FileNotifierService.LOGGER.warning("FileNotifierService already running")

    @ServiceHandler.run
    def runloop(self):
        """
            run event loop for watching files. Do not call directly, use FileNotifierService.start()
        """
        try:
            i = inotify.adapters.Inotify([file.path for file in self._file_list])

            while self._running:
                for event in i.event_gen(yield_nones=False, timeout_s=1):
                    if self._callback:
                        try:
                            ev_data = FileNotifierEvent(event)

                            if ev_data.filename in self._states:
                                ev_data.state = self._states[ev_data.filename]
                                ev_data.state.on_event(ev_data)

                            self._callback(ev_data)
                        except FileDeleted as fde:
                            file_state = fde.source
                            FileNotifierService.LOGGER.info("File %s is removed from watchlist",
                                                            file_state.file_path)
                            i.remove_watch(file_state.file_path)
                            del self._states[file_state.file_path]

        except Exception as ex:
            FileNotifierService.LOGGER.error('%s in loop: %s:\n %s',
                                             str(type(ex)), str(ex),
                                             traceback.format_exc())
            raise logtracker.CriticalError(str(FileNotifierService.__class__.__name__), \
                                           "Stop application")

        return 0
