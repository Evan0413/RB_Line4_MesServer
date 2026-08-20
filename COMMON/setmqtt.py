# 为了能在外部脚本中调用Django ORM模型，必须配置脚本环境变量，将脚本注册到Django的环境变量中
import os, sys
import django
import random
from django.conf import settings
from django.core.cache import cache
from paho.mqtt import publish

# from COMMON.analysis import *
# 第一个参数固定，第二个参数是工程名称.settings
os.environ.setdefault('DJANGO_SETTING_MODULE', 'my_django.settings')
django.setup()
# 使用独立线程运行
import threading
from threading import Thread
import time
import json
# ---------------------
import logging
import asyncio
import os
from COMMON.amqtt.broker import Broker
import paho.mqtt.client as mqtt
from COMMON.file_operation import GolbalGroup_Ini

async def broker_coro():
    config = {
        'listeners': {
            'default': {
                'type': 'tcp',
                # Listen on every local network adapter so production devices
                # can connect to this computer's current LAN address.
                'bind': '0.0.0.0:1833',
                # 'bind': '10.44.199.246:1833',
                # 'bind': '127.0.0.1:1833',
                # 'bind': '0:1833',
                'max_connections': 60,
            }
        },
        'sys_interval': 10,
            "auth": {
                "allow-anonymous": True,
                "password-file": os.path.join(
                    os.path.dirname(os.path.realpath(__file__)), "passwd"
                ),
                "plugins": ["auth_file", "auth_anonymous"],
            },
            "topic-check": {"enabled": False},
    }
    broker = Broker(config)
    await broker.start()

#mqtt broker
def main():
    GolbalGroup_Ini()
    formatter = "[%(asctime)s] :: %(levelname)s :: %(name)s :: %(message)s"
    logging.basicConfig(level=logging.INFO, format=formatter)


    # asyncio.get_event_loop().run_until_complete(broker_coro())
    # asyncio.get_event_loop().run_forever()
    # print("forever>>>>>>>>>>>>>>>>>>>>>>>>>>>>")

    new_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(new_loop)
    loop = asyncio.get_event_loop()
    # task = asyncio.ensure_future(do_work(checker))
    loop.run_until_complete(broker_coro())
    loop.run_forever()
    # st = task.result()

# 测试时启动函数
def mqtt_run():
    t = Thread(target=main)  # 执行的函数如果需要传递参数，threading.Thread(target=函数名,args=(参数，逗号隔开))
    t.start()
    print("start>>>>>>>>>>>>>>>>>>")
