import asyncio
from datetime import datetime

import aiohttp

from gain.request import fetch
from .log import logger

try:
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    pass


class Spider:
    start_url = ''
    parsers = []
    urls_count = 0
    frequency = 5

    @classmethod
    def is_running(cls):
        is_running = False
        for parser in cls.parsers:
            if len(parser.pre_parse_urls) > 0 or len(parser.parsing_urls) > 0:
                is_running = True
        return is_running

    @classmethod
    def parse(cls, html):
        for parser in cls.parsers:
            parser.parse_urls(html)

    @classmethod
    def run(cls):
        logger.info('Spider started!')
        start_time = datetime.now()
        semaphore = asyncio.Semaphore(cls.frequency)
        loop = asyncio.get_event_loop()

        tasks = asyncio.wait([parser.task(cls, semaphore) for parser in cls.parsers])

        try:
            loop.run_until_complete(cls.init_parse(semaphore))
            loop.run_until_complete(tasks)
        except KeyboardInterrupt:
            for task in asyncio.Task.all_tasks():
                task.cancel()
            loop.run_forever()
        finally:
            end_time = datetime.now()
            for parser in cls.parsers:
                if parser.item is not None:
                    logger.info('Item "{}": {}'.format(parser.item._item_name, parser.item._item_count))
            logger.info('Requests count: {}'.format(cls.urls_count))
            logger.info('Time usage: {}'.format(end_time - start_time))
            logger.info('Spider finished!')
            loop.close()

    @classmethod
    async def init_parse(cls, semaphore):
        with aiohttp.ClientSession() as session:
            html = await fetch(cls.start_url, session, semaphore)
            cls.parse(html)
