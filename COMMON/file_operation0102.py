import os
import configparser
from configparser import ConfigParser
from django.core.cache import cache
from COMMON.ora import *
import datetime
# filepath
software_ini = "../"


# file function
def GetFilePath(filename):
    proDir = os.path.split(os.path.realpath(__file__))[0]
    configpath = os.path.join(proDir, filename)
    return configpath


# def SoftWare_ini():

# 初始化全局变量 current_model current_model_sp equipnumgrop  equipstatus  deviceclass equipconnect
def GolbalGroup_Ini():
    filepath = GetFilePath("SoftWare.ini")
    print(filepath)
    conf = ConfigParser()  # 需要实例化一个ConfigParser对象
    conf.read(filepath)  # 需要添加上config.ini的路径，不需要open打开，直接给文件路径就读取，也可以指定encoding='utf-8'
    current_model = conf['CommonUse']['CurrentModel']
    current_model_sp = conf['CommonUse']['CurrentModel_SP']
    current_order = conf['CommonUse']['CurrentOrder']
    current_order_stand = conf['CommonUse']['CurrentOrder_Stand']
    # if current_model == "GP-001":
    #     return None
    cache.set('current_model', current_model, None)
    cache.set('current_model_sp', current_model_sp, None)
    cache.set('current_order', current_order, None)
    cache.set('current_order_stand', current_order_stand, None)

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

    # DeviceClass_SP
    DeviceClass_SP_Ini()

    # Equip_Status_SP
    Equip_Status_SP_Ini()

    # EquipConnect
    # dic中client_id为key ip:port为value  示例: 'EquipConnect':{'12345678': '127.0.0.1:5100', 'qwerty': '127.0.0.1:5200'}
    equip_connect = cache.get('EquipConnect', default=None)
    if equip_connect is None:
        equip_connect = {}
        cache.set('EquipConnect', equip_connect, None)
        print(equip_connect)

    equip_time = cache.get('EquipTime', default=None)    #全线机台标准时间初始化
    if equip_time is None:
        right_now = datetime.datetime.now()
        equip_time = {"StartTime": right_now, "ErrorTime": right_now, "EndTime": right_now, "Status": 0}   #status 0 正常生产 1 选择机台换型 2 stop 3 error
        cache.set('EquipTime', equip_time, None)
        print(cache.get('EquipTime', default=None))
        # end_time = datetime.datetime.now()
        # end_time = end_time + datetime.timedelta(seconds=10)
        # print(end_time)
        # print((end_time - right_now).seconds)

    equip_time_st = cache.get('EquipTimeST', default=None)          #机台特殊状态时间初始化   {"STNO": ,"StartTime": , "ErrorTime": , "EndTime": , "Status": 0}
    if equip_time_st is None:
        equip_time_st = []
        cache.set('EquipTimeST', equip_time_st, None)
        print(cache.get('EquipTimeST', default=None))

    # 点检机台列表初始化
    checkdevice = []  #点检机台清单
    cache.set('CheckDevice', checkdevice, None)
    # 从ini 中取出清单字符串
    filepath = GetFilePath("SoftWare.ini")
    conf = ConfigParser()  # 需要实例化一个ConfigParser对象
    conf.read(filepath)  # 需要添加上config.ini的路径，不需要open打开，直接给文件路径就读取，也可以指定encoding='utf-8'
    check_device = conf['CommonUse']['CheckDevice']
    print("CheckDevice:" + check_device)
    print(type(check_device))
    # 将字符串转化为list
    check_device = check_device.strip('[')
    check_device = check_device.strip(']')
    check_device = check_device.replace('\'', '')
    check_device = check_device.replace(' ', '')
    checkdevice = check_device.split(',')
    print(checkdevice)
    print(type(checkdevice))
    cache.set('CheckDevice', checkdevice, None)

    #将点检的机台信息更新到 equipstatus中
    equipstatus = cache.get('Equip_Status')
    for it1 in equipstatus:
        for it2 in checkdevice:
            if it1['EquipNumber'] == it2:
                it1['CheckDevice'] = "YES"
    cache.set('Equip_Status', equipstatus, None)

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
        equipnumgroup.append(it['equipment_num'])
    cache.set('EquipNumGroup', equipnumgroup, None)
    print('EquipNumGroup:')
    print(type(cache.get('EquipNumGroup')))
    print(cache.get('EquipNumGroup'))
    return data


def Equip_Status_Ini(data):
    equip_status = []
    for it in data:
        equipStatus = {"EquipName": it['equipment_name'], "EquipNumber": it['equipment_num'], "EquipOrder": "Start",
                       "EquipResult": "OK", "CheckDevice": "/", "CheckResult": "NA"}
        equip_status.append(equipStatus)
    cache.set('Equip_Status', equip_status, None)
    print('Equip_Status')
    print(type(cache.get('Equip_Status')))
    print(cache.get('Equip_Status'))
def Equip_Status_SP_Ini():
    device_class_sp = cache.get("DeviceClass_SP")
    equip_status_sp = []
    for it in device_class_sp:
        equipStatus = {"EquipName": it['EquipName'], "EquipNumber": it['EquipNumber'], "EquipOrder": "Start",
                       "EquipResult": "OK", "CheckDevice": "/", "CheckResult": "NA"}
        equip_status_sp.append(equipStatus)
    cache.set('Equip_Status_SP', equip_status_sp, None)
    print('Equip_Status_SP')
    print(type(cache.get('Equip_Status_SP')))
    print(cache.get('Equip_Status_SP'))

def DeviceClass_Ini(data):
    device_class = []
    for it in data:
        deviceclass = {"EquipName": it['equipment_name'], "EquipNumber": it['equipment_num'],
                       "EquipIP": it['equipment_ip'], "EquipSerial": it['equipment_serial'], "EquipStatus": False, "EquipError": False}
        device_class.append(deviceclass)
    cache.set('DeviceClass', device_class, None)
    print('DeviceClass')
    print(type(cache.get('DeviceClass')))
    print(cache.get('DeviceClass'))

def DeviceClass_SP_Ini():
    device_class_sp = []
    SQL = "SELECT * FROM equipment_tab"
    print(SQL)
    data = easy_sql_reader(SQL)
    for it in data:
        if it['equipment_num'][0:2] == "SP":
            deviceclass = {"EquipName": it['equipment_name'], "EquipNumber": it['equipment_num'],
                           "EquipIP": it['equipment_ip'], "EquipSerial": it['equipment_serial'], "EquipStatus": False,
                           "EquipError": False}
            device_class_sp.append(deviceclass)
        cache.set('DeviceClass_SP', device_class_sp, None)
    print('DeviceClass_SP')
    print(type(cache.get('DeviceClass_SP')))
    print(cache.get('DeviceClass_SP'))

def Device_Connect_Select(model, data):
    # 冒泡
    n = len(data)
    for i in range(n):
        # Last i elements are already in place
        for j in range(0, n - i - 1):
            if int(data[j]['equipment_serial']) > int(data[j + 1]['equipment_serial']):
                data[j], data[j + 1] = data[j + 1], data[j]

    device_class = []
    device_class_re = []
    for it in data:
        deviceclass = {"EquipName": it['equipment_name'], "EquipNumber": it['equipment_num'],
                       "EquipIP": it['equipment_ip'], "EquipSerial": it['equipment_serial'], "EquipStatus": False}
        device_class.append(deviceclass)
    print('DeviceClass')
    print(type(device_class))
    print(device_class)
    equip_connect = cache.get('EquipConnect', default=None)
    print(equip_connect)
    for it1 in device_class:
        print(type(it1))
        print(it1)
        checkRet = False
        for it2 in equip_connect.values():
            print(it2)
            print(it1["EquipIP"] + " : " + it2.split(":")[0])
            if it1["EquipIP"] == it2.split(":")[0]:
                checkRet = True
                break
        if checkRet is True:
            device_class_re.append(it1)
    print(device_class_re)
    return device_class_re