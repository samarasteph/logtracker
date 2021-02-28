#!/usr/bin/env python3.6

""" module logtracker """

class CriticalError(Exception):
    """ Critical error encountered, should stop application """
    def __init__(self, component, msg):
        """ 
            constructor 
            :param component: component or service name
            :param msg: error message
        """
        super().__init__(msg)
        self._component = component

    def __str__(self):
        return "CriticalError: %s" % str(self._component)
        #Exception.__str__(self)

