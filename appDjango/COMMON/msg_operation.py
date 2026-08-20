import pymysql
import threading
from threading import Thread
from django.conf import settings
from django.core.cache import cache
from paho.mqtt import publish
# 创建全局互斥锁
lock = threading.Lock()
SSE_mutex = threading.Lock()

def TRecv(client_Ip, data):
    print("*****TRecv接收并解析信息")
    data = eval(data)
    equip_topic = ""
    device_class = cache.get('DeviceClass', default=None)
    if device_class is not None:
        for it in device_class:
            tag = False
            if it['EquipIP'] == client_Ip:
                tag = True
                equip_number = it['EquipNumber']
                equip_topic = "Msg2Station/" + equip_number
                print(equip_topic)
                break
        if tag is False:
            raise Exception('[msg_operation] Can not find same client_Ip in DeviceClass')
    # else:
    #     raise Exception('[msg_operation] DeviceClass is None ,can not find client_Ip')

    command = data['Command']
    if command == '0x01':
        print('0x01')
    elif command == '0x02':
        print('0x02')
    elif command == '0x03':
        print('0x03')
    elif command == '0x04':
        print('0x04')
    elif command == '0x05':
        print('0x05')
    elif command == '0x06':
        print('0x06')
    elif command == '0x07':
        print('0x07')
    elif command == '0x08':
        print('0x08')
    elif command == '0x09':
        print('0x09')
    elif command == '0x010':
        print('0x010')
    elif command == '0x011':
        print('0x011')
    elif command == '0x012':
        print('0x012')
    elif command == '0x013':
        print('0x013')
    elif command == '0x014':
        print('0x014')

    return

def TConn(client_Id, client_Ip, client_Port, link):
    # 上锁
    warn_msg = ""
    lock.acquire()
    try:
        equip_connect = cache.get('EquipConnect', default=None)
        device_class = cache.get('DeviceClass', default=None)
        if equip_connect is None:
            equip_connect = {}
        print(equip_connect)
        print(device_class)
        if equip_connect is not None:
            if link:
                equip_connect[str(client_Id)] = str(client_Ip) + ':' + str(client_Port)
                cache.set('EquipConnect', equip_connect)
            else:
                equip_connect.pop(str(client_Id))
                cache.set('EquipConnect', equip_connect)
        else:
            warn_msg = '[msg_operation] EquipConnect is None, can not record'
            print(warn_msg)
            raise Exception(warn_msg)
        print(equip_connect)

        if device_class is not None:
            tag = False
            for it in device_class:
                if it['EquipIP'] == client_Ip:
                    it['EquipStatus'] = link
                    tag = True
                    break
            if tag:
                cache.set('DeviceClass', device_class)
            else:
                warn_msg = '[msg_operation] Can not find same device in DeviceClass'
                print(warn_msg)
                raise Exception(warn_msg)
        else:
            warn_msg = '[msg_operation] DeviceClass is None ,can not change'
            print(warn_msg)
            raise Exception(warn_msg)
        print(device_class)
        lock.release()
        # 功能未实现：fun()通知Web，更新station信息
    except:
        lock.release()
        warn_msg = "WARNING:TConn Warning, You should initialize cache first"
        print(warn_msg)
        # raise Exception(warn_msg)

def Recv(client_Ip, data):
    t = Thread(target=TRecv(client_Ip, data))
    t.start()
    return


def Conn(client_Id, client_Ip, client_Port, link):
    t = Thread(target=TConn(client_Id, client_Ip, client_Port, link))
    t.start()
    return

