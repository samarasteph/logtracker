#!/usr/bin/env python3.6

"""
	Test for 'servers' module
"""
#pylint: disabled=import-error

import logging
import asyncio
import websockets
import logtracker.servers
import tests.utils

tests.utils.setup_logger('test_servers')

def test_ws_server():
    """ test web socket server """
    log = tests.utils.get_logger('test_servers.test_ws_server')

    port = 8085
    loop = asyncio.get_event_loop()
    ws_server = logtracker.servers.WSServer(port=port)

    ws_server.start()


    async def pusher(message, delay):
        await asyncio.sleep(delay)
        log.info('pusher: %s', message)
        await ws_server.push_message(message)

    async def ws_connect(future):
        log.info("start ws_connect")
        await asyncio.sleep(1)
        messages_list = []
        try:
            async with websockets.connect('ws://localhost:%d' % port) as wsock:
                log.info("ws_connect: waiting messages")
                while True:
                    message = await wsock.recv()
                    if message:
                        messages_list.append(message)
        except GeneratorExit:
            log.info('Stop ws client coroutine')
        finally:
            future.set_result(messages_list)

    async def close_client(cor, delay):
        try:
            log.info('close_client: Close ws_connect')
            await asyncio.sleep(delay)
            cor.throw(GeneratorExit)
        finally:
            log.info('Exit close_client coroutine')

    future = asyncio.Future()
    cli_cr = ws_connect(future)

    messages = ['Message from earth', 'Message from mars', "Hello Mars", "Hello world"]
    tasks = [cli_cr]
    tasks.append(asyncio.Task(pusher(messages[0], 1.5)))
    tasks.append(asyncio.Task(pusher(messages[1], 1.75)))
    tasks.append(asyncio.Task(pusher(messages[2], 2)))
    tasks.append(asyncio.Task(pusher(messages[3], 2.25)))
    tasks.append(asyncio.Task(close_client(cli_cr, 2.5)))
    loop.run_until_complete(asyncio.wait(tasks))

    ws_server.stop()

    assert future.result() == messages

def test_restart_ws_server():
    """ test if ws server can be retarted correctly """
    log = tests.utils.get_logger('test_servers.test_restart_ws_server')

    port = 8087
    loop = asyncio.get_event_loop()
    ws_server = logtracker.servers.WSServer(port=port)

    async def wait(delay):
        await asyncio.sleep(delay)
        log.info("%d seconds waited" % delay)

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

