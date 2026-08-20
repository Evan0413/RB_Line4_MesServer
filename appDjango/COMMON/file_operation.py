import os
import configparser
from configparser import ConfigParser
from django.core.cache import cache
from COMMON.ora import *

# filepath
software_ini = "../"


# file function
def GetFilePath(filename):
    proDir = os.path.split(os.path.realpath(__file__))[0]
    configpath = os.path.join(proDir, filename)
    return configpath


# def SoftWare_ini():

# 初始化全局变量 current_model  equipnumgrop  equipstatus  deviceclass equipconnect
def GolbalGroup_Ini():
    filepath = GetFilePath("SoftWare.ini")
    conf = ConfigParser()  # 需要实例化一个ConfigParser对象
    conf.read(filepath)  # 需要添加上config.ini的路径，不需要open打开，直接给文件路径就读取，也可以指定encoding='utf-8'
    current_model = conf['CommonUse']['CurrentModel']
    # if current_model == "GP-001":
    #     return None
    cache.set('current_model', current_model, None)

    SQL = "SELECT * FROM station_tab WHERE gp_model = '" + current_model + "'"
    print(SQL)
    data = easy_sql_reader(SQL)
    # print(type(int((data[0]['equipment_serial']))))

    # EquipNumGrop
    data = EquipNumGroup_Ini(data)

    # Equip_Status
    Equip_Status_Ini(data)

    # DeviceClass
    DeviceClass_Ini(data)

    # EquipConnect
    # dic中client_id为key ip:port为value  示例: 'EquipConnect':{'12345678': '127.0.0.1:5100', 'qwerty': '127.0.0.1:5200'}
    equip_connect = cache.get('EquipConnect', default=None)
    if equip_connect is None:
        equip_connect = {}
        cache.set('EquipConnect', equip_connect, None)
        print(equip_connect)

    current_order = cache.get('current_order')
    print(current_order)
    print("-----------------------------------------current_order-------------------------")
    print("-----------------------------------------current_order-------------------------")
    print("-----------------------------------------current_order-------------------------")

def EquipNumGroup_Ini(data):
    # 冒泡
    n = len(data)
    for i in range(n):
        # Last i elements are already in place
        for j in range(0, n - i - 1):
            if int(data[j]['equipment_serial']) > int(data[j + 1]['equipment_serial']):
                data[j], data[j + 1] = data[j + 1], data[j]

    # EquipNumGrop
    equipnumgroup = []
    for it in data:
        equipnumgroup.append(it['equipment_serial'])
    cache.set('EquipNumGroup', equipnumgroup, None)
    print('EquipNumGroup:')
    print(type(cache.get('EquipNumGroup')))
    print(cache.get('EquipNumGroup'))
    return data


def Equip_Status_Ini(data):
    equip_status = []
    for it in data:
        equipStatus = {"EquipName": it['equipment_name'], "EquipNumber": it['equipment_num'], "EquipOrder": "NA",
                       "EquipResult": "NA"}
        equip_status.append(equipStatus)
    cache.set('Equip_Status', equip_status, None)
    print('Equip_Status')
    print(type(cache.get('Equip_Status')))
    print(cache.get('Equip_Status'))


def DeviceClass_Ini(data):
    device_class = []
    for it in data:
        deviceclass = {"EquipName": it['equipment_name'], "EquipNumber": it['equipment_num'],
                       "EquipIP": it['equipment_ip'], "EquipSerial": it['equipment_serial'], "EquipStatus": False}
        device_class.append(deviceclass)
    cache.set('DeviceClass', device_class, None)
    print('DeviceClass')
    print(type(cache.get('DeviceClass')))
    print(cache.get('DeviceClass'))



def Device_Connect_Select(model, data):
    # 冒泡
    n = len(data)
    for i in range(n):
        # Last i elements are already in place
        for j in range(0, n - i - 1):
            if int(data[j]['equipment_serial']) > int(data[j + 1]['equipment_serial']):
                data[j], data[j + 1] = data[j + 1], data[j]

    device_class = []
    for it in data:
        deviceclass = {"EquipName": it['equipment_name'], "EquipNumber": it['equipment_num'],
                       "EquipIP": it['equipment_ip'], "EquipSerial": it['equipment_serial'], "EquipStatus": False}
        device_class.append(deviceclass)
    print('DeviceClass')

    equip_connect = cache.get('EquipConnect', default=None)
    for it1 in device_class:
        checkRet = False
        for it2 in equip_connect:
            if it1["EquipIP"] == it2:
                checkRet = True
                break
        if checkRet is False:
            device_class.remove(it1)
    equip_connect = cache.get('EquipConnect', default=None)
    return device_class