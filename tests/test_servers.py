#!/usr/bin/env python3.6

"""
	Test for 'servers' module
"""
#pylint: disabled=import-error

import time
import threading
import asyncio
import websockets
import logtracker.servers
import logtracker.event
import tests.utils

tests.utils.setup_logger('test_servers')

async def pusher(ws_server,message, delay):
    """ send message from server to client """
    await asyncio.sleep(delay)
    log = tests.utils.get_logger('test_servers.pusher')
    log.info(f"send {message}")
    await ws_server.push_message(message)

async def ws_connect(future,port):
    """ clent connection to server """
    await asyncio.sleep(1)
    messages_list = []
    async with websockets.connect(f'ws://localhost:{port}') as wsock:
        while True:
            message = await wsock.recv()
            if message:
                if message == '@end':
                    future.set_result(messages_list)
                    return
                messages_list.append(message)

async def close_client(ws_server,delay):
    """ shutdown client connection """
    await asyncio.sleep(delay)
    log = tests.utils.get_logger('test_servers.close_client')
    log.info('close_client')
    await pusher(ws_server,'@end', 2.75)


def test_ws_server():
    """ test web socket server """

    log = tests.utils.get_logger('test_servers.test_ws_server')

    port = 8085
    loop = asyncio.get_event_loop()
    ws_server = logtracker.servers.WSServer(port=port)

    ws_server.start()

    future = asyncio.Future()
    cli_cr = ws_connect(future,port)

    messages = ['Message from earth', 'Message from mars', "Hello Mars", "Hello world"]
    tasks = [cli_cr]
    tasks.append(asyncio.Task(pusher(ws_server,messages[0], 1.5)))
    tasks.append(asyncio.Task(pusher(ws_server,messages[1], 1.75)))
    tasks.append(asyncio.Task(pusher(ws_server,messages[2], 2)))
    tasks.append(asyncio.Task(pusher(ws_server,messages[3], 2.25)))
    tasks.append(asyncio.Task(close_client(ws_server,2.5)))
    loop.run_until_complete(asyncio.wait(tasks))

    log.info("All tasks completed")

    ws_server.stop()

    assert future.result() == messages
    assert ws_server._start_server_task.done()

def test_ws_server_double_connection():
    """ test web socket server with 2 clients connecting"""

    log = tests.utils.get_logger('test_servers.test_ws_server')

    port = 8085
    loop = asyncio.get_event_loop()
    ws_server = logtracker.servers.WSServer(port=port)

    ws_server.start()

    future1 = asyncio.Future()
    cli_cr1 = ws_connect(future1,port)

    future2 = asyncio.Future()
    cli_cr2 = ws_connect(future2,port)

    messages = ['Message from earth', 'Message from mars', "Hello Mars", "Hello world"]
    tasks = [cli_cr1, cli_cr2 ]
    tasks.append(asyncio.Task(pusher(ws_server,messages[0], 1.5)))
    tasks.append(asyncio.Task(pusher(ws_server,messages[1], 1.75)))
    tasks.append(asyncio.Task(pusher(ws_server,messages[2], 2)))
    tasks.append(asyncio.Task(pusher(ws_server,messages[3], 2.25)))
    tasks.append(asyncio.Task(close_client(ws_server,2.5)))
    loop.run_until_complete(asyncio.wait(tasks))

    log.info("All tasks completed")

    ws_server.stop()

    assert future1.result() == messages
    assert future2.result() == messages

def test_restart_ws_server():
    """ test if ws server can be retarted correctly """
    log = tests.utils.get_logger('test_servers.test_restart_ws_server')

    port = 8087
    loop = asyncio.get_event_loop()
    ws_server = logtracker.servers.WSServer(port=port)

    async def wait(delay):
        await asyncio.sleep(delay)
        log.info(f"{delay} seconds waited")

    async def start_server():
        log.info('Start server')
        ws_server.start()

    async def stop_server():
        log.info('Stop server')
        ws_server.stop()

    async def start_n_stop():
        await wait(0.25)
        await start_server()
        await wait(0.5)
        await stop_server()
        await wait(0.5)
        await start_server()
        await wait(0.5)
        await stop_server()
        await wait(1)

    loop.run_until_complete(start_n_stop())

def test_start_stop_http():
    """ Test if http server shutdown nicely """
    log = tests.utils.get_logger('test_servers.test_start_stop_http')
    http = logtracker.servers.HttpServer('localhost', 7876)
    delay = 1.5

    def raise_exc():
        if http.started:
            http._future.set_exception(TimeoutError('Http server not stopped'))
            #logtracker.servers.HttpServer.THREAD_POOL.shutdown()

    log.info('start http server')
    http.start()
    log.info('server started')
    time.sleep(0.5)
    log.info('stop http server')
    tmr = threading.Timer(delay, raise_exc)
    tmr.start()
    assert http.started 
    if http.started:
        http.stop()
    assert not http.started
    log.info('http server stopped')
