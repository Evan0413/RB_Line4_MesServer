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

async def broker_coro():
    config = {
        'listeners': {
            'default': {
                'type': 'tcp',
                'bind': '172.11.0.3:1883',
                'max_connections': 10,
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


# -----------------------------上为broker 下为client-----------------------------------------------------------------

client_id = f'python-mqtt-{random.randint(0, 100)}'
client = mqtt.Client(client_id=client_id, clean_session=False)

# 建立mqtt连接
def on_connect(client, userdata, flag, rc):
    print("Connected with result code " + str(rc))
    if 0 == rc:
        print('Connected successfully')
        client.subscribe(settings.MQTT_TOPIC)
    elif 1 == rc:
        print("连接失败-不正确的协议版本")
    elif 2 == rc:
        print("连接失败-无效的客户端标识符")
    elif 3 == rc:
        print("连接失败-服务器不可用")
    elif 4 == rc:
        print("连接失败-错误的用户名或密码")
    elif 5 == rc:
        print("连接失败-未授权")
    else:
        print("6-255: 未定义.")

# 接收、处理mqtt消息
def on_message(client, userdata, msg):
    print("//Client:on_message position")
    print(f"//Client:Client Received: `{msg.payload.decode()}` ,from topic: `{msg.topic}` \n")
    print('//Client:' + str(cache.get('EquipConnect')))
    print("//Client:-----")
    # command = msg.split(';')[0]
    # if command == '0x01':
        # loginobj = LoginOutMsg()
        # loginobj.analysis(msg)
        # print(loginobj.user)



def on_disconnect(client, userdata, rc):
    print("Disconnect:" + str(rc))

def publish(topic, data):
    client.publish(topic, data)

# def Login_callback(client, userdata, msg):
#     # print("Received message '" + str(message.payload) + "' on topic '"
#     #    + message.topic + "' with QoS " + str(message.qos))
#     print("position Login_callback")
#     print(f"Received: `{msg.payload.decode()}` ,from: `{msg.topic}` topic")


#mqtt client
def main2():
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect

    # client.message_callback_add("commands/login", Login_callback)
    # client.message_callback_add("commands/msg/#", Msg_callback)

    client.username_pw_set(settings.MQTT_USER, settings.MQTT_PASSWORD)
    client.connect(
        host=settings.MQTT_SERVER,
        port=settings.MQTT_PORT,
        keepalive=settings.MQTT_KEEPALIVE
    )
    client.reconnect_delay_set(min_delay=1, max_delay=2000)
    client.loop_start()


