#!/usr/bin/env python3.6

""" logtracker module """

class CriticalError(Exception):
    """ Error stopping application  """
    def __init__(self, component, msg):
        super().__init__(msg)
        self._component = component

    def get_component(self):
        """ return component from which exception raised """
        return self._component

    component = property(fget=get_component)
