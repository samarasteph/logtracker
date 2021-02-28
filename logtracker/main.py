#!/usr/bin/env python3.6

"""
    MAIN
"""
import sys
import logging
import asyncio
import logtracker.config
import logtracker.servers
import logtracker.filenotifier
import logtracker.event

class Application:
    """ Application class: glue for all components/services """

    def __init__(self):
        self._http = None
        self._ws = None
        self._file_notifier = None
        self._event_manager = logtracker.event.Manager()

        def on_message(message):
            #logtracker.event.Manager.LOOP.run_until_complete(ws_server.push_message(message))
            asyncio.Task(self._ws.push_message(message), loop=logtracker.event.Manager.LOOP)

        self._filenotif_cb = on_message

    @staticmethod
    def load_config():
        """ load app configuration """
        if len(sys.argv) > 1:
            logtracker.config.load(file=sys.argv[1])
        else:
            logtracker.config.load()

        conf = logtracker.config.get()
        conf.init_logs(conf.logs.folder, conf.logs.prefix)

    def start_http(self):
        """ start http service """
        http_config = logtracker.config.get().server.http
        http = logtracker.servers.HttpServer(http_config.host, http_config.port)
        http.start()
        self._http = http

    def stop_http(self):
        """ stop http service """
        if self._http:
            self._http.stop()
            self._http = None

    def start_files_notifier(self):
        """ start file notifier service """
        fnotifier_service = logtracker.filenotifier.FileNotifierService(
            logtracker.config.get().files, self.on_file_event)

        fnotifier_service.start()
        self._file_notifier = fnotifier_service

    def stop_files_notifier(self):
        """ stop file notifier service """
        if self._file_notifier:
            self._file_notifier.stop()
            self._file_notifier = None

    def start_ws_server(self):
        """ start websocket server """
        host = logtracker.config.get().server.websocket.host
        port = logtracker.config.get().server.websocket.port
        ws_server = logtracker.servers.WSServer(host, port)
        ws_server.start()
        self._ws = ws_server

        self._event_manager.register_event(
            logtracker.filenotifier.FileNotifierEvent, self._filenotif_cb)

    def stop_ws_server(self):
        """ stop service """
        if self._ws:
            self._event_manager.unregister_event(
                logtracker.filenotifier.FileNotifierEvent, self._filenotif_cb)
            self._ws.stop()
            self._ws = None

    def on_file_event(self, file_event):
        """ push file events from FileNotifierService """
        self._event_manager.post_event(file_event)

    def start(self, loop=None):
        """ application running entry point """
        loop = loop or asyncio.get_event_loop()
        try:
            self.load_config()
            self.start_ws_server()
            self.start_http()
            self.start_files_notifier()
            loop.run_forever()
        except KeyboardInterrupt:
            log = logging.getLogger('logtracker.Application')
            log.info('CTRL+C pressed')
        finally:
            loop.stop()
            self.stop_files_notifier()
            self.stop_ws_server()
            self.stop_http()
            logtracker.event.Service.THREAD_POOL.shutdown()

if __name__ == "__main__":
    APPLICATION = Application()
    APPLICATION.start()
    print('quit application')
