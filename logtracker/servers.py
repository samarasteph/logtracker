#!/usr/bin/env python3.6

"""
    Server part to send files log to front-end.
    2 sub parts:
        - http server with rest API (config)
        - websocket server to feed html page in real time with log files modifications
"""
# pylint: disable=import-error
import asyncio
import json
import logging
import wsgiref.simple_server
import threading
import websockets
import bottle
import logtracker
import logtracker.config
import logtracker.event

class SAdapter(bottle.ServerAdapter):
    """ Adapter for bottle """
    def __init__(self, host, port, start_function):
        super().__init__(host=host, port=port)
        self._start_function = start_function

    def run(self, *_):
        """ called by bottle """
        self._start_function()

class HttpServer(logtracker.event.Service):
    """ Http server: encapsulate bottle server """

    LOGGER = logging.getLogger('logtracker.servers.HttpServer')

    def __init__(self, host, port):
        """ constructor """
        super().__init__()
        self._host = host
        self._port = port
        self._started = False
        self._server = wsgiref.simple_server.make_server(host, port, bottle.app())

    @logtracker.event.ServiceHandler.onstart
    def start_http(self):
        """ called before Http server is about to start """
        if not self._started:
            self._started = True
            HttpServer.LOGGER.info('Starting HttpServer')
        else:
            raise Warning("Http server already started")

    @logtracker.event.ServiceHandler.onstop
    def stop_server(self):
        """ called before Http server is about to stop """
        if self._started:
            HttpServer.LOGGER.info('Stop HttpServer')
            self._server.shutdown()
        else:
            raise Warning("Http server not yet started")

    @logtracker.event.ServiceHandler.run
    def serve(self):
        """ start bottle http server """
        HttpServer.LOGGER.info('running http server')
        # call bottle run
        try:
            server = SAdapter(self._host, self._port, self._server.serve_forever)
            bottle.run(server=server)
        except Exception as exc:
            import traceback
            HttpServer.LOGGER.error('Error while running server: %s\n%s', str(exc),
                                    traceback.print_tb(exc.__traceback__))
        finally:
            HttpServer.LOGGER.info('Stop Http server')
            self._started = False

    def is_started(self):
        """ return bool indicating server started """
        return self._started

    started = property(fget=is_started)


### Http routes ###

@bottle.route('/')
def defaultget():
    """ return index.html page """
    root_path = logtracker.config.get().server.http.html
    return bottle.static_file("index.html", root=root_path, mimetype='text/html')

@bottle.route('/<filename>')
def server_static(filename):
    """ static files (img,js...) """
    root_path = logtracker.config.get().server.http.html
    return bottle.static_file(filename, root=root_path)

@bottle.route('/files')
def get_filelist():
    """ returns log file list """
    return json.dumps([{"path": f.path, "color": f.color, "pattern": f.pattern}
                       for f in logtracker.config.get().files])

@bottle.route('/ws')
def get_wsconfig():
    """ return websocket server config """
    conf = dict()
    conf['url'] = logtracker.config.get().server.websocket.url
    return conf


class WSServer:
    """ Websocket server """

    LOGGER = logging.getLogger('logtracker.servers.WSServer')
    LOOP = asyncio.new_event_loop()

    def __init__(self, host='localhost', port=8080):
        """ constructor """
        self._host = host
        self._port = port
        self._connections = set()
        self._start_server_task = None
        self._connections = set()
        self._event = threading.Event()


    def start(self, loop=None):
        """ called when start called """
        if self._start_server_task is None:
            WSServer.LOGGER.info("Start Websocket server: host='%s' port=%d", self._host,
                                 self._port)
            self._res = asyncio.Future()
            self._start_server_task = asyncio.Task(self.run_server(), loop=loop)
            self._start_server_task.coroutine = websockets.serve(self.on_connection, self._host, self._port)
        else:
            WSServer.LOGGER.error("WSServer already started")
            raise RuntimeError("WSServer already started")

    def stop(self):
        """ called when stop called """
        if self._start_server_task is not None:
            WSServer.LOGGER.info("Stop Websocket server")

            self._res.set_result(0)
            #self._start_server_task.coroutine.wait_closed()

            if self._start_server_task.done() and self._start_server_task.exception():
                WSServer.LOGGER.error('WSServer task exception: %s',
                                      str(self._start_server_task.exception()))
            WSServer.LOGGER.info("Done")
            #self._start_server_task = None
        else:
            WSServer.LOGGER.error("WSServer not started yet")
            raise RuntimeError("WSServer not started yet")

    async def run_server(self):
        """ run server loop """
        WSServer.LOGGER.info("Websocket server running")
        try:
            async with self._start_server_task.coroutine:
                WSServer.LOGGER.info("Entering loop")
                await self._res

            WSServer.LOGGER.info("Stopping loop")

        except Exception as exception:
            WSServer.LOGGER.error("Exception while running %s", str(exception))
            #raise logtracker.CriticalError("Stop application")
        finally:
            WSServer.LOGGER.info("Websocket server stop running")

    async def on_connection(self, websocket, path):
        """ called on incoming connection """

        WSServer.LOGGER.info('incoming connection: ws=%s, path=%s', websocket, path)

        await self.register(websocket, path)
        try:
            async for message in websocket:
                WSServer.LOGGER.info(str(message))
        finally:
            await self.unregister(websocket)

    async def register(self, websocket, path):
        """ called to add incoming connection to clients list """
        WSServer.LOGGER.info('Register websocket=%s path=%s', str(websocket), str(path))
        self._connections.add(websocket)
        await asyncio.sleep(0.05)


    async def unregister(self, websocket):
        """ called when ws connection is done """
        WSServer.LOGGER.info('Unregister websocket=%s', str(websocket))
        self._connections.remove(websocket)
        await asyncio.sleep(0.05)

    async def push_message(self, message):
        """ callback for file events notification """
        if message and len(self._connections) > 0:
            await asyncio.wait([connection.send(message) for connection in self._connections])
