#!/usr/bin/env python3.6

import logging
import os
import os.path
import yaml

class ConfigException(Exception):
    """ Exception for config error """

# pylint: disable=too-few-public-methods
class Config:
    """
        Config class: store in memory config parameters loaded from yaml file
    """
    #YAML Tags
    DEFAULT_HOST = "localhost"
    DEFAULT_HTTP_PORT = 8906
    DEFAULT_WS_PORT = 9906
    DEFAULT_WS_URL  = 'ws://localhost'
    DEFAULT_LOG_FOLDER = "/tmp"
    DEFAULT_HTML_FOLDER = 'logtracker/html'

    # pylint: disable=C0326
    SERVER_TAG = 'server'
    HTTP_TAG   = 'http'
    HTML_TAG   = 'html'
    WS_TAG     = 'websocket'
    WS_URL_TAG = 'url'
    HOST_TAG   = 'host'
    PORT_TAG   = 'port'
    SSL_TAG    = 'ssl'
    CERT_TAG   = 'cert'
    LOGS_TAG   = 'logs'
    LOGS_FOLDER_TAG = 'folder'
    LOGS_PREFIX_TAG = 'prefix'
    FILES_TAG  = 'files'
    FILES_PATH_TAG = 'path'
    FILES_PATTERN_TAG = 'pattern'
    FILES_COLOR_TAG = 'color'

    COLORS= [ "blue", "red", "orange", "yellow", "green", "pink", "purple", "black", "grey" ]
    #config singleton
    CONFIG = None

    def __init__(self, yaml_file):
        """
            Constructor. Load configuration and set itself properties
            :param yaml_file: YAML configuration file path
        """
        config = None

        # pylint: disable=C0103
        with open(yaml_file,'r') as fd:
            config = yaml.safe_load(fd)
        if Config.SERVER_TAG not in config:
            raise ConfigException("no server configuration in config.yaml")

        # pylint: disable=missing-function-docstring
        class Prop:
            """
                internal class for managing properties.
                Adds properties attributes with respect
                of yaml tree structure hierarchy
            """
            def __init__(self, obj, name =None):
                self._name = name
                if isinstance(obj, list):
                    self._name=str(len(obj)) # name of Prop is index in list
                    obj.append(self)
                else:
                    setattr(obj, self._name, self)

                self._tostr = str(name)

            def set_prop(self, name, dictionary, default, ctor):
                """
                    set attribute property. takes dictionary parameter which is yaml
                    dictionary loaded from file. set_prop can take root yaml element
                    and find the right parent to attach new property.
                    :param name: property name
                    :param dictionary: dictionary object property is appended to
                    :param default: default value if property not found in dictionary children
                    :param ctor: contructor to build typed value from other type (string)
                """

                dic = self._find_parent_dict(dictionary, name)

                if dic is None:
                    dic = {}

                if not isinstance(dic, dict):
                    raise ConfigException("Parent property %s should be dict type" % self._name)

                setattr(self, name,
                        ctor(dic[name]) if name in dic and dic[name] else default)
               
            def __str__ (self):
                return str(self._tostr)

            def _find_parent_dict(self, dic, name):
                """
                    Try to find parent property in yaml dictionary tree structure
                    going recursively through children elements tree
                """
                if not isinstance(dic, dict):
                    return None

                if name in dic:
                    return dic

                if not self._name in dic:
                    for k in dic.keys():
                        res = self._find_parent_dict(dic[k],name)
                        if not res is None:
                            return res
                else:
                    return dic[self._name]

                return None

        #pylint: disable=C0103
        p = Prop(self, Config.SERVER_TAG)
        p = Prop(p, Config.HTTP_TAG)
        p.set_prop(Config.HOST_TAG, config, Config.DEFAULT_HOST, str)
        p.set_prop(Config.PORT_TAG, config, Config.DEFAULT_HTTP_PORT, int)
        p.set_prop(Config.SSL_TAG, config, 0, int)
        p.set_prop(Config.CERT_TAG, config, "", str)
        p.set_prop(Config.HTML_TAG, config, Config.DEFAULT_HTML_FOLDER, str)
        p = Prop( getattr(self,Config.SERVER_TAG), Config.WS_TAG )
        p.set_prop(Config.WS_URL_TAG, config, Config.DEFAULT_WS_URL, str)
        p.set_prop(Config.HOST_TAG, config, Config.DEFAULT_HOST, str)
        p.set_prop(Config.PORT_TAG, config, Config.DEFAULT_WS_PORT, int)

        p = Prop(self, Config.LOGS_TAG)
        p.set_prop(Config.LOGS_FOLDER_TAG, config, Config.DEFAULT_LOG_FOLDER, str)
        p.set_prop(Config.LOGS_PREFIX_TAG, config, "", str)

        setattr(self, Config.FILES_TAG, [])
        files_list = getattr(self, Config.FILES_TAG)

        #set tracked files list
        if Config.FILES_TAG in config:
            tags = [Config.FILES_PATH_TAG,  Config.FILES_PATTERN_TAG, Config.FILES_COLOR_TAG]
            for f in config[Config.FILES_TAG]:
                if tags[0] in f and len(f[tags[0]])>0:
                    p = Prop(files_list)
                    p.set_prop(tags[0], f, '', str)
                    p.set_prop(tags[1], f, '\n', str)
                    p.set_prop(tags[2], f, 'auto', str)

    @staticmethod
    def init_logs(log_folder, prefix):
        """ init appplication logs """
        if not os.path.exists(log_folder):
            os.makedirs(log_folder)

        fhandler = logging.FileHandler(os.path.join(log_folder, prefix + 'logtracker.log'))
        chandler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        fhandler.setFormatter(formatter)
        chandler.setFormatter(formatter)

        logger = logging.getLogger('logtracker')
        logger.setLevel(logging.INFO)
        logger.addHandler(fhandler)
        logger.addHandler(chandler)

    @classmethod
    def load(cls, file='config.yaml'):
        """
            load config singleton with config.yaml file
            :param file: yaml file with configuration
            :return: configuration object
            :rtype: Config
        """
        cls.CONFIG = Config(file)
        return cls.CONFIG

    @classmethod
    def get(cls):
        """
            returns Config singleton
        """
        return cls.CONFIG

def load(file='config.yaml'):
    """
        create and return Config singleton
        :rtype: Config
    """
    return Config.load(file)

def get():
    """
        return Config singleton
        :rtype: Config
    """
    return Config.get()
