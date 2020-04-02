#!/usr/bin/env python3.6

"""
    Config unit testing
"""

import os.path

# pylint: disable=no-name-in-module, wrong-import-position
from logtracker.config import Config

# pylint: disable=no-member

CURDIR = os.path.dirname(os.path.realpath(__file__))

def test_config1():
    """
        test complete config with non default values
    """
    conf = Config(os.path.join(CURDIR, "cfg1.yaml"))
    assert conf.server is not None
    assert conf.server.http is not None
    assert conf.server.http.host is not None
    assert conf.server.http.host == '0.0.0.0'
    assert conf.server.http.port is not None
    assert conf.server.http.port == 8907
    assert conf.server.http.ssl is not None
    assert conf.server.http.ssl == 1
    assert conf.server.http.cert is not None
    assert conf.server.http.cert == "/etc/cert"
    assert conf.server.websocket is not None
    assert conf.server.websocket.port is not None
    assert conf.server.websocket.port == 9907
    assert conf.logs is not None
    assert conf.logs.folder is not None
    assert conf.logs.folder == "/tmp/logs"
    assert conf.logs.prefix is not None
    assert conf.logs.prefix == "lg"
    assert conf.files is not None
    assert len(conf.files) == 1
    file = conf.files[0]
    assert file.path is not None
    assert file.path == "/var/log/syslog"
    assert file.pattern is not None
    assert file.pattern == r"\[.+\]"
    assert file.color is not None
    assert file.color == "auto"

def test_config2():
    """
        test default value(s) if property(ies) missing
    """
    conf = Config(os.path.join(CURDIR, "cfg2.yaml"))
    assert conf.server is not None
    assert conf.server.http is not None
    assert conf.server.http.host is not None
    assert conf.server.http.host == 'localhost'
    assert conf.server.http.port is not None
    assert conf.server.http.port == 8906
    assert conf.server.http.ssl is not None
    assert conf.server.http.ssl == 0
    assert conf.server.http.cert is not None
    assert conf.server.http.cert == ""
    assert conf.server.websocket is not None
    assert conf.server.websocket.port is not None
    assert conf.server.websocket.port == 9906
    assert conf.logs is not None
    assert conf.logs.folder is not None
    print('logs=%s' % conf.logs.folder)
    assert conf.logs.folder == "/tmp"
    assert conf.logs.prefix is not None
    assert conf.logs.prefix == ""
    assert conf.files is not None
    assert len(conf.files) == 2
    file = conf.files[0]
    assert file.path is not None
    assert file.path == "/var/log/syslog"
    assert file.pattern is not None
    assert file.pattern == "\n"
    assert file.color is not None
    assert file.color == "auto"
    file = conf.files[1]
    assert file.path is not None
    assert file.path == "/var/log/Xorg.0.log"
    assert file.pattern is not None
    assert file.pattern == r"\(Entry .+\)"
    assert file.color is not None
    assert file.color == "blue"

if __name__ == "__main__":
    test_config1()