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
import logtracker.config
import websockets
from bottle import route, run, static_file
import logtracker.event

class HttpServer(logtracker.event.Service):
    """ Http server: encapsulate bottle server """

    LOGGER = logging.getLogger('logtracker.servers.http')

    def __init__(self, host, port):
        """ constructor """
        super().__init__()
        self._host = host
        self._port = port
        self._loop = asyncio.get_event_loop()
        self._started = False

    @logtracker.event.ServiceHandler.onstart
    def start_http(self):
        """ called before Http server is about to start """
        if not self._started:
            self._started = True
            HttpServer.LOGGER.info('Starting HttpServer')
        else:
            raise "Http server already started"

    @logtracker.event.ServiceHandler.onstop
    def stop_server(self):
        """ called before Http server is about to stop """
        if self._started:
            self._started = False
        else:
            raise "Http server not yet started"

    @logtracker.event.ServiceHandler.run
    def serve(self):
        """ start bottle http server """
        print('running http server')
        # call bottle run
        run(host=self._host, port=self._port)

### Http routes ###

@route('/')
def defaultget():
    """ return index.html page """
    return static_file('index.html', root='html', mimetype='text/html')

@route('/files')
def get_filelist():
    """ returns log file list """
    return json.dumps([{"path": f.path, "color": f.color} for f in logtracker.config.get().files])

class WSServer:
    """ Websocket server """

    LOGGER = logging.getLogger('logtracker.servers.WSServer')
    LOOP = asyncio.new_event_loop() 

    def __init__(self, host='localhost', port='8080'):
        """ constructor """
        self._host = host
        self._port = port
        self._connections = set()
        self._start_server_coroutine = None
        self._connections = set()

    def start(self, loop=None):
        """ called when start called """
        if self._start_server_coroutine is None:
            WSServer.LOGGER.info("Start Websocket server: host='%s' port=%d", self._host,
                                 self._port)
            self._start_server_coroutine = websockets.serve(self.on_connection, self._host,
                                                            self._port)
            return asyncio.Task(self.run_server(), loop=loop)
        else:
            WSServer.LOGGER.error("WSServer already started")
            raise RuntimeError("WSServer already started")

    def stop(self):
        """ called when stop called """
        if self._start_server_coroutine is not None:
            WSServer.LOGGER.info("Stop Websocket server")
            self._start_server_coroutine.ws_server.close()
            self._start_server_coroutine = None
        else:
            WSServer.LOGGER.error("WSServer not started yet")
            raise RuntimeError("WSServer not started yet")

    async def run_server(self):
        """ run server loop """
        WSServer.LOGGER.info("Websocket server running")
        try:
            await self._start_server_coroutine
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
        await asyncio.sleep(0.5)


    async def unregister(self, websocket):
        """ called when ws connection is done """
        WSServer.LOGGER.info('Unregister websocket=%s', str(websocket))
        self._connections.remove(websocket)
        await asyncio.sleep(0.5)

    async def push_message(self, message):
        """ callback for file events notification """
        if message and len(self._connections) > 0:
            await asyncio.wait([connection.send(message) for connection in self._connections])
