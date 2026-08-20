import asyncio
from asyncio import CancelledError, futures
import logging

import pymysql
import threading
import json
from threading import Thread
import time
import traceback
# import gc
# from memory_profiler import profile
# import objgraph

from django.conf import settings
from django.core.cache import cache

from COMMON.getmqtt import *
from COMMON.ora import *
from COMMON.logBasic import logger
from COMMON.file_operation import *

from suds.client import Client
import socket
import datetime
import requests
from channels.db import database_sync_to_async
from asgiref.sync import sync_to_async
import xmltodict
from collections import deque

# 创建全局线程池对象 处理解析函数TRecv
# from concurrent.futures import ThreadPoolExecutor
# threadPool = ThreadPoolExecutor(max_workers=20, thread_name_prefix="recv_")

from ManDe import models as md
from django.core import serializers
# 创建全局互斥锁
lock = threading.Lock()   #Tconn 设备连接处理互斥锁
lock2 = threading.Lock()  #Trecv 请求解析互斥锁（弃用）
lock3 = threading.Lock()  # Time_Record 时间记录互斥锁
lock_cache = threading.Lock() # 内存cache操作互斥锁
lock_uuid = threading.Lock()
# log = logger()
log = logger
reply_msgs = deque()
# threadPool_futures = deque()


# 总的全局外部url
url = {
        "GetPlanOrder": "http://10.246.140.225:9000/mes.asmx/GetPlanOrder",
        "PlanOrderConfirm": "http://10.246.140.225:9000/mes.asmx/PlanOrderConfirm",
        "ProcessInfo": "http://10.246.140.225:9000/mes.asmx/ProcessInfo",
        "PlanOrderReport": "http://10.246.140.225:9000/mes.asmx/PlanOrderReport",
        "CreateSheetPull": "http://10.246.140.225:9000/mes.asmx/CreateSheetPull",
        "CallAGVOffline": "http://10.246.140.225:9000/mes.asmx/CallAGVOffline",
        "GlueUseConfirm": "http://10.246.140.225:9000/mes.asmx/GlueUseConfirm"
    }
def Cache_writer(key = "",value = "",timeout=None):
    if key == "" :
        raise Exception("Cache写入错误")
    log.info("-----lock_cache.acquire")
    lock_cache.acquire()
    cache.set(key,value,timeout)
    log.info("-----cache.set "  + str(key) + " = " + str(value))
    lock_cache.release()
    log.info("-----lock_cache.release")
# 特殊型号的站点只进行绑定就出站
def PassAfterBind(model,stno,main_name,main_code):
    log.info("---PassAfterBind")
    try:
        SQL = "SELECT * FROM station_tab WHERE gp_model = '" + model + "' and equipment_num = '" + stno + "'"
        data = SQL_function3(SQL)
        if not len(data) == 0:
            if data[0]['bind_pass'] == "True":
                # return True
                SQL = "UPDATE qr_confrimation_tab SET test_result = 'OK' WHERE station_no = '" + stno + "' and " + main_name + " = '" + main_code + "'"
                if SQL_function4(SQL):
                    return True
                else:
                    return False
            else:
                return False
        else:
            return False

    except Exception as err:
        log.info("---PassAfterBind ERROR" + str(err))
        return False


def Orderno_check(name,code,stno):          # stno 部分机台换型时使用工位来区分新旧工单下的sn码
    print(">>>>>>>>>>>>>>>>>Orderno_check")
    try:
        if not code or code.strip() == "":
            msg = "传入条码不能为空"
            log.error(msg)
            raise Exception(msg)
        current_order = cache.get('current_order')
        SQL = "SELECT order_no FROM ordersn_tab WHERE " + name + " = '" + code + "'"
        data = SQL_function3(SQL)
        if len(data) == 0:
            msg = "ordersn_tab中未找到" + code + "对应数据"
        if not data[0]['order_no'] == current_order:
            msg = "主码:" + code + " 对应工单与当前工单不符"
            raise Exception(msg)
        check_result = {
            "result": "OK",
            "msg": ""
        }
        log.info(str(check_result))
        return check_result
    except Exception as err:
        print(str(err))
        check_result = {
            "result": "NG",
            "msg": str(err)
        }
        log.info(str(check_result))
        return check_result
# 物料编码校验 用于第一站上料和后续工站绑定时进行物料号校验
#案例 pcba_code1:36091990K0A23082300174  qr_code2：CAGDW36092002990K0A00 xxxxx  lens：cckxy36091001990K0A00202310181691   物料号截取到K0A
def Partno_check(stno,name,code):
    print(">>>>>>>>>>>>>>>>>Partno_check")
    try:
        current_model = cache.get('current_model','')
        SQL = "SELECT st_current_model FROM station_tab WHERE gp_model = '" + current_model + "' and equipment_num = '" + stno + "'"
        data = SQL_function3(SQL)
        st_current_model = data[0]['st_current_model']

        name = name.upper()
        checkname = ""
        checkcode = ""
        result = "NG"
        if not Getpartno_check_flag():
            result = "OK"
            raise Exception("")

        if name == "QR_CODE1":
            checkname = "Q_PART_NO"
        elif name == "QR_CODE2":
            checkname = "H_PART_NO"
        elif name == "PCBA_CODE1" or name == "PCBA_CODE2":
            checkname = "P_PART_NO"
        elif name == "LENS":
            checkname = "J_PART_NO"
        SQL = "SELECT * FROM planorder_partno_tab WHERE gp_model = '" + st_current_model + "'"
        data = SQL_function3(SQL)
        for key in data[0]:
            if key == checkname:
                checkcode = data[0][key]
        if checkcode == "":
            raise Exception("匹配的当前物料号为空，请检查是否输入")
        elif checkcode.upper() == "NULL":
            result = "OK"
            raise Exception("当前物料号跳过匹配")
        code = code.upper()
        checkcode = checkcode.upper()

        index = code.find(checkcode)
        if not index == -1:
            check_result = {
                "result": "OK",
                "msg": "物料校验成功"
            }
            log.info(str(check_result))
            return check_result
        else:
            raise Exception("当前物料号不匹配")
    except Exception as err:
        print(str(err))
        check_result = {
            "result": result,
            "msg": str(err)
        }
        log.info(str(check_result))
        return check_result
def Remodel_getpartno_data(gp_model):
    SQL = "SELECT * FROM planorder_partno_tab WHERE gp_model = '" + gp_model + "'"
    data = SQL_function3(SQL)
    if len(data) == 0:
        msg = "未找到型号" + gp_model + "对应物料信息"
        raise Exception(msg)
    return data[0]
# 获取站位/码 对应的物料号和批次号 用于生产绑定、上传数据时记录当前物料号和批次号。 对特殊物料号进行强制校验 如螺丝胶水
def Getpartno_data(stno,bind_name,gp_model):
    ret_data = {
        "partno_code": "",
        "partbatch_code": "",
        "result": "OK",
        "msg": ""
    }
    return ret_data
    log.info(">>>>>>>>Getpartno_data")
    try:
        # 站点工艺用0x02 check时站位号对应  绑定零件用0x03 bind时用绑定码名称对应
        partno_name = ""
        partbatch_name = ""
        partno_code = ""
        partbatch_code = ""
        result = "NG"

        if stno == "" and bind_name == "":
            msg = "输入值为空，请检查"
            raise Exception(msg)
        if (not stno == "" )and (not bind_name == ""):
            msg = "只需要一个有效值，请检查"
            raise Exception(msg)

        # 过站/绑定时物料号使用记录获取 和 保存
        if not Getpartno_check_flag():
            result = "OK"
            raise Exception("")
        data = ""
        if not bind_name == "":
            bind_name = bind_name.upper()
            SQL = "SELECT * FROM planorder_partno_using_tab WHERE code_name = '" + bind_name + "'"
            data = SQL_function3(SQL)
        if not stno == "":
            stno = stno.upper()
            SQL = "SELECT * FROM planorder_partno_using_tab WHERE stno = '" + stno + "'"
            data = SQL_function3(SQL)
        # 站点匹配时可能存在单站多物料号
        for it in data:
            if it['force_check'].upper() == "TRUE":
                continue
            it_partno_name = it['partno_name']
            it_partbatch_name = it['partbatch_name']
            code_name_ch = it['code_name_ch']
            SQL = "SELECT * FROM planorder_partno_tab WHERE gp_model = '" + gp_model + "'"
            data = SQL_function3(SQL)
            if partno_code == "":
                if not data[0][it_partno_name] == "":
                    partno_code += code_name_ch + ":" + data[0][it_partno_name]
            else:
                partno_code += ";" + code_name_ch + ":" + data[0][it_partno_name]
            if partbatch_code == "":
                if not data[0][it_partbatch_name] == "":
                    partbatch_code += code_name_ch + ":" + data[0][it_partbatch_name]
            else:
                partbatch_code += ";" + code_name_ch + ":" + data[0][it_partbatch_name]

        ret_data = {
            "partno_code": partno_code,
            "partbatch_code": partbatch_code,
            "result":"OK",
            "msg":""
        }
        return ret_data
    except Exception as err:
        if result == "OK":
            ret_data = {
                "partno_code": "",
                "partbatch_code": "",
                "result": result,
                "msg": str(err)
            }
            return ret_data
        else:
            log.info(">>>>>>Getpartno_data ERROR:" + str(err))
            raise Exception(str(err))
# 获取、检查mom_setting信息是否为当天，用于生成镭雕sn和uuid前的校验
def Gettoday_numdata(t):
    SQL = "SELECT * FROM mom_setting"
    mom_data = SQL_function3(SQL)
    # 当前datetime为数据库自动更新变量，每次操作数据库后自动刷新时间
    print(t.day)
    print(datetime.datetime.strptime(mom_data[0]['datetime'], '%Y-%m-%d %H:%M:%S').day)
    t_day = t.day - datetime.datetime.strptime(mom_data[0]['datetime'], '%Y-%m-%d %H:%M:%S').day
    print(t_day)
    if not t_day == 0:
        SQL = "UPDATE mom_setting SET uuid_num = '0', sn_num = '0', sn_num_stand = '0'"
        SQL_function4(SQL)
        SQL = "SELECT * FROM mom_setting"
        mom_data = SQL_function3(SQL)
    return mom_data
# 生成镭雕sn码时获取当天sn序列号
def Getsn_num(t):
    mom_data = Gettoday_numdata(t)
    # 生产一个新的sn_num码提供使用
    x = int(mom_data[0]['sn_num']) + 1
    return x
def Getsn_num_stand(t):
    mom_data = Gettoday_numdata(t)
    # 生产一个新的支架sn_num码提供使用
    x = int(mom_data[0]['sn_num_stand']) + 1
    return x
# 上报MOM时候获取当天uuid序列号
def Getuuid_num(t):
    if not lock_uuid.acquire(timeout=10):
        log.info("Getuuid_num locked")
        raise Exception("ERROR: Getuuid_num locked")

    try:
        log.info("Getuuid_num lock_uuid.acquire")
        mom_data = Gettoday_numdata(t)
        x = int(mom_data[0]['uuid_num'])
        mom_uuid2 = str(x).zfill(6)
        SQL = "UPDATE mom_setting SET uuid_num = '" + str(x + 1) + "'"
        SQL_function4(SQL)
        log.info("Getuuid_num lock_uuid.release")
        return mom_uuid2
    finally:
        lock_uuid.release()
# ----------------------------本地ini文件读取方法---------------------------
# 获取Django web访问ip
def Getmyip():
    filepath = GetFilePath("SoftWare.ini")
    conf = ConfigParser()  # 需要实例化一个ConfigParser对象
    conf.read(filepath)  # 需要添加上config.ini的路径，不需要open打开，直接给文件路径就读取，也可以指定encoding='utf-8'
    myip = conf['CommonUse']['myip']
    return myip
# 获取MQTT 线体内部访问ip
def Getmyip_line():
    filepath = GetFilePath("SoftWare.ini")
    conf = ConfigParser()  # 需要实例化一个ConfigParser对象
    conf.read(filepath)  # 需要添加上config.ini的路径，不需要open打开，直接给文件路径就读取，也可以指定encoding='utf-8'
    myip = conf['CommonUse']['myip_line']
    return myip
#1线或者2线
def Getline_no():
    filepath = GetFilePath("SoftWare.ini")
    conf = ConfigParser()  # 需要实例化一个ConfigParser对象
    conf.read(filepath)  # 需要添加上config.ini的路径，不需要open打开，直接给文件路径就读取，也可以指定encoding='utf-8'
    line_no = conf['CommonUse']['line_no']
    return line_no
# 获取线体绑定数据列名称，方便在checksn插入成功后更新qr_confrimation_tab中新的站位信息中对应的绑定信息
def GetBindcolumn_name():
    filepath = GetFilePath("SoftWare.ini")
    conf = ConfigParser()  # 需要实例化一个ConfigParser对象
    conf.read(filepath)  # 需要添加上config.ini的路径，不需要open打开，直接给文件路径就读取，也可以指定encoding='utf-8'
    bindcolumn_name = conf['CommonUse']['bindcolumn_name']
    bindcolumn_name = bindcolumn_name.replace("'", '"')
    bindcolumn_name = eval(bindcolumn_name)
    print(type(bindcolumn_name))
    print(bindcolumn_name)
    return bindcolumn_name
def Getpartno_check_flag():
    filepath = GetFilePath("SoftWare.ini")
    conf = ConfigParser()  # 需要实例化一个ConfigParser对象
    conf.read(filepath)  # 需要添加上config.ini的路径，不需要open打开，直接给文件路径就读取，也可以指定encoding='utf-8'
    partno_check_flag = conf['CommonUse']['partno_check_flag']
    if partno_check_flag.upper() == "TRUE":
        return True
    elif partno_check_flag.upper() == "FALSE":
        return False
    else:
        raise Exception("partno_check_flag 数据不为True or False,请检查")
    return partno_check_flag
# 记录当前实际的胶水号
def Setjs_part_no(js_part_no):
    filepath = GetFilePath("SoftWare.ini")
    conf = ConfigParser()  # 需要实例化一个ConfigParser对象
    conf.read(filepath)  # 需要添加上config.ini的路径，不需要open打开，直接给文件路径就读取，也可以指定encoding='utf-8'
    conf.set('CommonUse', 'js_part_no', js_part_no)
    with open(filepath, 'w', encoding='utf-8') as f:
        conf.write(f)
# 保存当前实际的胶水号
def Getjs_part_no_msg():
    filepath = GetFilePath("SoftWare.ini")
    conf = ConfigParser()  # 需要实例化一个ConfigParser对象
    conf.read(filepath)  # 需要添加上config.ini的路径，不需要open打开，直接给文件路径就读取，也可以指定encoding='utf-8'
    js_part_no = conf['CommonUse']['js_part_no']
    js_part_no_time = conf['CommonUse']['js_part_no_time']
    js_part_no_flag = conf['CommonUse']['js_part_no_flag']
    Cache_writer("js_part_no", js_part_no)
    Cache_writer("js_part_no_time", js_part_no_time)
    Cache_writer("js_part_no_flag", js_part_no_flag)
# 记录当前实际的胶水号是否合法
def Setjs_part_no_msg(js_part_no, js_part_no_flag, js_part_no_time):
    filepath = GetFilePath("SoftWare.ini")
    conf = ConfigParser()  # 需要实例化一个ConfigParser对象
    conf.read(filepath)  # 需要添加上config.ini的路径，不需要open打开，直接给文件路径就读取，也可以指定encoding='utf-8'
    conf.set('CommonUse', 'js_part_no', js_part_no)
    conf.set('CommonUse', 'js_part_no_flag', js_part_no_flag)
    conf.set('CommonUse', 'js_part_no_time', js_part_no_time)
    with open(filepath, 'w', encoding='utf-8') as f:
        conf.write(f)
# ----------------------------本地ini文件读取方法---------------------------
def xml_to_json(xml_str):
    # parse是的xml解析器
    xml_parse = xmltodict.parse(xml_str)
    # json库dumps()是将dict转化成json格式,loads()是将json转化成dict格式。
    # dumps()方法的ident=1,格式化json
    json_str = json.dumps(xml_parse, ensure_ascii=False)
    return json_str

def SendMessage2MOM(param, url, test_result = ""):
    # client = Client(url)  # 创建一个webservice接口对象
    # resp = client.service.test(data)  # 调用这个接口下的get_version方法
    print(">>>>>SendMessage2MOM")
    print(param)
    log.info(">>>>>SendMessage2MOM")
    log.info(url)
    log.info(param)
    # print(json.loads(resp))
    text = ""
    # param = urlencode(param)  # key关键点
    fails = 0
    while True:
        try:
            if fails >= 2:
                print('网络连接出现问题>2次,发送失败')
                break
            # headers = {'content-type': 'application/json'}
            headers = {'content-type': 'application/x-www-form-urlencoded'}
            # headers = {'content-type': 'text/xml'}

            # POST形式发送信息
            ret = requests.post(url, data={'JsonStr': str(param)}, headers=headers, timeout=2)  # timeout 超时（秒）
            # GET形式发送信息
            # ret = requests.get(url=url, params=param, headers=headers, timeout=2)
            log.info("----------mom_ret----------")
            log.info(ret.status_code)
            log.info(ret.text)
            print(">>>>>requests:")
            print(ret.status_code)
            print("text:")
            print(ret.text)
            if ret.status_code == 200:#200 success 500 error
                text = ret.text
                text = xml_to_json(text)
                text = json.loads(text)
                text = text['string']['#text']
            else:
                fails += 1
                continue
        except:
            fails += 1
            print('网络连接出现问题, 正在尝试再次请求: ', fails)
            log.info("网络连接出现问题, 正在尝试再次请求")
        else:
            break
    if fails >= 2:
        text = {
            "STATUS": "NG",
            "ERRORMSG": "网络错误上传MOM失败"
        }
        # 判断MOM上传失败线体是否报警
        if not MomAlerm_Check():
            # 发送失败存储到本地数据库
            if MomMessageRecord(url, param, test_result):
                # 发送失败消息给看板
                viewboard_topic = "Msg2Station/ViewBoard"
                param = json.loads(str(param).replace("'", '"'))
                if isinstance(param, list):
                    param = param[0]
                viewboard_data_send = {
                    "Command": "S002",
                    "Station_No": "",
                    "Station_Name": "",
                    "Status": 3,  # 0正常  1断开  2故障  3上传MOM失败
                    "Message": "上传MOM失败,已保存"
                }
                SendMessage2Station(viewboard_topic, viewboard_data_send)
                text = {"STATUS": "NG","NGSOURCE": "TIMEOUT", "ERRORMSG": "上传MOM失败,已保存"}
                text = json.dumps(text)
            else:
                # msg = "上传MOM失败,记录保存失败,请检查Mes"
                # raise Exception(msg)
                text = {"STATUS": "NG", "NGSOURCE": "SQLINSERT", "ERRORMSG": "上传MOM失败,记录保存失败,请检查Mes"}
                text = json.dumps(text)
        else:
            # 发送失败消息给看板
            viewboard_topic = "Msg2Station/ViewBoard"
            param = json.loads(str(param).replace("'", '"'))
            if isinstance(param, list):
                param = param[0]
            viewboard_data_send = {
                "Command": "S002",
                "Station_No": "",
                "Station_Name": "",
                "Status": 3,  # 0正常  1断开  2故障  3上传MOM失败
                "Message": "上传MOM失败,已保存"
            }
            SendMessage2Station(viewboard_topic, viewboard_data_send)
            text = {"STATUS": "NG" ,"NGSOURCE": "TIMEOUT" , "ERRORMSG": "上传MOM失败"}
            text = json.dumps(text)

    print(">>>>>ReceiveMessageFromMOM")
    log.info(">>>>>ReceiveMessageFromMOM")
    log.info(text)
    return text
# 上传MOM超时后是否线体报警
def MomAlerm_Check():
    filepath = GetFilePath("SoftWare.ini")
    conf = ConfigParser()  # 需要实例化一个ConfigParser对象
    conf.read(filepath)  # 需要添加上config.ini的路径，不需要open打开，直接给文件路径就读取，也可以指定encoding='utf-8'
    mom_alarm = conf['CommonUse']['mom_alarm']
    if mom_alarm.upper() == "TRUE":
        return True
    else:
        return False
def MomMessageRecord(send_url, param, test_result):
    log.info(">>>>>>>>MomMessageRecord")
    if not (send_url == url['PlanOrderConfirm'] or send_url == url['ProcessInfo']):
        return True
    t = datetime.datetime.now()

    # param = eval(str(param))
    param = json.loads(str(param).replace("'", '"'))
    log.info(param)
    if isinstance(param,list):
        param_temp = param[0]
    else:
        param_temp = param

    sn = param_temp['SN']
    gp_model = ""
    order_no = ""
    station_no = ""
    code_name = ""

    SQL = "SELECT * FROM mom_message WHERE sn = '" + sn + "'"
    data = SQL_function3(SQL)
    if len(data) > 0:
        print("已经存在该sn离线数据记录,不记录")
        log.info("已经存在该sn离线数据记录，不记录")
        return True
    # 获取order_no和gp_model   主码只可能是前壳码或后壳码支架码  所以暂时只对这两种进行搜索
    maincode_list = ['qr_code1','qr_code2']
    for it in maincode_list:
        SQL = "SELECT qr_confrimation_tab.gp_model,ordersn_tab.order_no,ordersn_tab.current_station FROM qr_confrimation_tab,ordersn_tab where ordersn_tab." + it + " = '" + sn + "' and qr_confrimation_tab." + it + " = '" + sn + "'"
        data = SQL_function3(SQL)
        if not len(data) == 0:
            code_name = it
            gp_model = data[0]['gp_model']
            order_no = data[0]['order_no']
            station_no = data[0]['current_station']
            break
    else:
        SQL = "SELECT qr_confrimation_tab_sp.gp_model,ordersn_tab.order_no,ordersn_tab.current_station FROM qr_confrimation_tab_sp,ordersn_tab where ordersn_tab.stand_code= '" + sn + "' and qr_confrimation_tab_sp.stand_code = '" + sn + "'"
        data = SQL_function3(SQL)
        if not len(data) == 0:
            code_name = "stand_code"
            gp_model = data[0]['gp_model']
            order_no = data[0]['order_no']
            station_no = data[0]['current_station']
        else:
            msg = "数据库未找到当前主码" + sn + "信息"
            raise Exception(msg)

    SQL = "INSERT INTO mom_message (url,sn,code_name,datetime,gp_model,order_no,station_no,test_result) Value ( '" + send_url + "','" + sn + "','" + code_name + "','" + str(t) + "','" + gp_model + "','" + order_no + "','" + station_no + "','" + test_result + "')"
    if SQL_function4(SQL):
        print("记录离线数据成功")
        log.info("记录离线数据成功")
        return True
    else:
        msg = sn + "上传MOM失败,记录离线数据失败,请检查Mes"
        log.info(msg)
        raise Exception(msg)

def SendMessage2Station(topic, data):
    try:
        # # 通过Broker内部直接回复
        # data = json.dumps(data,ensure_ascii=False)
        # log.info("SendMessage2Station" + str(data))
        # dic_msg = {"data":data.encode('utf-8'), "topic":topic}
        # reply_msgs.append(dic_msg)
        # log.info("reply_msgs:" + str(reply_msgs))

        # 通过mqtt客户端回复
        data = json.dumps(data, ensure_ascii=False)
        log.info("SendMessage2Station_byclient" + str(data))
        publish(topic, data)
    except Exception as err:
         log.info("SendMessage2Station ERROR:" + str(err))
# 服务启动后向看板发送站点连接状态看板初始化
def Board_Init():
    log.info("Msg2Station/ViewBoard : Init Message")
    topic = "Msg2Station/ViewBoard"
    device_class = cache.get('DeviceClass')
    for it in device_class:
        viewboard_data_send = {}
        if it['EquipError'] is True:
            viewboard_data_send = {
                "Command": "S002",
                "Station_No": it['EquipNumber'],
                "Station_Name": it['EquipName'],
                "Status": 2,  # 0正常  1断开  2故障
                "Message": ""
            }
            # data = json.dumps(viewboard_data_send, ensure_ascii=False)  # 防止汉字编码乱码
            # publish(topic, data)
            print(viewboard_data_send)
            SendMessage2Station(topic, viewboard_data_send)
            continue
        else:
            if it['EquipStatus'] is True:
                # print("TRUE")
                viewboard_data_send = {
                    "Command": "S002",
                    "Station_No": it['EquipNumber'],
                    "Station_Name": it['EquipName'],
                    "Status": 0,  # 0正常  1断开  2故障
                    "Message": ""
                }
                # data = json.dumps(viewboard_data_send, ensure_ascii=False)  # 防止汉字编码乱码
                # publish(topic, data)
                print(viewboard_data_send)
                SendMessage2Station(topic, viewboard_data_send)
                continue
            elif it['EquipStatus'] is False:
                # print("FALSE")
                viewboard_data_send = {
                    "Command": "S002",
                    "Station_No": it['EquipNumber'],
                    "Station_Name": it['EquipName'],
                    "Status": 1,  # 0正常  1断开  2故障
                    "Message": ""
                }
                # data = json.dumps(viewboard_data_send, ensure_ascii=False)  # 防止汉字编码乱码
                # publish(topic, data)
                print(viewboard_data_send)
                SendMessage2Station(topic, viewboard_data_send)
                continue

# 看板重连、断联初始化发送所有机台信息
# 机台重连记录时间和次数
def JudgeTopic(topic, type):

    # 机器断连期间的时间也得算入时间记录，此时可以借助这个函数，未完成待补充
    log.info("JudgeTopic: " + topic)
    #查看传来的主题是否为看板的，如是，那就得发送初始数据
    if topic.upper() == "Msg2Station/ViewBoard".upper():
        # t = Thread(target=Board_Init())
        # t.start()
        t1 = threading.Thread(target=Board_Init, args=())
        t1.start()
        # future = threadPool.submit(Board_Init)
    else:
        topic_1 = topic.split("/")[0]
        topic_2 = topic.split("/")[1]

        log.info(topic_1 + "  " + topic_2)

        if topic_1 == "Msg2Station":
            t = datetime.datetime.now()
            month = t.month
            year = t.year
            if type is True:
                Time_Record_Counter(0, topic_2, year, month)
            elif type is False:
                Time_Record_Counter(2, topic_2, year, month)

# def SQL_function(SQL):
#     print(SQL)
#     t = MyThread(easy_sql_reader, (SQL,))
#     t.start()
#     data = t.get_result()
#     print(data)
#     print(len(data))
#     return data
#
# def SQL_function2(SQL):
#     print(SQL)
#     t = MyThread(sql_execute, (SQL,))
#     t.start()
#     data = t.get_result()
#     print(data)
#     return data
def SQL_function(SQL):
    print(SQL)
    data = easy_sql_reader(SQL)
    print(data)
    print(len(data))
    return data

def SQL_function2(SQL):
    print(SQL)
    data = sql_execute(SQL)
    print(data)
    log.info(data)
    return data
def SQL_function3(SQL):
    print(SQL)
    log.info(SQL)
    # [修复] 移除重复查询，原代码调用了两次easy_sql_reader导致数据库负载翻倍
    # data = easy_sql_reader(SQL)
    # log.info(data)
    # # 添加调用栈日志
    # stack = traceback.extract_stack()[-2]
    # log.info(f"调用来源: {stack.filename}:{stack.lineno} -> {stack.name}")
    # data = easy_sql_reader(SQL)
    # log.info(f"查询结果: {len(data)} 条")
    data = easy_sql_reader(SQL)
    log.info(data)
    stack = traceback.extract_stack()[-2]
    log.info(f"调用来源: {stack.filename}:{stack.lineno} -> {stack.name}")
    log.info(f"查询结果: {len(data)} 条")
    return data
def asy_SQL_function3(SQL,tag):
    print(SQL)
    log.info(SQL)
    data = easy_sql_reader(SQL)
    log.info(data)
    ret_data = {tag : data}
    return ret_data

def SQL_function4(SQL):
    print(SQL)
    log.info(SQL)
    data = sql_execute(SQL)
    log.info(data)
    return data
def SQL_function_long(SQL):
    print(SQL)
    log.info(SQL)
    data = long_sql_reader(SQL)
    # print(data)
    log.info(data)
    print(len(data))
    return data
def SQL_function_qr_confrimation_tab(SQL):
    print(SQL)
    log.info(SQL)
    data = json.loads(serializers.serialize("json", md.qr_confrimation_tab.objects.raw(SQL)))
    # print(data)
    return data
def Select_Column_from_Tab(data_columns, TestItem):
    for it1 in data_columns:
        if it1['COLUMN_NAME'].upper() == TestItem.upper():
            print(it1['COLUMN_NAME'] + " : " + TestItem)
            return False
    print("NONE Cloumnname" + " : " + TestItem)
    return True
    # SQL = "SELECT count(*) FROM information_schema.COLUMNS WHERE table_name = '" + TabName + "' and column_name = '" + TestItem + "'"
    # data = SQL_function(SQL)
    # if data[0]['count(*)'] == "0":
    #     return True
    # else:
    #     return False
def Alter_Column(TabName, TestItem):
    if TestItem == "":
        msg = "数据上传失败,测试项名称不可为空"
        raise Exception(msg)
    Tag = False
    AlterStringGroup = ["ALTER TABLE "+ TabName +" ADD `"+ TestItem +"` VarChar(50) DEFAULT NULL","ALTER TABLE "+ TabName +" ADD `"+ TestItem +"_Result` VarChar(50) DEFAULT NULL"]
    for it in AlterStringGroup:
        if SQL_function4(it):
            Tag = True
        else:
            Tag = False
            break
    return Tag

def Update_Model_Quantity(Gp_Model, Test_Result):
    if Test_Result.upper() == "OK":
        SQL = "SELECT Pass FROM model_tab WHERE gp_model = '" + Gp_Model + "'"
        data = SQL_function(SQL)
        Quantity = str(int(data[0]['Pass']) + 1)
        SQL = "UPDATE model_tab set Pass = '" + Quantity + "' WHERE gp_model = '" + Gp_Model + "'"
        SQL_function2(SQL)
        return True
    elif Test_Result.upper() == "NG":
        SQL = "SELECT Fail FROM model_tab WHERE gp_model = '" + Gp_Model + "'"
        data = SQL_function(SQL)
        Quantity = str(int(data[0]['Fail']) + 1)
        SQL = "UPDATE model_tab set Fail = '" + Quantity + "' WHERE gp_model = '" + Gp_Model + "'"
        SQL_function2(SQL)
        return True
    return False

def ReciveOrder_Analysis(data):
    command = data['Command']
    Station_No = data['Station_No']
    equip_status = cache.get('Equip_Status')
    device_class = cache.get('DeviceClass')
    current_model = cache.get("current_model")
    for item in equip_status:
        if item['EquipNumber'] == Station_No:
            print(datetime.datetime.now())
            if command == "0x05":                        #（在一键下发的情况下）收到换型的返回信息后，向下一站再次发送换型信息
                print("0x05")                            # 普通换型 和 选择机台换型 只会修改打勾机台状态 （注意并发时的数据读写问题）
                item['EquipOrder'] = 'Remodel'
                item['EquipResult'] = data['Result']
                Cache_writer("Equip_Status", equip_status, None)
                log.info(">>>>>> ModelSetFlag: " + str(cache.get('ModelSetFlag', default=0)))
                print(">>>>>> ModelSetFlag: " + str(cache.get('ModelSetFlag', default=0)))
                if data['Result'] == "OK" and cache.get('ModelSetFlag', default=0) == 1:    # 1 一键下发  2  选择机台下发
                    for i in range(0,len(device_class)):
                        if(device_class[i]['EquipNumber'] == Station_No and i != len(device_class)-1):
                            topic = "Msg2Station/" + device_class[i+1]['EquipNumber']
                            print(topic)
                            send_data = {
                                "Command": "0x05",
                                "Gp_Model": current_model
                            }
                            # 换型下发物料号信息
                            partno_data = Remodel_getpartno_data(current_model)
                            send_data['Q_PART_NO'] = partno_data['Q_PART_NO']
                            send_data['H_PART_NO'] = partno_data['H_PART_NO']
                            send_data['P_PART_NO'] = partno_data['P_PART_NO']
                            send_data['J_PART_NO'] = partno_data['J_PART_NO']
                            send_data['ZC_PART_NO'] = ""
                            log.info("quick_remodel:" + str(send_data))
                            SendMessage2Station(topic, send_data)
            elif command == "0x06":
                item['EquipOrder'] = 'Clean'
                item['EquipResult'] = data['Result']
                Cache_writer("Equip_Status", equip_status, None)
                if data['Result'] == "OK":
                    for i in range(0, len(device_class)):
                        if (device_class[i]['EquipNumber'] == Station_No and i != len(device_class) - 1):
                            topic = "Msg2Station/" + device_class[i + 1]['EquipNumber']
                            send_data = {
                                "Command": "0x06",
                                "Gp_Model": current_model
                            }
                            SendMessage2Station(topic, send_data)
            elif command == "0x07":
                print("0x07为MES下发的开始命令,机台返回统一使用0x17中的0返回状态")
                # item['EquipOrder'] = "Start"
                # item['EquipResult'] = data['Result']
                # Cache_writer("Equip_Status", equip_status, None)
            elif command == "0x08":
                print("0x08为MES下发的停机命令,机台返回统一使用0x17中的1返回状态")
                # item['EquipOrder'] = "Stop"
                # item['EquipResult'] = data['Result']
                # Cache_writer("Equip_Status", equip_status, None)
            elif command == "0x09":
                item['EquipOrder'] = "Reset"
                item['EquipResult'] = data['Result']
                Cache_writer("Equip_Status", equip_status, None)
            elif command == "0x13":
                item['EquipOrder'] = "ReMesStatus"
                item['EquipResult'] = data['Result']
                Cache_writer("Equip_Status", equip_status, None)
            elif command == "0x15":                             #治具确认
                item['EquipOrder'] = "CheckCarrier"
                item['EquipResult'] = data['Result']
                Cache_writer("Equip_Status", equip_status, None)
            elif command == "0x16":                             #点检
                item['EquipOrder'] = "CheckDevice"
                item['EquipResult'] = data['Result']
                Cache_writer("Equip_Status", equip_status, None)
    # 治具点检功能现全部由第一台机器负责确认
    if Station_No == "ST01" and command == "0x15":
        for item in equip_status:
            item['EquipOrder'] = "CheckCarrier"
            item['EquipResult'] = data['Result']
            Cache_writer("Equip_Status", equip_status, None)
# 换型后，非当前型号下已经连接的机台专用时间记录函数
def Time_Record_StopOnline(STNO):
    t = datetime.datetime.now()
    month = t.month
    year = t.year

    delta_t = cache.get('delta_t' ,default=None)
    if delta_t is None:
        delta_t = 5

    SQL = "SELECT stop FROM sta_total WHERE year = '" + str(year) + "' and month = '" + str(
        month) + "' and stano = '" + STNO + "'"
    data = SQL_function3(SQL)
    if len(data) == 0:
        SQL = "INSERT INTO sta_total (stano,normal,fatal,stop,year,month,normal_num,fatal_num,stop_num) Value ('" + STNO + "','0','0','0','" + str(
            year) + "','" + str(month) + "'," + str(0) + "," + str(0) + "," + str(0) + ")"
        if SQL_function4(SQL):
            print("插入新时间记录成功")
        else:
            print("插入新时间记录失败")
        SQL = "SELECT stop FROM sta_total WHERE year = '" + str(year) + "' and month = '" + str(
            month) + "' and stano = '" + STNO + "'"
        data = SQL_function3(SQL)

    delta_t += int(data[0]['stop'])
    SQL = "UPDATE sta_total set stop = '" + str(delta_t) + "' WHERE year = '" + str(
        year) + "' and month = '" + str(month) + "' and stano = '" + STNO + "'"
    if SQL_function4(SQL):
        print("修改" + STNO + "等待时间成功")
    else:
        print("修改" + STNO + "等待时间失败")

    # stoponline_time = cache.get('stoponline_time', default=None)
    # if stoponline_time is None:
    #     stoponline_time = t
    #     Cache_writer('stoponline_time', stoponline_time, None)
    #     delta_t = 5
    # else:
    #     delta_t = (t - stoponline_time).seconds
    #     if delta_t > 6:
    #         msg = "时间过久，重新记录"
    #         stoponline_time = t
    #         Cache_writer('stoponline_time', stoponline_time, None)
    #         delta_t = 5
def Time_Record_Counter(type, stno, year, month):
    try:
        # 供看板显示使用
        # 记录开机之后 开始 停机 错误的次数  停机换型算stop次数，报警算fatal次数，其中设备刚建立连接时算normal次数，其中出现换型、停机后的恢复开始状态不算normal
        # sta_total 下总状态记录
        SQL = "SELECT * FROM sta_total WHERE year = '" + str(year) + "' and month = '" + str(
            month) + "' and stano = '" + stno + "'"
        # thread_name("Time_Record_Counter")
        data = SQL_function3(SQL)

        if len(data) == 0:
            SQL = "INSERT INTO sta_total (stano,normal,fatal,stop,year,month,normal_num,fatal_num,stop_num) Value ('" + stno + "','0','0','0','" + str(
                year) + "','" + str(month) + "'," + str(0) + "," + str(0) + "," + str(0) + ")"
            if SQL_function4(SQL):
                print("插入新时间记录成功")
                # 插入新的时间说明切换到下个月，此时应该给内存中时间缓存清空，重新计算。但是要有提前保存上个月的逻辑 未完成 待补充
            else:
                print("插入新时间记录失败")
        if type == 0:
            SQL = "SELECT normal_num FROM sta_total WHERE year = '" + str(year) + "' and month = '" + str(
                month) + "' and stano = '" + stno + "'"
            data = SQL_function3(SQL)
            normal_time = int(data[0]['normal_num']) + 1

            SQL = "UPDATE sta_total set normal_num = " + str(normal_time) + " WHERE year = '" + str(
                year) + "' and month = '" + str(month) + "' and stano = '" + stno + "'"
            if SQL_function4(SQL):
                print("normal_num:修改" + stno + ": normal时间成功")
                log.info("normal_num:修改" + stno + ": normal时间成功")
            else:
                print("normal_num:修改" + stno + ": normal时间失败")
                log.info("normal_num:修改" + stno + ": normal时间失败")
        if type == 2 or type == 4:
            SQL = "SELECT stop_num FROM sta_total WHERE year = '" + str(year) + "' and month = '" + str(
                month) + "' and stano = '" + stno + "'"
            data = SQL_function3(SQL)
            stop_time = int(data[0]['stop_num']) + 1

            SQL = "UPDATE sta_total set stop_num = " + str(stop_time) + " WHERE year = '" + str(
                year) + "' and month = '" + str(month) + "' and stano = '" + stno + "'"
            if SQL_function4(SQL):
                print("stop_num:修改" + stno + ": stop时间成功")
                log.info("stop_num:修改" + stno + ": stop时间成功")
            else:
                log.info("stop_num:修改" + stno + ": stop时间失败")
                print("stop_num:修改" + stno + ": stop时间失败")
        if type == 3:
            SQL = "SELECT fatal_num FROM sta_total WHERE year = '" + str(year) + "' and month = '" + str(
                month) + "' and stano = '" + stno + "'"
            data = SQL_function3(SQL)
            fatal_time = int(data[0]['fatal_num']) + 1

            SQL = "UPDATE sta_total set fatal_num = " + str(fatal_time) + " WHERE year = '" + str(
                year) + "' and month = '" + str(month) + "' and stano = '" + stno + "'"
            if SQL_function4(SQL):
                print("fatal_num:修改" + stno + ": fatal时间成功")
                log.info("fatal_num:修改" + stno + ": fatal时间成功")
            else:
                log.info("fatal_num:修改" + stno + ": fatal时间失败")
                print("fatal_num:修改" + stno + ": fatal时间失败")
    except Exception as err:
        print("Time_Record_Counter ERROR: " + str(err))
        log.info("Time_Record_Counter ERROR: " + str(err))

 # type:-1 新上料 0 开始 start 1 成功结束(一个生产完成) 2 stop 3 报警  4 remodel /  tag_st:  True对部分机台，False对当前产线
def Time_Record(stno,type,tag_st):  
    try:
        print("lock3.acquire")
        log.info("lock3.acquire")
        lock3.acquire()
        log.info(">>>>>Time_Record" + "stno:" + stno + " TYPE:" + str(type) + " tag_st:" + str(tag_st))  # status: 0 开始 start 1 remodel 2 stop 3 报警
        equip_time = cache.get('EquipTime', default=None)
        equip_time_st = cache.get('EquipTimeST', default=None)
        equip_status = cache.get('Equip_Status', default=None)
        t = datetime.datetime.now()
        month = t.month
        year = t.year
        # sta_total 记录是否存在，不存在就创建新的
        SQL = "SELECT * FROM sta_total WHERE year = '" + str(year) + "' AND month = '" + str(
            month) + "' AND stano = '" + stno + "'"
        data = SQL_function3(SQL)
        if len(data) == 0:
            SQL = "INSERT INTO sta_total (stano,normal,fatal,stop,year,month,normal_num,fatal_num,stop_num) Value ('" + stno + "','0','0','0','" + str(
                year) + "','" + str(month) + "'," + str(0) + "," + str(0) + "," + str(0) + ")"
            if SQL_function4(SQL):
                print("插入新时间记录成功")
                # 插入新的时间说明切换到下个月，此时应该给内存中时间缓存清空，重新计算。但是要有提前保存上个月的逻辑 未完成 待补充
            else:
                print("插入新时间记录失败")

        if type != 0:
            Time_Record_Counter(type, stno, year, month)

        # if type == -1:   # 上料checksn成功,记录本次上料和上次上料的时间差  单一站台时间的计算和产线时间的计算是分开的
        #     if stno == "ST01":
        #         SQL = "UPDATE ordersn_tab set online_time = '" + t + "' WHERE year = '" + str(
        #             year) + "' and month = '" + str(month) + "' and stano = '" + stno + "'"
        #     # SQL = "SELECT * FROM ordersn_tab WHERE current_station = '" + stno + "'"
        #     # data = SQL_function3(SQL)
        #     # delta_t = (t - data[0]['laststation_time']).seconds

        if type == 0:  # start
            # equip_time = {"StartTime": t, "ErrorTime": t, "EndTime": t, "Status": 0}
            # 切换单机的特殊状态 记录时间
            if tag_st is True:
                for item in equip_time_st:
                    if item['STNO'] == stno:
                        if item['Status'] == 1:  # 0 正常生产 1 选择机台换型 2 stop  3 error
                            item['Status'] = 0
                            delta_t = (t - item['EndTime']).seconds
                            item['StartTime'] = t
                            SQL = "SELECT stop FROM sta_total WHERE year = '" + str(year) + "' and month = '" + str(
                                month) + "' and stano = '" + stno + "'"
                            data = SQL_function3(SQL)
                            delta_t += int(data[0]['stop'])
                            SQL = "UPDATE sta_total set stop = '" + str(delta_t) + "' WHERE year = '" + str(
                                year) + "' and month = '" + str(month) + "' and stano = '" + stno + "'"
                            if SQL_function4(SQL):
                                print("部分机台换型--开始:修改" + stno + ": stop时间成功")
                            else:
                                print("部分机台换型--开始:修改" + stno + ": stop时间失败")
                        elif item['Status'] == 2:
                            item['Status'] = 0
                            item['StartTime'] = t
                            delta_t = (t - item['EndTime']).seconds
                            SQL = "SELECT stop FROM sta_total WHERE year = '" + str(year) + "' and month = '" + str(
                                month) + "' and stano = '" + stno + "'"
                            data = SQL_function3(SQL)
                            delta_t += int(data[0]['stop'])
                            SQL = "UPDATE sta_total set stop = '" + str(delta_t) + "' WHERE year = '" + str(
                                year) + "' and month = '" + str(month) + "' and stano = '" + stno + "'"
                            if SQL_function4(SQL):
                                print("stop--开始:修改" + stno + ": stop时间成功")
                            else:
                                print("stop--开始:修改" + stno + ": stop时间失败")
                        elif item['Status'] == 3:
                            item['Status'] = 0
                            item['StartTime'] = t
                            delta_t = (t - item['ErrorTime']).seconds
                            SQL = "SELECT fatal FROM sta_total WHERE year = '" + str(year) + "' and month = '" + str(
                                month) + "' and stano = '" + stno + "'"
                            data = SQL_function3(SQL)
                            delta_t += int(data[0]['fatal'])
                            SQL = "UPDATE sta_total set fatal = '" + str(delta_t) + "' WHERE year = '" + str(
                                year) + "' and month = '" + str(month) + "' and stano = '" + stno + "'"
                            if SQL_function4(SQL):
                                print("error--开始:修改" + stno + ": fatal时间成功")
                            else:
                                print("error--开始:修改" + stno + ": fatal时间失败")
                        break
                Cache_writer('EquipTimeST', equip_time_st, None)
                # # 如光st里面全部都由error变成正常 ，修改全线equip_time 为正常
                # sta_tag = True
                # for item in equip_time_st:
                #     if item['Status'] != 0:
                #         sta_tag = False
                # if sta_tag:
                #     equip_time['Status'] = 0
                #     Cache_writer('EquipTime', equip_time, None)

                print(cache.get('EquipTimeST'))
            # 是切换全产线的状态 记录时间,只在需要点检的第一站进行一次时间记录，后面的点检站不记录(避免重复记录)
            if tag_st is False:
                if equip_time['Status'] == 0:  # 0 正常(点检) 变正常
                    t0 = equip_time['StartTime']
                    equip_time['StartTime'] = t
                    Cache_writer('EquipTime', equip_time, None)
                    delta_t = (t - t0).seconds
                    Cache_writer('delta_t', delta_t, None)

                    log.info("StartTime:" + str(t0) + "  " + "delta_t:" + str(delta_t))

                    print(">>>>>delta_t")
                    print(delta_t)

                    # 此处记录 start--start  之间时间间隔作为全线正常生产时候的时间记录，只卡控第一站/第一台点检站(未定) 进入，顺带修改其他站台正常生产时间
                    equipnumgroup = cache.get('EquipNumGroup')
                    for it_stno in equipnumgroup:
                        # 因为其余站被卡控无法进入该记录时间函数，所以单独检查其他站是否存在数据库信息，没有就创建
                        SQL = "SELECT * FROM sta_total WHERE year = '" + str(year) + "' AND month = '" + str(
                            month) + "' AND stano = '" + it_stno + "'"
                        data = SQL_function3(SQL)
                        if len(data) == 0:
                            SQL = "INSERT INTO sta_total (stano,normal,fatal,stop,year,month,normal_num,fatal_num,stop_num) Value ('" + it_stno + "','0','0','0','" + str(
                                year) + "','" + str(month) + "'," + str(0) + "," + str(0) + "," + str(0) + ")"
                            if SQL_function4(SQL):
                                print("插入新时间记录成功")
                            else:
                                print("插入新时间记录失败")

                        SQL = "SELECT normal FROM sta_total WHERE year = '" + str(year) + "' and month = '" + str(
                            month) + "' and stano = '" + it_stno + "'"

                        data = SQL_function3(SQL)
                        delta_t_new = delta_t + int(data[0]['normal'])
                        # print(delta_t)
                        SQL = "UPDATE sta_total set normal = '" + str(delta_t_new) + "' WHERE year = '" + str(
                            year) + "' and month = '" + str(month) + "' and stano = '" + it_stno + "'"
                        if SQL_function4(SQL):
                            print("st修改normal时间成功")
                            log.info("st修改normal时间成功")

                    # print(cache.get('EquipTime'))
                    # Cache_writer('EquipTime', equip_time, None)
                    # print(cache.get('EquipTime'))
                elif equip_time['Status'] == 1:  # 1 换型变正常
                    # 未完成 待完善     变start前要判断点检  要添加点检信息系统(已经添加)
                    # equip_time['Status'] = 0
                    print(equip_time)
                    delta_t = (t - equip_time['EndTime']).seconds
                    equip_time['StartTime'] = t

                    # 全线下所有机台都变start之后才能修改Status为0
                    temptag = True
                    equip_status = cache.get('Equip_Status')
                    for item in equip_status:
                        if item['EquipOrder'].upper() != "START":
                            temptag = False
                    if temptag:
                        equip_time['Status'] = 0
                        Cache_writer('EquipTime', equip_time, None)

                    SQL = "SELECT stop FROM sta_total WHERE year = '" + str(year) + "' and month = '" + str(
                        month) + "' and stano = '" + stno + "'"
                    data = SQL_function3(SQL)
                    delta_t += int(data[0]['stop'])
                    SQL = "UPDATE sta_total set stop = '" + str(delta_t) + "' WHERE year = '" + str(
                        year) + "' and month = '" + str(month) + "' and stano = '" + stno + "'"
                    if SQL_function4(SQL):
                        print("全线:换型--开始:修改stop时间成功")
                        log.info("全线:换型--开始:修改stop时间成功")
                    else:
                        print("全线:换型--开始:修改stop时间失败")
                        log.info("全线:换型--开始:修改stop时间失败")
                    Cache_writer('EquipTime', equip_time, None)
                    print(cache.get('EquipTime'))
                elif equip_time['Status'] == 2:  # 2 stop  变正常    要等待全部机台正常才能变为0
                    temptag = True
                    equip_status = cache.get('Equip_Status')
                    for item in equip_status:
                        if item['EquipOrder'].upper() == "STOP":
                            temptag = False
                    if temptag:
                        equip_time['Status'] = 0
                        equip_time['StartTime'] = t
                        Cache_writer('EquipTime', equip_time, None)
                        equipnumgroup = cache.get('EquipNumGroup')

                        delta_t = (t - equip_time['EndTime']).seconds

                        for it_stnum in equipnumgroup:
                            SQL = "SELECT stop FROM sta_total WHERE year = '" + str(year) + "' and month = '" + str(
                                month) + "' and stano = '" + it_stnum + "'"
                            data = SQL_function3(SQL)
                            delta_t_new = delta_t + int(data[0]['stop'])
                            SQL = "UPDATE sta_total set stop = '" + str(delta_t_new) + "' WHERE year = '" + str(
                                year) + "' and month = '" + str(month) + "' and stano = '" + it_stnum + "'"
                            if SQL_function4(SQL):
                                print("全线:stop--开始:修改stop时间成功")
                                log.info("全线:stop--开始:修改stop时间成功")
                            else:
                                print("全线:stop--开始:修改stop时间失败")
                                log.info("全线:stop--开始:修改stop时间失败")
                            Cache_writer('EquipTime', equip_time, None)
                            print(cache.get('EquipTime'))

                elif equip_time['Status'] == 3:  # 3 error  变正常    全线模式下的error暂时存放在equip_time_st表中,站台恢复后删除
                    # 待添加 未完成       多个设备error时候，不能直接 equip_time['Status'] = 0，导致余下外部error设备列表循环进不来 st表清理不干净
                    delta_t = 0
                    tempdata = {}
                    temptag = True
                    equip_status = cache.get('Equip_Status')
                    # 可能不止一个error
                    for item in equip_status:
                        if item['EquipOrder'].upper() == "ERROR":
                            temptag = False
                    if temptag:
                        equip_time['Status'] = 0
                        Cache_writer('EquipTime', equip_time, None)
                    # 找到就删掉
                    for item in equip_time_st:
                        if item['STNO'] == stno:
                            tempdata = item
                            delta_t = (t - item['ErrorTime']).seconds
                            break
                    equip_time_st.remove(tempdata)
                    SQL = "SELECT fatal FROM sta_total WHERE year = '" + str(year) + "' and month = '" + str(
                        month) + "' and stano = '" + stno + "'"
                    data = SQL_function3(SQL)
                    delta_t += int(data[0]['fatal'])
                    SQL = "UPDATE sta_total set fatal = '" + str(delta_t) + "' WHERE year = '" + str(
                        year) + "' and month = '" + str(month) + "' and stano = '" + stno + "'"
                    if SQL_function4(SQL):
                        print("全线:error--开始:修改fatal时间成功")
                    else:
                        print("全线:error--开始:修改fatal时间失败")
                    Cache_writer('EquipTimeST', equip_time_st, None)
                    print(cache.get('EquipTime'))
                    print(cache.get('EquipTimeST'))

        elif type == 1:  # 一个产品生产完成
            # 待添加 未完成
            # st 模式下会生产完成吗？ 应该判断tag_st? 生产完成应该记录
            # 最后一个产品生产完成时候才记录 （生产成功-starttime）这段时间 记录入normal中 ，其余只记录上线时间-上一个产品上线时间
            # equip_time['EndTime'] = t
            # equip_time['ErrorTime'] = t
            # 是切换全产线的状态 记录时间
            if tag_st is False:
                t1 = equip_time['StartTime']
                delta_t = (t - t1).seconds
                print(">>>>>delta_t")
                print(delta_t)
                SQL = "SELECT normal FROM sta_total WHERE year = '" + str(year) + "' and month = '" + str(
                    month) + "' and stano = '" + stno + "'"
                data = SQL_function3(SQL)
                delta_t += int(data[0]['normal'])
                print(delta_t)
                SQL = "UPDATE sta_total set normal = '" + str(delta_t) + "' WHERE year = '" + str(
                    year) + "' and month = '" + str(month) + "' and stano = '" + stno + "'"
                if SQL_function4(SQL):
                    print("修改normal时间成功")

                Cache_writer('EquipTime', equip_time, None)
                print(cache.get('EquipTime', default=None))
            elif tag_st is True:
                # 如果单机换型状态下真的生产成功了一个产品  未完成 待补充
                print(".....")

        elif type == 2:  # stop
            if tag_st is True:
                tag_ex = False  # exist stno存在
                for item in equip_time_st:
                    if item['STNO'] == stno:
                        tag_ex = True
                        if item['Status'] == 3:
                            print(stno + "状态为error，无法stop")
                        else:  # 0 正常生产 1 选择机台换型 2 stop 3 error
                            item['Status'] = 2
                            print(stno + "修改为stop")
                if tag_ex is False:
                    # 单机remodel就存于equip_time_st中了, 选择机台情况下不应该存在找不到的情况
                    equip_time_st.append({"StartTime": t, "ErrorTime": t, "EndTime": t, "Status": 2, "STNO": stno})
                    print(stno + "创建为stop")
                Cache_writer('EquipTimeST', equip_time_st, None)
            if tag_st is False:
                if equip_time['Status'] == 2:
                    print("全线:已经处于stop模式")
                    log.info("全线:已经处于stop模式")
                    lock3.release()
                    print("lock3.release")
                    log.info("lock3.release")
                    return
                elif equip_time['Status'] == 3:
                    tempdata = {}
                    for it in equip_time_st:
                        if it['STNO'] == stno:
                            tempdata = it
                            equip_time_st.remove(it)
                    if len(equip_time_st) == 0:
                        equip_time['Status'] = 2
                    # 记录error时间
                    delta_t = (t - tempdata['ErrorTime']).seconds
                    SQL = "SELECT fatal FROM sta_total WHERE year = '" + str(year) + "' and month = '" + str(
                        month) + "' and stano = '" + stno + "'"
                    data = SQL_function3(SQL)
                    delta_t += int(data[0]['fatal'])
                    SQL = "UPDATE sta_total set fatal = '" + str(delta_t) + "' WHERE year = '" + str(
                        year) + "' and month = '" + str(month) + "' and stano = '" + stno + "'"
                    if SQL_function4(SQL):
                        print("全线:error--stop:修改fatal时间成功")
                    else:
                        print("全线:error--stop:修改fatal时间失败")

                    Cache_writer('EquipTime', equip_time, None)
                    Cache_writer('EquipTimeST', equip_time_st, None)
                    print("全线:error--stop:" + stno)
                    log.info("全线:error--stop:" + stno)
                    print(cache.get('EquipTime', default=None))
                    lock3.release()
                    print("lock3.release")
                    log.info("lock3.release")
                    return
                elif equip_time['Status'] == 1:
                    equip_time['Status'] = 2
                    Cache_writer('EquipTime', equip_time, None)
                    print("全线:换型--stop:" + stno)
                    log.info("全线:换型--stop:" + stno)
                    print(cache.get('EquipTime', default=None))
                    lock3.release()
                    print("lock3.release")
                    log.info("lock3.release")
                    return
                # 正常 变 停机 改状态记录时间
                t0 = equip_time['EndTime']
                equip_status = cache.get('Equip_Status', default=None)
                # 全线正常换成stop 都得变成stop才能改status，不然影响下一个机台进入判断
                tem_tag = True
                for item in equip_status:
                    if item['EquipOrder'] != "STOP":
                        tem_tag = False
                if tem_tag:
                    equip_time['Status'] = 2
                    equip_time['EndTime'] = t

                Cache_writer('EquipTime', equip_time, None)

                print("全线:正常--stop:" + stno)
                log.info("全线:正常--stop:" + stno)
                print(cache.get('EquipTime', default=None))

                delta_t = (t - t0).seconds
                SQL = "SELECT normal FROM sta_total WHERE year = '" + str(year) + "' and month = '" + str(
                    month) + "' and stano = '" + stno + "'"
                data = SQL_function3(SQL)
                delta_t += int(data[0]['normal'])
                print(delta_t)
                SQL = "UPDATE sta_total set normal = '" + str(delta_t) + "' WHERE year = '" + str(
                    year) + "' and month = '" + str(month) + "' and stano = '" + stno + "'"
                if SQL_function4(SQL):
                    print("修改normal时间成功")
                    log.info("修改normal时间成功")

        elif type == 3:  # error
            if tag_st is True:
                # st模式下肯定先有换型，不可能什么都没有新建error，如光有 那得记录正常--error之间的时间记录到normal
                tag_ex = False  # exist 是否已经存在该机台的特殊状态信息
                for item in equip_time_st:
                    if item['STNO'] == stno:
                        tag_ex = True
                        # 记录开始到错误的时间，为正常生产时间 或等待时间
                        delta_t = 0
                        if item['Status'] == 0:  # 正常生产--报错  记录生产时间
                            item['Status'] = 3
                            delta_t = (t - item['StartTime']).seconds
                            print(">>>>>delta_t")
                            print(delta_t)
                            SQL = "SELECT normal FROM sta_total WHERE year = '" + str(year) + "' and month = '" + str(
                                month) + "' and stano = '" + stno + "'"
                            data = SQL_function3(SQL)
                            delta_t += int(data[0]['normal'])
                            print(delta_t)
                            SQL = "UPDATE sta_total set normal = '" + str(delta_t) + "' WHERE year = '" + str(
                                year) + "' and month = '" + str(month) + "' and stano = '" + stno + "'"
                            if SQL_function4(SQL):
                                print("st修改normal时间成功")
                        elif item['Status'] == 1 or item['Status'] == 2:  # 换型/stop--报错   记录等待时间
                            item['Status'] = 3
                            delta_t = (t - item['StartTime']).seconds
                            print(">>>>>delta_t")
                            print(delta_t)
                            SQL = "SELECT stop FROM sta_total WHERE year = '" + str(year) + "' and month = '" + str(
                                month) + "' and stano = '" + stno + "'"
                            data = SQL_function3(SQL)
                            delta_t += int(data[0]['stop'])
                            print(delta_t)
                            SQL = "UPDATE sta_total set stop = '" + str(delta_t) + "' WHERE year = '" + str(
                                year) + "' and month = '" + str(month) + "' and stano = '" + stno + "'"
                            if SQL_function4(SQL):
                                print("st修改stop时间成功")
                        if item['Status'] == 3:
                            print("st机台" + stno + "已经是error")
                            item['Status'] = 3
                        else:
                            item['ErrorTime'] = t
                            item['Status'] = 3
                            print(stno + "修改为error")
                if tag_ex is False:  # st里面没找到 所以是正常机台的error
                    # 待添加 未完成
                    # equip_time['Status'] = 3
                    # equip_time_st.append({"StartTime": t, "ErrorTime": t, "EndTime": t, "Status": 3, "STNO": stno})
                    # print("st机台" + stno + "创建为error")
                    lock3.release()
                    print("lock3.release")
                    log.info("lock3.release")
                    Time_Record(stno, 3, False)
                    lock3.release()
                    print("lock3.release")
                    log.info("lock3.release")
                    return
                Cache_writer('EquipTime', equip_time, None)
                Cache_writer('EquipTimeST', equip_time_st, None)
                print(cache.get('EquipTimeST', default=None))
            elif tag_st is False:
                # # equip_time['ErrorTime'] = t
                # equip_time['Status'] = 3
                # Cache_writer('EquipTime', equip_time, None)
                # # equip_time_st中暂时存储error的站台信息
                # equip_time_st.append({"StartTime": t, "ErrorTime": t, "EndTime": t, "Status": 3, "STNO": stno})
                # Cache_writer('EquipTimeST', equip_time_st, None)
                if equip_time['Status'] == 0:  # 如果之前是正常，现在要变报警
                    equip_time['Status'] = 3
                    equip_time['ErrorTime'] = t
                    equip_time_st.append({"StartTime": t, "ErrorTime": t, "EndTime": t, "Status": 1, "STNO": stno})
                    print('添加:' + str({"StartTime": t, "ErrorTime": t, "EndTime": t, "Status": 1, "STNO": stno}))

                    # 正常--报警  修改正常工作时间
                    delta_t = (t - equip_time['StartTime']).seconds
                    print(">>>>>delta_t")
                    print(delta_t)
                    SQL = "SELECT normal FROM sta_total WHERE year = '" + str(year) + "' and month = '" + str(
                        month) + "' and stano = '" + stno + "'"
                    data = SQL_function3(SQL)
                    delta_t += int(data[0]['normal'])
                    print(delta_t)
                    SQL = "UPDATE sta_total set normal = '" + str(delta_t) + "' WHERE year = '" + str(
                        year) + "' and month = '" + str(month) + "' and stano = '" + stno + "'"
                    if SQL_function4(SQL):
                        print("全线修改normal时间成功")


                elif equip_time['Status'] == 1 or equip_time['Status'] == 2:  # 如果之前是换型 or stop，现在要变报警
                    equip_time['Status'] = 3
                    equip_time['ErrorTime'] = t
                    equip_time_st.append({"StartTime": t, "ErrorTime": t, "EndTime": t, "Status": 1, "STNO": stno})
                    print('添加:' + str({"StartTime": t, "ErrorTime": t, "EndTime": t, "Status": 1, "STNO": stno}))

                    # remodel/stop--报警  修改stop工作时间
                    delta_t = (t - equip_time['EndTime']).seconds
                    print(">>>>>delta_t")
                    print(delta_t)
                    SQL = "SELECT stop FROM sta_total WHERE year = '" + str(year) + "' and month = '" + str(
                        month) + "' and stano = '" + stno + "'"
                    data = SQL_function3(SQL)
                    delta_t += int(data[0]['stop'])
                    print(delta_t)
                    SQL = "UPDATE sta_total set stop = '" + str(delta_t) + "' WHERE year = '" + str(
                        year) + "' and month = '" + str(month) + "' and stano = '" + stno + "'"
                    if SQL_function4(SQL):
                        print("全线修改stop时间成功")

                elif equip_time['Status'] == 3:  # 如果之前是error
                    record_tag = False
                    for it in equip_time_st:
                        if it['STNO'] == stno:
                            record_tag = True
                    if record_tag is False:
                        equip_time_st.append({"StartTime": t, "ErrorTime": t, "EndTime": t, "Status": 1, "STNO": stno})
                        print('添加:' + str({"StartTime": t, "ErrorTime": t, "EndTime": t, "Status": 1, "STNO": stno}))
                        Cache_writer('EquipTimeST', equip_time_st, None)

                Cache_writer('EquipTime', equip_time, None)
                Cache_writer('EquipTimeST', equip_time_st, None)
        elif type == 4:  # remodel  线体换型/单击换型
            if tag_st is False:

                equip_time = cache.get('EquipTime', default=None)
                equip_time_st = cache.get('EquipTimeST', default=None)
                equipnumgroup = cache.get('EquipNumGroup')
                if equip_time['Status'] == 0:
                    t = datetime.datetime.now()
                    equip_time['EndTime'] = t  # 换型到start之间时间为t-endtime，作为等待时间
                    # 待全部机位记录完成后  修改Status位
                    tag_num = 0
                    st_len = len(equipnumgroup) - 1
                    if stno == equipnumgroup[st_len]:
                        equip_time['Status'] = 1

                    print("全线:正常--换型,成功")
                    log.info("全线:正常--换型,成功")

                    delta_t = (t - equip_time['StartTime']).seconds
                    SQL = "SELECT normal FROM sta_total WHERE year = '" + str(year) + "' and month = '" + str(
                        month) + "' and stano = '" + stno + "'"
                    data = SQL_function3(SQL)
                    delta_t += int(data[0]['normal'])
                    print(delta_t)
                    SQL = "UPDATE sta_total set normal = '" + str(delta_t) + "' WHERE year = '" + str(
                        year) + "' and month = '" + str(month) + "' and stano = '" + stno + "'"
                    if SQL_function4(SQL):
                        print("全线修改normal时间成功")
                        log.info("全线修改normal时间成功")

                    # 清空之前选择机台换型导致的st中的内容
                    equip_time_st = []

                    Cache_writer('EquipTime', equip_time, None)
                    Cache_writer('EquipTimeST', equip_time_st, None)

                elif equip_time['Status'] == 1:  # 1换型 2 stop 和 3 error下由前端做卡控不让换型
                    print("全线:已经是换型状态，不记录新时间")
                    log.info("全线:已经是换型状态，不记录新时间")
                    lock3.release()
                    print("lock3.release")
                    log.info("lock3.release")
                    return
                elif equip_time['Status'] == 2:
                    print("全线:stop状态下不能换型,应该先切换到开始状态")
                    log.info("全线:stop状态下不能换型,应该先切换到开始状态")
                    lock3.release()
                    print("lock3.release")
                    log.info("lock3.release")
                    return
                elif equip_time['Status'] == 3:
                    print("全线:error状态下不能换型")
                    log.info("全线:error状态下不能换型")
                    lock3.release()
                    print("lock3.release")
                    log.info("lock3.release")
                    return

            elif tag_st is True:
                # Time_Record函数外应该保证设备都是可换型的状态
                # 建立在这些设备已经换型成功的基础之上的记录
                # equip_time_st = cache.get('EquipTimeST', default=None)
                delta_t = 0
                tag_ex = False
                equip_time_st_temp = equip_time_st
                for item in equip_time_st_temp:
                    if item['STNO'] == stno:
                        tag_ex = True
                        delta_t = (t - item['StartTime']).seconds
                        if item['Status'] != 1:
                            print("异常:" + str(stno) + "该设备状态不为换型，不删除，请检查")
                        # elif item['Status'] == 1:
                        #     print("删除 equip_time_st 中存在的" + item['STNO'])
                        #     equip_time_st.remove(item)

                if tag_ex is False:
                    delta_t = (t - equip_time['StartTime']).seconds
                    SQL = "SELECT normal FROM sta_total WHERE year = '" + str(year) + "' and month = '" + str(
                        month) + "' and stano = '" + stno + "'"
                    data = SQL_function3(SQL)
                    delta_t += int(data[0]['normal'])
                    print(delta_t)
                    SQL = "UPDATE sta_total set normal = '" + str(delta_t) + "' WHERE year = '" + str(
                        year) + "' and month = '" + str(month) + "' and stano = '" + stno + "'"
                    if SQL_function4(SQL):
                        print("st修改normal时间成功")

                    # 单站换的全都会存入st中
                    # t = datetime.datetime.now()
                    equip_time_st.append({"StartTime": t, "ErrorTime": t, "EndTime": t, "Status": 1, "STNO": stno})
                    print('添加:' + str({"StartTime": t, "ErrorTime": t, "EndTime": t, "Status": 1, "STNO": stno}))
                    Cache_writer('EquipTimeST', equip_time_st, None)
                else:
                    SQL = "SELECT stop FROM sta_total WHERE year = '" + str(year) + "' and month = '" + str(
                        month) + "' and stano = '" + stno + "'"
                    data = SQL_function3(SQL)
                    delta_t += int(data[0]['stop'])
                    print(delta_t)
                    SQL = "UPDATE sta_total set stop = '" + str(delta_t) + "' WHERE year = '" + str(
                        year) + "' and month = '" + str(month) + "' and stano = '" + stno + "'"
                    if SQL_function4(SQL):
                        print("st修改stop时间成功")

                # #单站换的全都会存入st中
                # # t = datetime.datetime.now()
                # equip_time_st.append({"StartTime": t, "ErrorTime": t, "EndTime": t, "Status": 1, "STNO": stno})
                # print('添加:' + str({"StartTime": t, "ErrorTime": t, "EndTime": t, "Status": 1, "STNO": stno}))
                # Cache_writer('EquipTimeST', equip_time_st, None)

            # equip_time['ErrorTime'] = t
            # equip_time['Status'] = 3
            Cache_writer('EquipTime', equip_time, None)
            # print(cache.get('EquipTime', default=None))
        lock3.release()
        print("lock3.release")
        log.info("lock3.release")
    except Exception as err:
        print("--------------------------Time_record ERROR--------------------------------")
        print(err)
        log.info(err)
        log.info("--------------------------Time_record ERROR--------------------------------")
        lock3.release()
        log.info("lock3.release")

        log.info(stno)
        log.info(type)
        log.info(tag_st)


# 时间戳转正常时间
def timestamp_to_timestr(timestamp):
    log.info(">>>>>>>>>>>timestamp_to_timestr")
    if timestamp == "":
        raise Exception("timestamp is empty")
    timestamp = int(timestamp)

    # 转换成localtime
    time_local = time.localtime(timestamp / 1000)
    # time_local = time.localtime(timestamp)
    print(time_local)
    # 转换成新的时间格式(精确到秒)
    dt = time.strftime("%Y-%m-%d %H:%M:%S", time_local)
    print(dt)
    return dt
# 主线体之外的特殊机台处理函数
def TRecv_SP(client_Ip, data, topic):
    try:
        log.info("---------TRecv_SP---------")
        data = str(data)
        data = eval(data)
        try:
            command = data['Command']
        except Exception as err:
            print("解析data，command格式时出现错误，直接退出解析")
            print(err)
            return
        print(command)
        if command == "0x02":   # SP
            equip_topic = "Msg2Station/" + data['Check']['Station_No']
            try:
                print('0x02')
                type = "0"

                sn = data['Check']['Serial_No']

                # 线体临时优化
                sn = sn.replace(' ', '')
                  # 检查条码是否为空
                if not sn or sn.strip() == "":
                    msg = "传入条码不能为空"
                    log.error(msg)
                    raise Exception(msg)
                stno = data['Check']['Station_No']
                type = str(data['Check']['Type'])
                gp_model = data['Check']['Gp_Model']
                equipnumgroup = cache.get('EquipNumGroup')
                current_model_sp = cache.get('current_model_sp')
                current_order_stand = cache.get('current_order_stand')
                if not current_model_sp.upper() == gp_model.upper():
                    msg = "工位的型号和实际生产的型号不一致"
                    raise Exception(msg)

                order_sn_tag = False
                num_real = 0  # 实际生产的数量
                t = datetime.datetime.now()
                result = "NG"
                msg = ""

                # 只有订单开启时才能进入checksn的验证环节      该订单状态    Close 已经关闭   Start 正在生产
                SQL = "SELECT * FROM planorder_stand_tab WHERE order_no = '" + current_order_stand + "'"
                data = SQL_function3(SQL)
                if len(data) == 0:
                    msg = "未找到当前工单信息:" + current_order_stand + " 请检查"
                    raise Exception(msg)
                elif len(data) > 1:
                    msg = "找到多个工单信息:" + current_order_stand + " 请检查"
                    raise Exception(msg)

                if data[0]['status'].upper() == "":  # 如果订单状态为空，说明目前是第一个上料
                    SQL = "UPDATE planorder_stand_tab set status = 'Start',datetime = '" + str(t) + "' WHERE order_no = '" + current_order_stand + "'"
                    if not SQL_function4(SQL):
                        raise Exception("工单" + current_order_stand + "开始修改成功")
                    # msg = "工单" + current_order + "未开始，请检查"
                    # print(msg)
                    # raise Exception(msg)
                if data[0]['status'].upper() == "START":
                    print("工单" + current_order_stand + "开始确认成功")
                if data[0]['status'].upper() == "CLOSE":
                    msg = "工单" + current_order_stand + "已经关闭"
                    print(msg)
                    raise Exception(msg)

                sn_turn = 1
                # 确定当前上传的条码类型 和 名称
                # 0前壳qrcode1     1  pcba1        2后壳qrcode2    3 pcba2   4 料盘码
                code_name = ""
                if type == "0":
                    code_name = "qr_code1"
                elif type == "1":
                    code_name = "pcba_code1"
                elif type == "2":
                    code_name = "qr_code2"
                elif type == "3":
                    code_name = "pcba_code2"
                elif type == "5":
                    code_name = "lens"

                # SP站点 确保线体中存在该产品信息 生产结果为OK
                if not sn or sn.strip() == "":
                    msg = "传入条码不能为空"
                    log.error(msg)
                    raise Exception(msg)
                SQL = "SELECT * FROM ordersn_tab WHERE " + code_name + " = '" + sn + "'"
                line_data = SQL_function3(SQL)
                if len(line_data) == 0:
                    msg = "线体中未查询到" + code_name + ": " + sn + "的生产信息"
                    raise Exception(msg)
                # 线体状态查询
                log.info(code_name + ":" + sn + " Result:" + line_data[0]['result'])
                if line_data[0]['result'] == "" or line_data[0]['result'].upper() == "NG" or line_data[0]['result'].upper() == "NA":
                    msg = "本体线体生产不完整,该主码NG/NA"
                    raise Exception(msg)

                # [新增] SP机台重投次数限制,最多3次(retest_num>3拒绝进站)
                # try:
                #     retest_num_sp = int(line_data[0]['retest_num']) if line_data[0]['retest_num'] is not None else 0
                # except Exception:
                #     retest_num_sp = 0
                # if retest_num_sp > 3:
                #     msg = "SP机台NG复测3次,过站失败,retest_num=" + str(retest_num_sp)
                #     log.error(msg)
                #     raise Exception(msg)

                # [新增] 扫镜头进站时，校验绑定的PCBA料号与当前下料配置的料号是否一致
                if type == "5":  # 镜头进站
                    # 获取当前支架型号配置的PCBA料号
                    SQL = "SELECT P_PART_NO FROM planorder_partno_tab WHERE gp_model = '" + gp_model + "'"
                    config_partno_data = SQL_function3(SQL)
                    if len(config_partno_data) == 0:
                        msg = "未找到当前支架型号" + gp_model + "对应的PCBA料号配置"
                        raise Exception(msg)
                    config_pcba_partno = config_partno_data[0]['P_PART_NO']

                    # 校验绑定的pcba_code1料号：通过PCBA→机型→P_PART_NO链路校验
                    if line_data[0]['pcba_code1'] and line_data[0]['pcba_code1'].strip() != "":
                        SQL = "SELECT gp_model FROM qr_confrimation_tab WHERE pcba_code1 = '" + line_data[0]['pcba_code1'] + "' LIMIT 1"
                        pcba1_data = SQL_function3(SQL)
                        if len(pcba1_data) > 0 and pcba1_data[0]['gp_model'] != "":
                            pcba1_gp_model = pcba1_data[0]['gp_model']
                            SQL = "SELECT P_PART_NO FROM planorder_partno_tab WHERE gp_model = '" + pcba1_gp_model + "'"
                            pcba1_partno_data = SQL_function3(SQL)
                            if len(pcba1_partno_data) > 0 and pcba1_partno_data[0]['P_PART_NO'] != "":
                                if pcba1_partno_data[0]['P_PART_NO'] != config_pcba_partno:
                                    msg = "绑定的PCBA1所属机型(" + pcba1_gp_model + ")的料号(" + pcba1_partno_data[0]['P_PART_NO'] + ")与当前配置料号(" + config_pcba_partno + ")不匹配"
                                    raise Exception(msg)

                    # 校验绑定的pcba_code2料号：通过PCBA→机型→P_PART_NO链路校验
                    if line_data[0]['pcba_code2'] and line_data[0]['pcba_code2'].strip() != "":
                        SQL = "SELECT gp_model FROM qr_confrimation_tab WHERE pcba_code2 = '" + line_data[0]['pcba_code2'] + "' LIMIT 1"
                        pcba2_data = SQL_function3(SQL)
                        if len(pcba2_data) > 0 and pcba2_data[0]['gp_model'] != "":
                            pcba2_gp_model = pcba2_data[0]['gp_model']
                            SQL = "SELECT P_PART_NO FROM planorder_partno_tab WHERE gp_model = '" + pcba2_gp_model + "'"
                            pcba2_partno_data = SQL_function3(SQL)
                            if len(pcba2_partno_data) > 0 and pcba2_partno_data[0]['P_PART_NO'] != "":
                                if pcba2_partno_data[0]['P_PART_NO'] != config_pcba_partno:
                                    msg = "绑定的PCBA2所属机型(" + pcba2_gp_model + ")的料号(" + pcba2_partno_data[0]['P_PART_NO'] + ")与当前配置料号(" + config_pcba_partno + ")不匹配"
                                    raise Exception(msg)


                # 校验线体主码的实际型号与支架锁付生产型号。
                # 借用项目按第二个下划线前的前缀兼容，例如：
                # C06_8M_30 与 C06_8M_P01_4_8M 均按 C06_8M 校验。
                SQL = "SELECT gp_model FROM qr_confrimation_tab WHERE " + code_name + " = '" + sn + "'"
                qr_confdata = SQL_function3(SQL)
                if len(qr_confdata) == 0:
                    msg = "未找到主码对应的本体型号"
                    raise Exception(msg)

                body_model = str(qr_confdata[0]['gp_model'] or "").strip().upper()
                stand_model = str(gp_model or "").strip().upper()
                if body_model == "" or stand_model == "":
                    msg = "主码型号或生产型号为空"
                    raise Exception(msg)

                if body_model != stand_model:
                    body_parts = body_model.split("_")
                    stand_parts = stand_model.split("_")
                    body_prefix = "_".join(body_parts[:2]) if len(body_parts) >= 2 else ""
                    stand_prefix = "_".join(stand_parts[:2]) if len(stand_parts) >= 2 else ""
                    if body_prefix == "" or body_prefix != stand_prefix:
                        msg = "主码型号(" + body_model + ")与生产型号(" + stand_model + ")不匹配"
                        raise Exception(msg)
                    log.info("借用项目型号前缀匹配: " + body_prefix)

                # 查重
                SQL = "SELECT * FROM qr_confrimation_tab_sp " \
                      " WHERE " + code_name + " = '" + sn + "' and station_no = '" + stno + "'"
                data = SQL_function(SQL)
                if len(data) > 0:
                    SQL = "UPDATE qr_confrimation_tab_sp set check_time = '" + str(
                        t) + "' WHERE " + code_name + " = '" + sn + "' and station_no = '" + stno + "'"
                    if SQL_function4(SQL) is False:
                        msg = "更新数据失败"
                        raise Exception(msg)
                else:
                    SQL = "INSERT INTO qr_confrimation_tab_sp (" + code_name + ",station_no,check_result,test_result,gp_model,check_time) Value ('" + sn + "','" + stno + "','OK','NA','" + gp_model + "','" + str(
                        t) + "')"
                    if SQL_function4(SQL) is False:
                        msg = "插入数据失败"
                        raise Exception(msg)
                    # 同步更新该码对应的绑定信息
                    bindcolumn_name = GetBindcolumn_name()
                    for it in bindcolumn_name:
                        if it == code_name or line_data[0][it] == "":
                            continue
                        else:
                            SQL = "UPDATE qr_confrimation_tab_sp SET " + it + " = '" + line_data[0][
                                it] + "' WHERE " + code_name + " = '" + sn + "'"
                            if not SQL_function4(SQL):
                                msg = "更新数据失败"
                                raise Exception(msg)
                    # 镜头工单先镭雕后check：num_real在check时自增。 支架工单先check后镭雕支架：num_real 并不在check时进行自增，在镭雕申请成功之后就自增

                result = "OK"
                data_send = {
                    "Command": "0x02",
                    "Check_Result":
                        {
                            "Serial_No": sn,
                            "Result": result,
                            "Message": msg
                        }
                }
                log.info(str(data_send))
                SendMessage2Station(equip_topic, data_send)
                return data_send
            except Exception as err:
                result = "NG"
                print(str(err))
                log.info(str(err))
                data_send = {
                    "Command": "0x02",
                    "Check_Result":
                        {
                            "Result": result,
                            "Serial_No": sn,
                            "Message": str(err)
                        }
                }
                print(data_send)
                log.info(data_send)
                SendMessage2Station(equip_topic, data_send)
                return data_send
        elif command == "0x03": #SP
            equip_topic = "Msg2Station/" + data['Bind']['Station_No']
            temp_num = 0
            try:
                print("0x03")
                current_model = cache.get('current_model')
                current_order = cache.get('current_order')
                current_order_stand = cache.get('current_order_stand')

                Pcba1 = data['Bind']['Pcba1']
                Pcba2 = data['Bind']['Pcba2']
                Lens = data['Bind']['Lens']
                Stand = data['Bind']['Stand']
                Qr_code1 = data['Bind']['Qr_code1']
                Qr_code2 = data['Bind']['Qr_code2']

                # 线体临时优化
                Qr_code2 = Qr_code2.replace(' ', '')

                Station_No = data['Bind']['Station_No']
                Gp_Model = data['Bind']['Gp_Model']

                result = 'NG'
                msg = ''
                bind_code = ""
                bind_name = ""
                # 汇总绑定信息
                code_list = []
                code_list.append(Qr_code1)
                code_list.append(Pcba1)
                code_list.append(Qr_code2)
                code_list.append(Pcba2)
                code_list.append(Lens)
                code_list.append(Stand)
                print(code_list)
                print(code_list)
                name_list = ['qr_code1', 'pcba_code1', 'qr_code2', 'pcba_code2', 'lens', 'stand_code']
                print(name_list)

                # 确保绑定信息足够
                temp_num = 0
                # 对一主码 多个绑定码 情况做区分
                multi_bind_tag = False

                for item in code_list:
                    if not item == "":
                        temp_num += 1
                if temp_num < 2:
                    if temp_num == 0:
                        msg = "缺少绑定信息"
                        raise Exception(msg)
                    elif temp_num == 1:
                        check_code = ""
                        check_name = ""
                        for i in range(0, len(code_list)):
                            print(code_list[i])
                            print(name_list[i])
                            if not code_list[i] == "" or code_list[i] == None:
                                check_code = code_list[i]
                                check_name = name_list[i]
                                break
                        # 验证绑定码可用性
                        SQL = "SELECT * FROM qr_confrimation_tab_sp WHERE " + check_name + " = '" + check_code + "'"
                        data = SQL_function3(SQL)
                        if not len(data) == 0:
                            msg = "qr_confrimation_tab_sp中已经存在 " + check_name + ":" + check_code + " 绑定,请检查"
                            raise Exception(msg)
                        else:
                            result = "OK"
                            raise Exception("无重复")
                elif temp_num > 2:
                    # 原代码：multi_bind_tag = True; raise Exception("三码绑定情况，暂时未实现")
                    # 修改时间：2026-03-02
                    # 修改逻辑：移除三码绑定异常，支持多码绑定（双目、三目等）
                    multi_bind_tag = True
                    log.info("多码绑定情况，支持多码绑定")

                # 找到主码
                main_code = ""
                main_name = ""
                count_num = 0
                for i in range(0, len(code_list)):
                    count_num += 1
                    if not code_list[i] == "":
                        main_code = code_list[i]
                        main_name = name_list[i]
                        break
                # 验证主码可用性
                if not main_code or main_code.strip() == "":
                    msg = "传入条码不能为空"
                    log.error(msg)
                    raise Exception(msg)
                SQL = "SELECT * FROM qr_confrimation_tab_sp WHERE " + main_name + " = '" + main_code + "'"
                data = SQL_function3(SQL)
                if len(data) == 0:
                    msg = "qr_confrimation_tab_sp不存在" + main_name + ":" + main_code + " 对应的绑定信息"
                    raise Exception(msg)
                elif len(data) > 1:
                    msg = "qr_confrimation_tab_sp找到多个" + main_name + ":" + main_code + " 对应的绑定信息"
                    raise Exception(msg)

                # 绑定中二次确认 SP站点 确保线体中存在该产品信息 生产结果为OK
                if not main_code or main_code.strip() == "":
                    msg = "传入条码不能为空"
                    log.error(msg)
                    raise Exception(msg)
                SQL = "SELECT * FROM ordersn_tab WHERE " + main_name + " = '" + main_code + "'"
                line_data = SQL_function3(SQL)
                if len(line_data) == 0:
                    msg = "线体中未查询到" + main_name + ": " + main_code + "的生产信息"
                    raise Exception(msg)
                # 线体状态查询
                log.info(main_name + ":" + main_code + " Result:" + line_data[0]['result'])
                if line_data[0]['result'] == "" or line_data[0]['result'].upper() == "NG" or line_data[0]['result'].upper() == "NA":
                    msg = "本体线体生产不完整,该主码NG/NA"
                    raise Exception(msg)



                # 原代码：只处理单个绑定码（第一个非空码）
                # 修改时间：2026-03-02
                # 修改逻辑：收集所有绑定码并循环处理，支持多码绑定
                # 找到所有绑定码
                bind_codes = []
                bind_names = []
                for i in range(count_num, len(code_list)):
                    if not code_list[i] == "":
                        bind_codes.append(code_list[i])
                        bind_names.append(name_list[i])

                # 获取物料号配置和工单信息（提前获取，减少重复查询）
                part_no_dict = {"pcba_code1": "P_PART_NO", "pcba_code2": "P_PART_NO", "lens": "J_PART_NO", "stand_code": "ZC_PART_NO"}
                if not main_code or main_code.strip() == "":
                    msg = "传入条码不能为空"
                    log.error(msg)
                    raise Exception(msg)
                SQL = "SELECT * FROM qr_confrimation_tab WHERE " + main_name + " = '" + main_code + "'"
                data = SQL_function3(SQL)
                main_code_model = data[0]['gp_model']
                SQL = "SELECT * FROM planorder_partno_tab WHERE gp_model = '" + main_code_model + "'"
                partno_data = SQL_function3(SQL)
                SQL = "SELECT * FROM planorder_stand_tab WHERE order_no = '" + current_order_stand + "'"
                order_data = SQL_function3(SQL)

                # 循环处理每个绑定码
                for idx in range(len(bind_codes)):
                    bind_code = bind_codes[idx]
                    bind_name = bind_names[idx]

                    # 验证绑定码物料号
                    partno_code = ""
                    if bind_name in part_no_dict:
                        partno_code = partno_data[0].get(part_no_dict[bind_name], "")
                        if partno_code == "":
                            SQL = "SELECT * FROM planorder_partno_tab WHERE gp_model = '" + Gp_Model + "'"
                            partno_data_new = SQL_function3(SQL)
                            partno_code = partno_data_new[0].get(part_no_dict[bind_name], "")
                            if partno_code == "":
                                msg = Gp_Model + " 对应绑定物料号为空"
                                raise Exception(msg)

                    if partno_code and bind_code.find(partno_code) == -1:
                        raise Exception("绑定码" + bind_name + "与主码物料型号不一致")

                    # 验证工单物料号

                    #先不校验绑定码物料号是否符合工单
                    # if order_data and bind_code.find(order_data[0]['part_no']) == -1:
                    #     msg = "绑定码" + bind_name + "物料号不符合工单" + current_order_stand + " 请检查"
                    #     raise Exception(msg)

                    # 检查是否已绑定
                    SQL = "SELECT * FROM qr_confrimation_tab_sp WHERE " + bind_name + " = '" + bind_code + "'"
                    data = SQL_function3(SQL)
                    if not len(data) == 0:
                        if not multi_bind_tag:
                            msg = "qr_confrimation_tab_sp中已经存在 " + bind_name + ":" + bind_code + " 绑定,请检查"
                            raise Exception(msg)
                    else:
                        # 更新绑定信息到qr_confrimation_tab
                        SQL = "UPDATE qr_confrimation_tab SET " + bind_name + " = '" + bind_code + "' WHERE " + main_name + " = '" + main_code + "'"
                        if SQL_function4(SQL):
                            msg = "qr_confrimation_tab " + bind_name + " 绑定更新成功"
                        else:
                            msg = "qr_confrimation_tab " + bind_name + " 绑定更新失败"
                            result = "NG"

                # 同步所有绑定信息到qr_confrimation_tab_sp
                SQL = "SELECT * from qr_confrimation_tab WHERE " + main_name + " = '" + main_code + "'"
                qr_data = SQL_function3(SQL)
                SQL = "UPDATE qr_confrimation_tab_sp SET qr_confrimation_tab_sp.pcba_code1 = '" + qr_data[0]['pcba_code1'] + "'," \
                      "qr_confrimation_tab_sp.pcba_code2 = '" + qr_data[0]['pcba_code2'] + "'," \
                      "qr_confrimation_tab_sp.qr_code1 = '" + qr_data[0]['qr_code1'] + "'," \
                      "qr_confrimation_tab_sp.qr_code2 = '" + qr_data[0]['qr_code2'] + "'," \
                      "qr_confrimation_tab_sp.lens = '" + qr_data[0]['lens'] + "'," \
                      "qr_confrimation_tab_sp.stand_code = '" + qr_data[0]['stand_code'] + "'" \
                      "WHERE " + main_name + " = '" + main_code + "'"
                if SQL_function4(SQL):
                    msg = "qr_confrimation_tab_sp 绑定更新成功"
                else:
                    msg = "qr_confrimation_tab_sp 绑定更新失败"
                    result = "NG"
                result = "OK"
                # ------------ 更新qr_bind_tab 中的绑定内容--------------
                SQL = "SELECT * FROM qr_bind_tab WHERE " + main_name + " = '" + main_code + "'"
                data = SQL_function3(SQL)
                if len(data) > 1:
                    msg = "qr_bind_tab找到多个信息，请检查"
                elif len(data) == 1:
                    SQL = "UPDATE qr_bind_tab SET " + bind_name + " = '" + bind_code + "' WHERE " + main_name + " = '" + main_code + "'"
                    if SQL_function4(SQL):
                        msg = "主码" + main_name + ":" + main_code + "和:" + bind_name + ":" + bind_code + " 更新绑定成功"
                        result = "OK"
                    else:
                        msg = "qr_bind_tab更新绑定数据失败"
                elif len(data) == 0:
                    msg = "qr_bind_tab中未找到绑定信息，请检查"
                    print(msg)
                    if not main_code or main_code.strip() == "":
                        msg = "传入条码不能为空"
                        log.error(msg)
                        raise Exception(msg)
                    SQL = "SELECT * FROM qr_confrimation_tab WHERE " + main_name + " = '" + main_code + "'"
                    data = SQL_function3(SQL)
                    if len(data) == 0:
                        msg = "qr_bind_tab & qr_confrimation_tab中未找到绑定信息，请检查"
                        raise Exception(msg)
                    else:
                        SQL = "INSERT INTO qr_bind_tab (" + main_name + ") Values ('" + main_code + "')"
                        if not SQL_function4(SQL):
                            msg = "qr_bind_tab插入主码数据失败"
                            result = "NG"
                        SQL = "UPDATE qr_bind_tab SET " + bind_name + " = '" + bind_code + "' WHERE " + main_name + " = '" + main_code + "'"
                        if SQL_function4(SQL):
                            msg = "主码" + main_name + ":" + main_code + "和:" + bind_name + ":" + bind_code + " 更新绑定成功"
                            result = "OK"
                        else:
                            msg = "qr_bind_tab更新绑定数据失败"
                            result = "NG"
                # ------------ 更新ordersn_tab 中的绑定内容--------------
                if not main_code or main_code.strip() == "":
                    msg = "传入条码不能为空"
                    log.error(msg)
                    raise Exception(msg)
                SQL = "SELECT * FROM ordersn_tab WHERE " + main_name + " = '" + main_code + "'"
                data = SQL_function3(SQL)
                if len(data) > 1:
                    msg = "ordersn_tab找到多个信息，请检查"
                elif len(data) == 0:
                    msg = "ordersn_tab未找到主码信息，请检查"
                elif len(data) == 1:
                    SQL = "UPDATE ordersn_tab SET " + bind_name + " = '" + bind_code + "',stand_order_no = '" + current_order_stand + "' WHERE " + main_name + " = '" + main_code + "'"
                    if SQL_function4(SQL):
                        msg = "主码" + main_name + ":" + main_code + "和:" + bind_name + ":" + bind_code + " 更新绑定成功"
                        result = "OK"
                    else:
                        msg = "ordersn_tab更新绑定数据失败"
                        raise Exception(msg)

                data_send = {
                    "Command": "0x03",
                    "Bind_Result":
                        {
                            "Result": result,
                            "Message": msg
                        }
                }
                log.info(data_send)
                SendMessage2Station(equip_topic, data_send)
                return data_send

            except Exception as err:
                type = -1
                if not (temp_num == 0) or (temp_num == 3):
                    if temp_num == 1:
                        bind_name = check_name
                    if bind_name == 'qr_code1' or bind_name == 'qr_code2':
                        type = 0
                    elif bind_name == 'pcba_code1' or bind_name == 'pcba_code2':
                        type = 1
                    elif bind_name == 'lens':
                        type = 2
                    elif bind_name == 'stand_code':
                        type = 3

                print(err)
                data_send = {
                    "Command": "0x03",
                    "Bind_Result":
                        {
                            "Result": result,
                            "Type": str(type),
                            "Message": str(err)
                        }
                }
                print(data_send)
                log.info(data_send)
                SendMessage2Station(equip_topic, data_send)
                return data_send
        elif command == '0x04':  # SP数据上传指令 dateup
            code_name = ""
            Serial_No = ""
            Station_No = ""
            Gp_Model = ""
            Type = ""
            try:
                log.info("0x04")

                current_order_stand = cache.get('current_order_stand')

                Serial_No = data['DataUp']['Serial_No']

                # 线体临时优化
                Serial_No = Serial_No.replace(' ', '')

                Station_No = data['DataUp']['Station_No']

                Type = str(data['DataUp']['Type'])
                Test_Result = data['DataUp']['Test_Result']  # 总结果
                Gp_Model = data['DataUp']['Gp_Model']
                Judge_Code = data['DataUp']['Judge_Code']

                Start_Time = data['DataUp']['Start_Time']
                End_Time = data['DataUp']['End_Time']

                Test_Value = data['DataUp']['Test_Value']  # {"Test_Item":"","Value":"","Result":""}
                msg = ""
                result = "NG"
                equip_topic = "Msg2Station/" + Station_No
                t = datetime.datetime.now()
                print(t)
                line_no = Getline_no()
                # 转换时间戳
                if not Start_Time == "" and not Start_Time == "":
                    Start_Time = timestamp_to_timestr(Start_Time)
                    End_Time = timestamp_to_timestr(End_Time)
                # 确定当前上传的条码类型 和 名称
                # 0前壳qrcode1     1  pcba1     2后壳qrcode2    3 pcba2
                code_name = ""
                if Type == "0":
                    code_name = "qr_code1"
                elif Type == "1":
                    code_name = "pcba_code1"
                elif Type == "2":
                    code_name = "qr_code2"
                elif Type == "3":
                    code_name = "pcba_code2"
                elif Type == "5":
                    code_name = "lens"
                if code_name == "":
                    msg = "code_name未匹配 Type=" + str(Type)
                    raise Exception(msg)

                # ------------------------------------- 查询当前sn的cheksn 和result 状态 ---------------------------------------------
                SQL = "SELECT check_result, test_result FROM qr_confrimation_tab_sp WHERE " + code_name + " = '" + Serial_No + "' and station_no = '" + Station_No + "'"
                data = SQL_function3(SQL)
                if len(data) > 1:
                    msg = "存在两条重复数据，请排查"
                    raise Exception(msg)
                elif len(data) == 0:
                    msg = "未查询到本站数据"
                    raise Exception(msg)
                elif len(data) == 1:
                    if data[0]['check_result'] == "NG":
                        msg = "本站的前功程确认已经失败，不能过站"
                        raise Exception(msg)
                    elif data[0]['check_result'] == "NA":
                        msg = "工程确认未记录，不能过站"
                        raise Exception(msg)
                    elif data[0]['check_result'] == "OK":
                        msg = "OK"
                    else:
                        msg = "不能识别Check状态"
                        raise Exception(msg)
                    if data[0]['test_result'] != "NA":
                        msg = "该站已存在测试记录,继续追加记录"
                        # raise Exception(msg)
                    else:
                        msg = "OK"
                    SQL = "SELECT * FROM ordersn_tab WHERE " + code_name + " = '" + Serial_No + "'"
                    check_Data = SQL_function3(SQL)
                    if check_Data[0]['stand_code'] == "":
                        msg = "支架码未绑定 stand_code not exists"
                        raise Exception(msg)
                # Update_Product_Status
                UpdateResult = ""
                if Test_Result.upper() == "OK":
                    UpdateResult = "OK"
                else:
                    UpdateResult = "NG"
                # 更新 test_result 测试项数据
                # SQL = "UPDATE qr_confrimation_tab_sp set test_result = '" + UpdateResult + "', test_time = '" + str(
                #     t) + "' WHERE " + code_name + " = '" + Serial_No + "' and station_no = '" + Station_No + "' and check_result = 'OK' and gp_model = '" + Gp_Model + "'"
                SQL = "UPDATE qr_confrimation_tab_sp set test_result = '" + UpdateResult + "', test_time = '" + str(t) + "' WHERE " + code_name + " = '" + Serial_No + "' and station_no = '" + Station_No + "' and check_result = 'OK'"
                data = SQL_function4(SQL)
                if data:
                    msg = "测试记录更新成功"
                else:
                    msg = "产品信息更新失败"
                    raise Exception(msg)
                print(msg)

                # Insert_TestValue
                Insert_Tag = False
                Errcode = ""
                if Test_Result.upper() != "OK":
                    if len(Judge_Code) != 0:
                        for i in range(0, len(Judge_Code)):
                            Errcode += str(Judge_Code[i])
                            if i < len(Judge_Code) - 1:
                                Errcode += "-"
                    else:
                        msg = "TestResut is NG,But Not UpLoad judgecode"
                        print(msg)
                        # raise Exception(msg)

                SQL = "SELECT column_name FROM information_schema.COLUMNS WHERE table_name = '" + Station_No + "_test_tab'"
                data_columns = SQL_function3(SQL)
                SQL = "SELECT * FROM ordersn_tab WHERE " + code_name + " = '" + Serial_No + "'"
                code_data = SQL_function3(SQL)
                SQL = "INSERT INTO " + Station_No + "_test_tab " + "(qr_code1, qr_code2, pcba_code1, pcba_code2 ,lens ,station_no,test_result,gp_model,judge_code,start_time,end_time) values ('" + code_data[0]['qr_code1'] + "','" + code_data[0]['qr_code2'] + "','" + code_data[0]['pcba_code1'] + "','" + code_data[0]['pcba_code2']  + "','" + code_data[0]['lens'] + "','" + Station_No + "','" + Test_Result + "','" + Gp_Model + "','" + Errcode + "','" + Start_Time + "','" + End_Time + "')"
                AlterRet = True
                if len(Test_Value) != 0:
                    for it in Test_Value:
                        if Select_Column_from_Tab(data_columns, it['Test_Item']):
                            if Alter_Column(Station_No + "_test_tab ", it['Test_Item']) is False:
                                AlterRet = False
                if AlterRet:
                    Insert_Tag = SQL_function4(SQL)
                    if Insert_Tag:
                        print("Insert success")
                    else:
                        print("Insert fail")
                else:
                    Insert_Tag = False

                if Insert_Tag:
                    print("insert--------")
                    equipnumgroup = cache.get('EquipNumGroup')
                    UpdateTestValue = ""
                    Updata_Tag = False
                    if len(Test_Value) != 0:
                        # Update_TestValue
                        for i in range(0, len(Test_Value)):
                            temp = "`" + Test_Value[i]['Test_Item'] + "` = '" + Test_Value[i]['Value'] + "',`" + Test_Value[i]['Test_Item'] + "_Result` = '" + Test_Value[i]['Result'] + "'"
                            if i < len(Test_Value) - 1:
                                temp += " , "
                            UpdateTestValue += temp
                        SQL = "UPDATE " + Station_No + "_test_tab set " + UpdateTestValue + " WHERE " + code_name + " = '" + Serial_No + "' and  station_no = '" + Station_No + "'"
                        if SQL_function4(SQL):
                            Updata_Tag = True
                        else:
                            Updata_Tag = False
                    elif len(Test_Value) == 0:
                        Updata_Tag = True
                    # ---------------------------------最后一站/ 测试解果为失败时候 存入 product_statistics_tab----------------------
                    if Updata_Tag:
                        print("updata------")
                        # 先查询搜索绑定信息，添加到product_statistics_tab时一并插入
                        SQL = "SELECT * FROM qr_confrimation_tab_sp WHERE " + code_name + " = '" + Serial_No + "' AND station_no = '" + Station_No + "'"
                        bind_data = SQL_function3(SQL)
                        print(bind_data)
                        bind_qr_code1 = bind_data[0]['qr_code1']
                        bind_qr_code2 = bind_data[0]['qr_code2']
                        bind_pcba_code1 = bind_data[0]['pcba_code1']
                        bind_pcba_code2 = bind_data[0]['pcba_code2']

                        # ---------- 数据库记录时间2 ----------- NG / 最后一站OK  发送产品信息给MOM ------------------------
                        # if not (Test_Result.upper() == "NG" and Station_No == equipnumgroup[len(equipnumgroup) - 1]):
                        SQL = "SELECT * FROM planorder_stand_tab WHERE order_no = '" + current_order_stand + "'"
                        order_data = SQL_function3(SQL)

                        SQL = "SELECT * FROM qr_confrimation_tab_sp WHERE " + code_name + " = '" + Serial_No + "'"
                        pro_data = SQL_function3(SQL)
                        if len(pro_data) == 0:
                            msg = "未查询到Code: " + Serial_No
                            raise Exception(msg)

                        SQL = "SELECT * FROM planorder_partno_tab WHERE gp_model = '" + pro_data[0]['gp_model'] + "'"
                        partno_data = SQL_function3(SQL)
                        if len(partno_data) == 0:
                            msg = "planorder_partno_tab未找到当前型号" + pro_data[0]['gp_model']
                            raise Exception(msg)

                        sta_delta_t = (t - datetime.datetime.strptime(pro_data[0]['check_time'],
                                                                      '%Y-%m-%d %H:%M:%S')).seconds

                        mom_uuid1 = t.strftime('%Y%m%d')
                        mom_uuid2 = ""

                        SQL = "SELECT * FROM qr_confrimation_tab_sp WHERE " + code_name + " = '" + Serial_No + "'"
                        sta_data = SQL_function3(SQL)
                        for it in sta_data:
                            mom_uuid2 = Getuuid_num(t)
                            if not it['test_time'] == "":
                                sta_delta_t = (datetime.datetime.strptime(it['test_time'],
                                                                          '%Y-%m-%d %H:%M:%S') - datetime.datetime.strptime(
                                    it['check_time'], '%Y-%m-%d %H:%M:%S')).seconds
                            else:
                                sta_delta_t = "0"
                                it['test_time'] = it['check_time']
                            Data2mom = {
                                "UUID": mom_uuid1 + "L" + line_no + mom_uuid2,
                                "STATION_NO": it['station_no'],
                                "CODE": "100",
                                # "OFFLINE_TIME": pro_data[0]['offline_time'],
                                "OFFLINE_TIME": it['test_time'],
                                "WORK_TIME": sta_delta_t,
                                "K_PART_NO": "K_PART_NO",
                                "K_PART_BATCH": "K_PART_BATCH",
                                "Q_PART_NO": partno_data[0]['Q_PART_NO'],
                                "Q_PART_BATCH": partno_data[0]['Q_PART_BATCH'],
                                "J_PART_NO": "",
                                "J_PART_BATCH": "",
                                "H_PART_NO": partno_data[0]['H_PART_NO'],
                                "H_PART_BATCH": partno_data[0]['H_PART_BATCH'],
                                "F_PART_NO": "",
                                "F_PART_BATCH": "",
                                "L_PART_NO": partno_data[0]['L_PART_NO'],
                                "L_PART_BATCH": partno_data[0]['L_PART_BATCH'],
                                "Z_PART_NO": partno_data[0]['Z_PART_NO'],
                                "Z_PART_BATCH": partno_data[0]['Z_PART_BATCH'],
                                "PCBA_1": it['pcba_code1'],
                                "PCBA_2": it['pcba_code2'],
                                "SN": code_data[0]['stand_code'],
                                "PART_NO": order_data[0]['part_no'],
                                "STATION_STATUS": Test_Result.upper(),
                            }
                            # 发送单站状态给MOM ---- 生产过程信息接口
                            if Planorder_stand_ismomcheck():
                                ret_data = ProcessInfo(Data2mom)
                                if ret_data['STATUS'] == "NG":
                                    raise Exception(ret_data['ERRORMSG'])
                        # ---------------------- 发送NG或最终OK 给看板 ------------------------------
                        # 发送产品最终生产信息给看板统计
                        # （只需要发送最后一站/失败的dataup结果，也就是最终产品的生产成败信息）
                        model_tag = cache.get('ModelSetFlag', default=0)
                        current_model = cache.get('current_model')
                        current_order = cache.get('current_order')
                        current_order_stand = cache.get('current_order_stand')

                        # if model_tag == 1 or model_tag == 0:  # 1 一键下发  2  选择机台下发
                        #     st_current_model = cache.get('current_model')
                        # elif model_tag == 2:
                        #     SQL = "SELECT st_current_model FROM station_tab WHERE gp_model = '" + current_model + "' and equipment_num = '" + Station_No + "'"
                        #     data = SQL_function3(SQL)
                        #     st_current_model = data[0]
                        # viewboard_topic = "Msg2Station/ViewBoard"
                        # viewboard_data_send = {
                        #     "Command": "S001",
                        #     "Station_No": Station_No,
                        #     "Gp_Model": st_current_model,
                        #     "ETP": Test_Result.upper()
                        # }
                        # SendMessage2Station(viewboard_topic, viewboard_data_send)
                        # 工单已经CLOSE 生产了一个OK ，但不能确定是最后一个（可能最后一个刚进站使得工单Close，此时就有一个OK出站）
                        if Test_Result.upper() == "OK":
                            print("------------------------------------报工")
                            if Planorder_stand_ismomcheck():
                                mom_ret = PlanOrderReport_SP(code_name, Serial_No, Station_No)
                                if mom_ret is False:
                                    raise Exception("报工上传MOM失败")
                    else:
                        result = "NG"
                        msg = "添加产品测试项数据失败"
                        raise Exception(msg)
                else:
                    result = "NG"
                    msg = "添加产品测试基本数据失败"
                    raise Exception(msg)

            except Exception as err:
                log.info("Exception ERROR" + str(err))
                if Test_Result.upper() == 'OK':
                    SQL = "UPDATE qr_confrimation_tab_sp set test_result = 'NG' WHERE " + code_name + " = '" + Serial_No + "' and station_no = '" + Station_No + "' and check_result = 'OK'"
                    if SQL_function4(SQL):
                        log.info("Code:" + Serial_No + "SP处理NG,本地下线更新成功")

                data_send = {
                    "Command": "0x04",
                    "DataUp_Result":
                        {
                            "Serial_No": Serial_No,
                            "Station_No": Station_No,
                            "Result": "NG",
                            "Message": str(err)
                        }
                }
                log.info(data_send)
                SendMessage2Station(equip_topic, data_send)
                return data_send

            data_send = {
                "Command": "0x04",
                "DataUp_Result":
                    {
                        "Serial_No": Serial_No,
                        "Station_No": Station_No,
                        "Result": "OK",
                        "Message": msg
                    }
            }
            log.info(data_send)
            print(msg)
            # 返回给机台的信息
            SendMessage2Station(equip_topic, data_send)
            return data_send
        elif command == '0x05':
            command = data['Command']
            Station_No = data['Station_No']
            equip_status_sp = cache.get('Equip_Status_SP')
            device_class_sp = cache.get('DeviceClass_SP')
            current_model_sp = cache.get("current_model_sp")
            for item in equip_status_sp:
                if item['EquipNumber'] == Station_No:
                    print(datetime.datetime.now())
                    if command == "0x05":  # （在一键下发的情况下）收到换型的返回信息后，向下一站再次发送换型信息
                        print("0x05")  # 普通换型 和 选择机台换型 只会修改打勾机台状态 （注意并发时的数据读写问题）
                        item['EquipOrder'] = 'Remodel'
                        item['EquipResult'] = data['Result']
                        Cache_writer("Equip_Status_SP", equip_status_sp, None)
                        print(">>>>>> ModelSetFlag: " + str(cache.get('ModelSetFlag', default=0)))
                        if data['Result'] == "OK" and cache.get('ModelSetFlag', default=0) == 1:  # 1 一键下发  2  选择机台下发
                            for i in range(0, len(device_class_sp)):
                                if (device_class_sp[i]['EquipNumber'] == Station_No and i != len(device_class_sp) - 1):
                                    topic = "Msg2Station/" + device_class_sp[i + 1]['EquipNumber']
                                    print(topic)
                                    send_data = {
                                        "Command": "0x05",
                                        "Gp_Model": current_model_sp
                                    }
                                    # 换型下发物料号信息
                                    # partno_data = Remodel_getpartno_data(Selected_Model)
                                    send_data['Q_PART_NO'] = ""
                                    send_data['H_PART_NO'] = ""
                                    send_data['P_PART_NO'] = ""
                                    send_data['J_PART_NO'] = ""
                                    send_data['ZC_PART_NO'] = ""

                                    SendMessage2Station(topic, send_data)
        elif command == '0x18':  # SP AGV 叫料上传MOM  Type 1 叫料 3 取料
            try:
                print('0x18')
                log.info("0x18")
                current_model_sp = cache.get('current_model_sp')
                Num = data['Num']
                Type = data['Status']
                STPO = data['Station_Point']
                STNO = data['Station_No']
                t = datetime.datetime.now()

                st_current_model = current_model_sp
                # 获取当前工单号对应的料号
                SQL = "SELECT * FROM mom_setting"
                data = SQL_function3(SQL)
                SQL = "SELECT * FROM planorder_partno_stpo_tab WHERE station_point = '" + STPO + "' AND gp_model = '" + st_current_model + "'"
                stpo_data = SQL_function3(SQL)
                # part_no_name = ['Q_PART_NO','H_PART_NO','P_PART_NO','J_PART_NO','ZC_PART_NO']
                # material_no = ""
                # for it in part_no_name:
                #     if not stpo_data[0][it] == "":
                #         material_no = stpo_data[0][it]
                part_no_name = stpo_data[0]['PART_NO_NAME']
                SQL = "SELECT " + part_no_name + " FROM planorder_partno_tab WHERE gp_model = '" + st_current_model + "'"
                partno_data = SQL_function3(SQL)
                material_no = partno_data[0][part_no_name]

                if stpo_data[0]['agv_send'].upper() == 'TRUE':  # 如果为上料
                    # 组装信息
                    Data2Mom = {
                        "REQ_QTY": str(Num),
                        "LINE_NO": data[0]['LINENO_STAND'],
                        "SHIFT_NO": "0",
                        "POINT_NO": STPO,
                        "PRODUCT_DATE": t.strftime('%Y-%m-%d'),
                        # "MATERIAL_NO": "37760003990A0A00"
                        "MATERIAL_NO": material_no
                    }
                    print(Data2Mom)
                    # 发送叫料信息给MOM
                    ret = SendMessage2MOM(Data2Mom, url['CreateSheetPull'])
                    log.info("--------ret")
                    log.info(ret)
                    ret = json.loads(ret)
                    print(ret['STATUS'])
                    # 返回信息给叫料的机台
                    data = {
                        "Command": "0x18",
                        "Station_Point": STPO,
                        "Result": "NG"
                    }
                    if ret['STATUS'] == "OK":
                        data['Result'] = "OK"
                        # 统计叫料数量
                        Data2Mom['REQ_QTY']
                        Data2Mom['MATERIAL_NO']
                    print("sta")
                    print(data)
                    print(STNO)
                    SendMessage2Station("Msg2Station/" + STNO, data)

                elif stpo_data[0]['agv_get'].upper() == 'TRUE':  # 如果为下料
                    Data2Mom = {
                        "LINE_NO": data[0]['LINENO'],
                        "POINT_NO": STPO,
                        "PARTNO": material_no,
                    }
                    print(Data2Mom)
                    ret = SendMessage2MOM(Data2Mom, url['CallAGVOffline'])
                    ret = json.loads(ret)
                    # 返回信息给的机台
                    data = {
                        "Command": "0x18",
                        "Station_Point": STPO,
                        "Result": "NG"
                    }
                    if ret['STATUS'] == "OK":
                        data['Result'] = "OK"

                    SendMessage2Station("Msg2Station/" + STNO, data)
            except Exception as err:
                log.info(str(err))
                data = {
                    "Command": "0x18",
                    "Station_Point": STPO,
                    "Result": "NG"
                }
                SendMessage2Station("Msg2Station/" + STNO, data)
        elif command == '0x19': #SP 生产支架SN  # 0镭雕SN  1 扫码
            try:
                print('0x19')
                log.info("SP 0x19")

                SN = ""
                msg = ""
                t = datetime.datetime.now()
                current_order = cache.get('current_order')
                current_order_stand = cache.get('current_order_stand')
                current_model = cache.get('current_model')
                current_model_sp = cache.get('current_model_sp')
                STNO = data['Station_No']

                filepath = GetFilePath("SoftWare.ini")
                conf = ConfigParser()  # 需要实例化一个ConfigParser对象
                conf.read(filepath)  # 需要添加上config.ini的路径，不需要open打开，直接给文件路径就读取，也可以指定encoding='utf-8'
                line_no = conf['CommonUse']['line_no']
                # sn_head = conf['CommonUse']['sn_head']

                # 先查看当前型号是否是镭雕上料的
                SQL = "SELECT * FROM model_tab WHERE gp_model = '" + current_model_sp + "'"
                data = SQL_function3(SQL)
                if data[0]['sn_way'] == "":
                    msg = "当前型号未找到上料方式,请检查"
                    raise Exception(msg)
                elif data[0]['sn_way'] == "1":
                    msg = "当前为扫码上料，请换型到镭雕上料型号"
                    raise Exception(msg)

                SQL = "SELECT * FROM planorder_stand_tab WHERE order_no = '" + current_order_stand + "'"
                data = SQL_function3(SQL)
                if len(data) == 0:
                    msg = "当前订单:" + current_order_stand + " 未找到"
                    raise Exception(msg)
                if data[0]['status'].upper() == "CLOSE":
                    msg = "当前工单已关闭"
                    raise Exception(msg)

                # 支架镭雕头部码的获取
                SQL = "SELECT * FROM planorder_laser_tab WHERE gp_model = '" + current_model_sp + "'"
                laser_data = SQL_function3(SQL)
                if len(laser_data) == 0:
                    msg = "未找到当前型号:" + current_model_sp + " 的镭雕前缀信息，请维护"
                    raise Exception(msg)
                stand_head_code1 = laser_data[0]['stand_head_code1']
                stand_head_code2 = laser_data[0]['stand_head_code2']

                # 生产一个新的sn码提供使用
                x = Getsn_num_stand(t)
                part_no = data[0]['part_no']
                year = str(t.year)[2:4]
                month = str(t.month)
                day = str(t.day)

                SN = stand_head_code1 + stand_head_code2 + part_no + "L" + year + month.zfill(2) + day.zfill(2) + str(x).zfill(4)
                print(SN)
                #壳体sn_num和num_real镭雕由上料check后才自增 支架涉及到壳子先check在镭雕支架，所以申请镭雕后直接自增sn_num_stand 和sn_real
                num_real = int(data[0]['num_real']) + 1
                SQL = "UPDATE planorder_stand_tab SET num_real = '" + str(num_real) + "',datetime = '" + str(t) + "' WHERE order_no = '" + current_order_stand + "'"
                if not SQL_function4(SQL):
                    raise Exception("更新planorder_stand_tab num_real数量失败")
                if not SQL_function4(SQL):
                    raise Exception("更新mom_setting sn_num_stand数量失败")

                SQL = "UPDATE mom_setting SET sn_num_stand = '" + str(x) + "'"
                if not SQL_function4(SQL):
                    raise Exception("更新mom_setting sn_num_stand数量失败")
                msg = "生成支架SN码成功"
                data = {
                    "Command": "0x19",
                    "Station_No": STNO,
                    "Sn": SN,
                    "Message": msg
                }
                SendMessage2Station("Msg2Station/" + STNO, data)
            except Exception as err:
                print(err)
                data = {
                    "Command": "0x19",
                    "Station_No": STNO,
                    "Sn": "",
                    "Message": str(err)
                }
                SendMessage2Station("Msg2Station/" + STNO, data)
        else:
            print("未找到command对应格式")
        return
    except Exception as err:
        print(str(err))
        return
def TRecv(client_Ip, data, topic):
    # thread_name("TRecv")
    global lock2
    # myip = socket.gethostbyname(socket.getfqdn(socket.gethostname()))
    # s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # s.connect(('8.8.8.8', 80))
    # myip = s.getsockname()[0]
    # s.close()
    myip = Getmyip_line()
    print("Myip_Line:" + myip)
    if myip == client_Ip:
        print("---------------本地重复IP消息，pass--------------")
        log.info("---------------本地重复IP消息，pass--------------")
        log.info("TRecv接收并解析信息,本地重复IP消息" + str(data))
        return
    if topic == "Msg2Station/ViewBoard":
        print("---------------来自看板的消息，不解析--------------")
        return
    print("*****TRecv接收并解析信息")
    log.info("TRecv接收并解析信息" + str(data))
    data = eval(data)
    print(data)

    equip_topic = ""
    device_class = cache.get('DeviceClass', default=None)
    device_class_sp = cache.get('DeviceClass_SP', default=None)
    print(device_class_sp)
    # 如果是SP系列机台单独处理(摄像头线体外的独立机台)
    for it in device_class_sp:
        if it['EquipIP'] == client_Ip:
            print("------------------接收的信息是来自SP机台-------------------")
            log.info("------------------接收的信息是来自SP机台-------------------")
            print("lock2.acquire")
            log.info("lock2.acquire")
            lock2.acquire()

            TRecv_SP(client_Ip, data, topic)

            lock2.release()
            print("lock2.release")
            log.info("lock2.release")
            return
    tag = False
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
            print("------------------接收的信息不是来自当前型号下的设备，不予解析-------------------")
            log.info("------------------接收的信息不是来自当前型号下的设备，不予解析-------------------")
            return
            # raise Exception('接收的信息不是来自当前型号下的设备，不予解析')
    # else:
    #     raise Exception('[msg_operation] DeviceClass is None ,can not find client_Ip')
    # 收到机台请求回复机台  0x01 0x02 0x03 0x04
    # 请求机台后收到机台回复 0x05 0x06 0x07
    try:
        command = data['Command']
        print("lock2.acquire")
        log.info("lock2.acquire")
        # lock2.acquire()
    except Exception as err:
        print("解析data，command格式时出现错误，直接退出解析")
        print(err)
        # lock2.release()
        print("lock2.release")
        log.info("lock2.release")
        return

    if command == '0x01':
        print('0x01')
        data_send = {
            "Command": "0x01",
            "Login_Result":
                {
                    "Level": 1,
                    "Result": "NG",
                    "Message": "test"
                }
        }
        SendMessage2Station(equip_topic, data_send)
        # lock2.release()
        print("lock2.release")
        log.info("lock2.release")
        return
    elif command == '0x02':                         #条码确认(前工程确认)checksn
        try:
            print('0x02')
            type = "0"

            sn = data['Check']['Serial_No']

            # 线体临时优化
            sn = sn.replace(' ', '')

            # 检查条码是否为空
            if not sn or sn.strip() == "":
                msg = "传入条码不能为空"
                log.error(msg)
                raise Exception(msg)

            stno = data['Check']['Station_No']
            type = str(data['Check']['Type'])
            gp_model = data['Check']['Gp_Model']
            equipnumgroup = cache.get('EquipNumGroup')
            current_model = cache.get('current_model')
            current_order = cache.get('current_order')

            order_sn_tag = False
            num_real = 0  # 实际生产的数量
            t = datetime.datetime.now()
            result = "NG"
            msg = ""

            # 只有订单开启时才能进入checksn的验证环节      该订单状态    Close 已经关闭   Start 正在生产
            SQL = "SELECT * FROM planorder_tab WHERE order_no = '" + current_order + "'"
            data = SQL_function3(SQL)
            if len(data) == 0:
                msg = "未找到当前工单信息:" + current_order + " 请检查"
                raise Exception(msg)
            elif len(data) > 1:
                msg = "找到多个工单信息:" + current_order + " 请检查"
                raise Exception(msg)


            # if data[0]['status'].upper() == "":       # 如果订单状态为空，说明目前是第一个上料
            #     SQL = "UPDATE planorder_tab set status = 'Start'" + " WHERE order_no = '" + current_order + "'"
            #     if SQL_function4(SQL):
            #         print("工单" + current_order + "开始修改成功")
                # msg = "工单" + current_order + "未开始，请检查"
                # print(msg)
                # raise Exception(msg)

            count = 0
            select_count = -1
            for item in equipnumgroup:
                if item == stno:
                    select_count = count
                    break
                else:
                    count += 1
            if select_count == -1:
                msg = "工位号不存在"
                raise Exception(msg)
            if select_count == 0:  # 如果为第一站 才校验工单状态
                if data[0]['status'].upper() == "START":
                    print("工单" + current_order + "开始确认成功")
                if data[0]['status'].upper() == "CLOSE":
                    msg = "工单" + current_order + "已经关闭"
                    print(msg)
                    raise Exception(msg)

            # 获取当前站点工艺对应的物料号和批次号 进行记录  /  过站强制进行的物料校验码比对 如螺丝胶水
            partno_data = Getpartno_data(stno,"",gp_model)
            partno_code = partno_data['partno_code']
            partbatch_code = partno_data['partbatch_code']

            sn_turn = 1
            # 确定当前上传的条码类型 和 名称
            # 0前壳qrcode1     1  pcba1        2后壳qrcode2    3 pcba2   4 料盘码
            code_name = ""
            if type == "0":
                code_name = "qr_code1"
            elif type == "1":
                code_name = "pcba_code1"
            elif type == "2":
                code_name = "qr_code2"
            elif type == "3":
                code_name = "pcba_code2"
            elif type == "5":
                code_name = "lens"

            # 检查当前产品
            # 检查当前的sn分配情况，并更新当前sn对应的时间状态
            SQL = "SELECT * FROM ordersn_tab WHERE " + code_name + " = '" + sn + "'"
            data = SQL_function3(SQL)

            if len(data) > 1:
                msg = "Code:" + sn + " ordersn_tab找到多个对应的信息"
                raise Exception(msg)
            elif len(data) == 1:
                # checksn时候，如果当前的条码产品已经存在，就更新该条码的过站时间信息
                order_sn_tag = True
            if len(data) == 0 and not stno.upper() == "ST01":
                msg = "Code:" + sn + " ordersn_tab未找到对应的信息"
                raise Exception(msg)


            model_tag = False
            SQL = "SELECT st_current_model FROM station_tab WHERE equipment_num = '" + stno + "' and gp_model = '" + cache.get('current_model') + "'"
            data = SQL_function3(SQL)
            if len(data) == 0:
                msg = "station_tab中未找到对应型号" + str(stno)
                raise Exception(msg)
            for it in data:
                if it['st_current_model'] == gp_model:              #当前机台的生产 是否为 设备对应的生产型号（选择机台换型或正常换型型号）
                    model_tag = True
            if model_tag:
                count = 0
                select_count = -1
                for item in equipnumgroup:
                    if item == stno:
                        select_count = count
                        break
                    else:
                        count += 1

                print("select_count = " + str(select_count))
                if select_count == -1:
                    msg = "工位号不存在"
                    raise Exception(msg)

                if select_count == 0:               #如果为第一站 只插入
                    if order_sn_tag:
                        msg = "Code:" + sn + " ordersn_tab 存在对应的信息"
                        raise Exception(msg)
                    # 检查工单型号 与 当前型号是否匹配    工单型号绑定
                    SQL = "SELECT st_current_model FROM station_tab WHERE equipment_num = '" + stno + "' and gp_model = '" + current_model + "'"
                    data = SQL_function3(SQL)
                    st_current_model = data[0]['st_current_model']
                    SQL = "SELECT * FROM planorder_partno_tab WHERE gp_model = '" + st_current_model + "'"
                    data_model_partno = SQL_function3(SQL)
                    SQL = "SELECT * FROM planorder_tab WHERE order_no = '" + current_order + "'"
                    data_order_partno = SQL_function3(SQL)
                    if not data_order_partno[0]['part_no'].upper() == data_model_partno[0]['BT_PART_NO'].upper():
                        msg = "当前型号物料号与工单型号不匹配"
                        raise Exception(msg)
                    # 第一站check时检查当前sn码中物料号
                    SQL = "SELECT * FROM model_tab WHERE gp_model = '" + current_model + "'"
                    data = SQL_function3(SQL)
                    if data[0]['sn_way'] == "1":  # 0镭雕码 1 扫码
                        retdata = Partno_check(stno, code_name, sn)
                        if retdata['result'] == "NG":
                            result = "NG"
                            raise Exception(retdata['msg'])

                    # 查看该sn时候已经有入站数据
                    SQL = "SELECT * FROM qr_confrimation_tab WHERE " + code_name + " = '" + sn + "' and station_no = '" + stno + "' and gp_model = '" + gp_model + "'"
                    data = SQL_function(SQL)
                    if len(data) > 0:
                        # 更新入站时间
                        SQL = "UPDATE qr_confrimation_tab set check_time = '" + str(t) +  "' WHERE " + code_name + " = '" + sn + "' and station_no = '" + stno + "' and gp_model = '" + gp_model + "'"
                        SQL_function4(SQL)
                        msg = "第一站已存在校验数据Code=" + str(sn)
                        result = "NG"
                        raise Exception(msg)
                    else:
                        # 只在第一站上料 修改 工单中数量记录信息num_real
                        SQL = "SELECT * FROM planorder_tab WHERE order_no = '" + current_order + "'"
                        data = SQL_function3(SQL)
                        num_real = int(data[0]['num_real'])

                        print("num_real:" + str(num_real))
                        new_num_real = num_real + 1
                        SQL = "UPDATE planorder_tab SET num_real = '" + str(new_num_real) + "',datetime = '" + str(t) + "' WHERE order_no = '" + current_order + "'"
                        if SQL_function4(SQL):
                            msg = "更新工单实际生产数量成功"
                            print(msg)
                        else:
                            msg = "更新工单实际生产数量失败"
                            raise Exception(msg)
                        # 更新mom_setting 中当日镭雕sn的编号  check过站了才自增镭雕号
                        SQL = "SELECT * FROM model_tab WHERE gp_model = '" + cache.get('current_model') + "'"
                        data = SQL_function3(SQL)
                        if data[0]['sn_way'] == "0":  #1扫码0镭雕
                            mom_data = Gettoday_numdata(t)
                            sn_num = int(mom_data[0]['sn_num']) + 1
                            SQL = "UPDATE mom_setting SET sn_num = '" + str(sn_num) + "'"
                            if not SQL_function4(SQL):
                                raise Exception("更新mom_setting sn_num数量失败")

                        SQL = "INSERT INTO qr_confrimation_tab (" + code_name + ",station_no,check_result,test_result,gp_model,check_time,part_no,part_batch) Value ('" + sn + "','" + stno + "','OK','NA','" + gp_model + "','" + str(t) + "','" + partno_code + "','" + partbatch_code + "')"
                        if SQL_function4(SQL):
                            SQL = "INSERT INTO ordersn_tab (order_no," + code_name + ",online_time,laststation_time,used,result,current_station) Value ('" + current_order + "','" + sn + "','" + str(t) + "','" + str(t) + "','True','','" + stno + "')"
                            if SQL_function4(SQL):
                                result = "OK"
                                msg = "Code:" + sn + " 校验成功,添加成功"
                            else:
                                result = "NG"
                                msg = "Code:" + sn + " 校验成功,添加失败"
                        else:
                            msg = "校验失败,添加失败"
                            raise Exception(msg)
                        #时间记录

                else:                               #如果不是第一站 前工程校验后插入数据
                    # 校验前工程工单号当前合法性
                    # retdata = Orderno_check(code_name,sn,stno)
                    # if retdata['result'] == "NG":
                    #     result = "NG"
                    #     raise Exception(retdata['msg'])

                    SQL = "SELECT * FROM qr_confrimation_tab " \
                          " WHERE " + code_name + " = '" + sn + "' and station_no = '" + stno + "' and gp_model = '" + gp_model + "'"
                    data = SQL_function(SQL)
                    if len(data) > 0:
                        log.info("检测到重复进站 - " + code_name + ":" + sn + " 已存在站:" + stno + " 的记录")
                        log.info("旧记录: id=" + str(data[0]['id']) + ", check=" + data[0]['check_result'] + ", test=" + data[0]['test_result'])

                        SQL = "UPDATE qr_confrimation_tab set check_time = '" + str(
                            t) + "' WHERE " + code_name + " = '" + sn + "' and station_no = '" + stno + "' and gp_model = '" + gp_model + "'"
                        SQL_function4(SQL)
                        msg = "该站已经存在当前SN数据,"

                        # 可复测站点识别
                        passdevice = cache.get('PassDevice', [])
                        SQL = "SELECT * FROM ordersn_tab WHERE " + code_name + " = '" + sn + "'"
                        ordersn_data = SQL_function3(SQL)
                        if len(ordersn_data) == 0:
                            result = "NG"
                            msg = 'ordersn_tab 未查询到' + sn
                            raise Exception(msg)

                        log.info("重投诊断 - 当前站:" + stno + ", ordersn_tab.current_station:" + ordersn_data[0]['current_station'] + ", retest_num:" + str(ordersn_data[0]['retest_num']) + ", PassDevice:" + str(passdevice))

                        if ordersn_data[0]['current_station'] == stno.upper():
                            # 同站复测
                            if int(ordersn_data[0]['retest_num']) <= 3:
                                for it in passdevice:
                                    if it.upper() == stno.upper():
                                        log.info("同站复测通过 - 重置" + stno + "记录状态")
                                        SQL_UPD = "UPDATE qr_confrimation_tab SET check_result='OK', test_result='NA', check_time='" + str(t) + "', part_no='" + partno_code + "', part_batch='" + partbatch_code + "' WHERE " + code_name + " = '" + sn + "' and station_no = '" + stno + "' and gp_model = '" + gp_model + "'"
                                        if SQL_function4(SQL_UPD):
                                            log.info("记录状态已重置(check=OK,test=NA)")
                                        else:
                                            log.warning("记录状态重置失败")
                                        if data[0]['test_result'] != 'OK':
                                            SQL_ORD = "UPDATE ordersn_tab SET retest_num = retest_num + 1, current_station = '" + stno + "', laststation_time = '" + str(t) + "' WHERE " + code_name + " = '" + sn + "'"
                                            if SQL_function4(SQL_ORD):
                                                log.info("ordersn_tab已更新(retest_num+1,current_station=" + stno + ")")
                                            else:
                                                log.warning("ordersn_tab更新失败")
                                        else:
                                            log.info("OK品同站复测,不累加retest_num")
                                        # 同步绑定信息
                                        bindcolumn_name = GetBindcolumn_name()
                                        for bind_it in bindcolumn_name:
                                            if bind_it == code_name or data[0][bind_it] == "":
                                                continue
                                            else:
                                                SQL_BIND = "UPDATE qr_confrimation_tab SET " + bind_it + " = '" + data[0][bind_it] + "' WHERE " + code_name + " = '" + sn + "' and station_no = '" + stno + "'"
                                                if not SQL_function4(SQL_BIND):
                                                    log.warning("绑定信息同步失败:" + bind_it)
                                        result = "OK"
                                        msg = "可复测进站 (已重置记录状态)"
                                        raise Exception(msg)
                                else:
                                    result = "NG"
                                    msg = '该站不在可复测站点列表中,不允许复测'
                                    raise Exception(msg)
                            else:
                                result = "NG"
                                msg = 'NG复测3次,过站失败'
                                raise Exception(msg)
                        else:
                            # 不同站：回退重投 或 脏数据处理
                            current_stnum_str = ordersn_data[0]['current_station'].replace("ST","").replace("st","")
                            if not current_stnum_str or not current_stnum_str.isdigit():
                                result = "NG"
                                msg = 'ordersn_tab.current_station格式异常:' + ordersn_data[0]['current_station']
                                raise Exception(msg)

                            current_stnum = int(current_stnum_str)
                            stnum = int(stno.replace("ST","").replace("st",""))
                            log.info("站位比较 - 尝试进站:ST" + str(stnum) + ", 已达站:ST" + str(current_stnum))

                            if stnum <= current_stnum:
                                # 回退或同站位（允许重投）
                                if int(ordersn_data[0]['retest_num']) <= 3:
                                    prev_station_idx = select_count - 1 if select_count > 0 else 0
                                    prev_station = equipnumgroup[prev_station_idx] if prev_station_idx < len(equipnumgroup) else stno
                                    SQL = "SELECT * FROM qr_confrimation_tab WHERE " + code_name + " = '" + sn + "' and station_no = '" + prev_station + "' and gp_model = '" + gp_model + "'"
                                    retest_data = SQL_function3(SQL)
                                    if len(retest_data) == 0:
                                        result = "NG"
                                        msg = "自动重投逻辑,未找到上一站" + prev_station + "的确认记录"
                                        raise Exception(msg)
                                    if retest_data[0]['check_result'] == "OK":
                                        log.info("回退重投通过(ST" + str(stnum) + "<=ST" + str(current_stnum) + ") - 重置" + stno + "记录状态")
                                        SQL_UPD = "UPDATE qr_confrimation_tab SET check_result='OK', test_result='NA', check_time='" + str(t) + "', part_no='" + partno_code + "', part_batch='" + partbatch_code + "' WHERE " + code_name + " = '" + sn + "' and station_no = '" + stno + "' and gp_model = '" + gp_model + "'"
                                        if SQL_function4(SQL_UPD):
                                            log.info("记录状态已重置(check=OK,test=NA)")
                                        else:
                                            log.warning("记录状态重置失败")
                                        # 更新ordersn_tab: retest_num+1, current_station回退, laststation_time
                                        SQL_ORD = "UPDATE ordersn_tab SET retest_num = retest_num + 1, current_station = '" + stno + "', laststation_time = '" + str(t) + "' WHERE " + code_name + " = '" + sn + "'"
                                        if SQL_function4(SQL_ORD):
                                            log.info("ordersn_tab已更新(retest_num+1,current_station=" + stno + ")")
                                        else:
                                            log.warning("ordersn_tab更新失败")
                                        # 同步绑定信息(从上一站记录复制)
                                        bindcolumn_name = GetBindcolumn_name()
                                        for bind_it in bindcolumn_name:
                                            if bind_it == code_name or retest_data[0][bind_it] == "":
                                                continue
                                            else:
                                                SQL_BIND = "UPDATE qr_confrimation_tab SET " + bind_it + " = '" + retest_data[0][bind_it] + "' WHERE " + code_name + " = '" + sn + "' and station_no = '" + stno + "'"
                                                if not SQL_function4(SQL_BIND):
                                                    log.warning("绑定信息同步失败:" + bind_it)
                                        result = "OK"
                                        msg = "自动重投逻辑,过站成功 (已重置记录状态,第" + str(int(ordersn_data[0]['retest_num'])+1) + "次重投)"
                                        raise Exception(msg)
                                    else:
                                        result = "NG"
                                        msg = "自动重投逻辑,前工程确认异常 (上一站" + prev_station + "的check结果不是OK)"
                                        raise Exception(msg)
                                else:
                                    result = "NG"
                                    msg = 'NG复测3次,过站失败'
                                    raise Exception(msg)

                            else:
                                # stnum > current_stnum: 前进方向但有旧记录 → 脏数据场景
                                log.warning("🔍 检测到脏数据场景 - 当前站ST" + str(stnum) + " > 已达站ST" + str(current_stnum) + " 但存在旧记录")
                                log.warning("建议检查: 该产品是否异常跳站或上次测试中断")

                                # 脏数据清理策略：如果复测次数未超限，允许清理并重新进站
                                if int(ordersn_data[0]['retest_num']) <= 3:
                                    log.info("脏数据重置 - 重置" + stno + "的异常记录状态，允许重新进站")
                                    SQL_UPD = "UPDATE qr_confrimation_tab SET check_result='OK', test_result='NA', check_time='" + str(t) + "', part_no='" + partno_code + "', part_batch='" + partbatch_code + "' WHERE " + code_name + " = '" + sn + "' and station_no = '" + stno + "' and gp_model = '" + gp_model + "'"
                                    if SQL_function4(SQL_UPD):
                                        log.info("脏数据已重置(check=OK,test=NA)")
                                        # 更新ordersn_tab: retest_num+1, current_station, laststation_time
                                        SQL_ORD = "UPDATE ordersn_tab SET retest_num = retest_num + 1, current_station = '" + stno + "', laststation_time = '" + str(t) + "' WHERE " + code_name + " = '" + sn + "'"
                                        if SQL_function4(SQL_ORD):
                                            log.info("ordersn_tab已更新(retest_num+1,current_station=" + stno + ")")
                                        else:
                                            log.warning("ordersn_tab更新失败")
                                        # 同步绑定信息(从当前旧记录复制)
                                        bindcolumn_name = GetBindcolumn_name()
                                        for bind_it in bindcolumn_name:
                                            if bind_it == code_name or data[0][bind_it] == "":
                                                continue
                                            else:
                                                SQL_BIND = "UPDATE qr_confrimation_tab SET " + bind_it + " = '" + data[0][bind_it] + "' WHERE " + code_name + " = '" + sn + "' and station_no = '" + stno + "'"
                                                if not SQL_function4(SQL_BIND):
                                                    log.warning("绑定信息同步失败:" + bind_it)
                                        result = "OK"
                                        msg = "脏数据已重置,允许重新进站"
                                    else:
                                        log.error("脏数据重置失败")
                                        result = "NG"
                                        msg = "脏数据重置失败，请手动检查qr_confrimation_tab"
                                    raise Exception(msg)
                                else:
                                    result = "NG"
                                    msg = 'NG复测3次,过站失败(脏数据场景)'
                                    raise Exception(msg)

                       
                    SQL = "SELECT * FROM qr_confrimation_tab WHERE " + code_name + " = '" + sn + "' and station_no = '" + \
                          equipnumgroup[select_count - 1] + "' and gp_model = '" + gp_model + "'"
                    data = SQL_function3(SQL)
                    if len(data) == 0:
                        msg = "未查询到上一站数据"
                        raise Exception(msg)
                    if len(data) > 1:
                        msg = "上一站存在重复数据，请排查"
                        raise Exception(msg)
                    if data[0]['check_result'] == "NG":
                        msg = "上一站的前功程确认已经失败"
                        raise Exception(msg)
                    elif data[0]['check_result'] == "NA":
                        msg = "上一站的前工程确认未记录"
                        raise Exception(msg)
                    elif data[0]['check_result'] == "OK":
                        result = "OK"
                    else:
                        msg = "不能识别上站的Check状态"
                        raise Exception(msg)

                    if data[0]['test_result'] == "NG":
                        result = "NG"
                        msg = "上一站的测试失败，不应进入本站"
                        raise Exception(msg)
                    elif data[0]['test_result'] == "NA":
                        result = "NG"
                        msg = "上一站的测试记录未记录，不应进入本站"
                        raise Exception(msg)
                    elif data[0]['test_result'] == "OK":
                        result = "OK"
                        if order_sn_tag:
                            SQL = "UPDATE ordersn_tab SET laststation_time = '" + str(
                                t) + "', current_station = '" + stno + "' WHERE " + code_name + " = '" + sn + "'"
                            if SQL_function4(SQL):
                                print("Code:" + sn + "状态更新成功")
                        SQL = "INSERT INTO qr_confrimation_tab (" + code_name + ",station_no,check_result,test_result,gp_model,check_time,part_no,part_batch) Value ('" + sn + "','" + stno + "','OK','NA','" + gp_model + "','" + str(t) + "','" + partno_code + "','" + partbatch_code + "')"
                        # SQL = "INSERT INTO qr_confrimation_tab (" + code_name + ",station_no,check_result,test_result,gp_model,check_time) Value ('" + sn + "','" + stno + "','OK','NA','" + gp_model + "','" + str(t) + "')"
                        if SQL_function4(SQL) is False:
                            msg = "插入数据失败"
                            raise Exception(msg)
                        # 同步更新该码对应的绑定信息
                        bindcolumn_name = GetBindcolumn_name()
                        for it in bindcolumn_name:
                            if it == code_name or data[0][it] == "":
                                continue
                            else:
                                SQL = "UPDATE qr_confrimation_tab SET " + it + " = '" + data[0][it] + "' WHERE " + code_name + " = '" + sn + "'"
                                if not SQL_function4(SQL):
                                    msg = "更新数据失败"
                                    raise Exception(msg)
                        else:
                            SQL = "UPDATE ordersn_tab SET laststation_time = '" + str(t) + "' , current_station = '" + stno + "' WHERE " + code_name + " = '" + sn + "' AND order_no = '" + current_order + "'"
                            if SQL_function4(SQL):
                                result = "OK"
                                msg = "Code:" + sn + " 校验成功,添加成功"
                            else:
                                result = "NG"
                                msg = "Code:" + sn + " 校验成功,添加失败"

                    else:
                        result = "NG"
                        msg = "不能识别上站的Test状态"
                        raise Exception(msg)
            elif gp_model == cache.get('current_model'):
                msg = "工位的型号和实际生产的型号不一致"
                raise Exception(msg)
            else:
                msg = "数据库型号和实际生产的型号不一致"
                raise Exception(msg)

            data_send = {
                "Command": "0x02",
                "Check_Result":
                    {
                        "Serial_No": sn,
                        "Result": result,
                        "Message": msg
                    }
            }
            log.info(str(data_send))
            SendMessage2Station(equip_topic, data_send)
            # lock2.release()
            print("lock2.release")
            log.info("lock2.release")
            return
        except Exception as err:
            log.info(str(err))
            data_send = {
                "Command": command,
                "Check_Result":
                    {
                        "Serial_No": sn,
                        "Result": result,
                        "Message": str(err)
                    }
            }
            log.info(str(data_send))
            SendMessage2Station(equip_topic, data_send)
            # lock2.release()
            print("lock2.release")
            log.info("lock2.release")
            return
    elif command == '0x031':        # 新的绑定逻辑，根据外部software文件中的数据识别绑定信息
        try:
            print("0x031")
            current_model = cache.get('current_model')
            current_order = cache.get('current_order')
            bind_dict = data['Bind']
            Station_No = data['Bind']['Station_No']
            Gp_Model = data['Bind']['Gp_Model']
            # 返回结果
            result = "NG"
            # 有效码的个数
            code_num = 0
            # 名称格式统一转换
            code_dict = {}
            for key in bind_dict:
                if key.upper() == "STATION_NO" or key.upper() == "GP_MODEL":
                    continue
                else:
                    key_temp = key.lower()
                    if key.upper() == "PCBA1":
                        key_temp = "pcba_code1"
                    elif key.upper() == "PCBA2":
                        key_temp = "pcba_code2"
                    elif key.upper() == "STAND":
                        key_temp = "stand_code"
                    code_dict[key_temp] = bind_dict[key]
                    if not bind_dict[key] == "":
                        code_num = code_num + 1
            print(code_dict)

            # 只有单码 确定重复性
            if code_num == 1:
                # 验证绑定码可用性
                for key in code_dict:
                    check_name = ""
                    check_code = ""
                    if not code_dict[key] == "":
                        check_name = key
                        check_code = code_dict[key]
                        break
                # # 校验物料号合法性
                # retdata = Partno_check(check_name, check_code)
                # if retdata['result'] == "NG":
                #     result = "NG"
                #     raise Exception(retdata['msg'])
                # 校验号码重复
                SQL = "SELECT * FROM qr_confrimation_tab WHERE " + check_name + " = '" + check_code + "' and station_no = '" + Station_No + "'"
                data = SQL_function3(SQL)
                if not len(data) == 0:
                    msg = "qr_confrimation_tab中已经存在 " + check_name + ":" + check_code + " 绑定,请检查"
                    raise Exception(msg)
                else:
                    result = "OK"
                    raise Exception("无重复")
            elif code_num == 2:             # 获取绑定码处理优先级表 bind_level 判断主码和绑定码
                main_name = ""
                main_code = ""
                bind_name = ""
                bind_code = ""
                # bind_level 根据当前型号获取
                SQL = "SELECT bind_level FROM station_bind_tab WHERE gp_model = '" + current_model + "'"
                data = SQL_function3(SQL)
                bind_level = eval(data[0]['bind_level'])
                if len(bind_level) == 0:
                    msg = "未找到当前型号:" + current_model + " 的站点绑定规则，请检查"
                    raise Exception(msg)

                temp_num = 1
                for code_name in bind_level:
                    print(code_name)
                    for key in code_dict:
                        if key == code_name and (not code_dict[key] == ""):
                            if temp_num == 1:
                                main_name = key
                                main_code = code_dict[key]
                                temp_num = temp_num + 1
                            elif temp_num == 2:
                                bind_name = key
                                bind_code = code_dict[key]
                                break
                # 如果没有对应上主码信息
                if main_name == "":
                    msg = "绑定失败,未找到主码信息,请检查"
                    raise Exception(msg)
                # 验证该码对应工单的合法性
                retdata = Orderno_check(main_name, main_code, Station_No)
                if retdata['result'] == "NG":
                    result = "NG"
                    raise Exception(retdata['msg'])
                # 验证主码可用性
                if not main_code or main_code.strip() == "":
                    msg = "传入条码不能为空"
                    log.error(msg)
                    raise Exception(msg)
                SQL = "SELECT * FROM qr_confrimation_tab WHERE " + main_name + " = '" + main_code + "' and station_no = '" + Station_No + "'"
                data = SQL_function3(SQL)
                if len(data) == 0:
                    msg = "qr_confrimation_tab未找到" + main_name + ":" + main_code + " 对应的绑定信息"
                    raise Exception(msg)
                elif len(data) > 1:
                    msg = "qr_confrimation_tab找到多个" + main_name + ":" + main_code + " 对应的绑定信息"
                    raise Exception(msg)
                # # 验证绑定码可用性 物料号校验
                # retdata = Partno_check(bind_name, bind_code)
                # if retdata['result'] == "NG":
                #     result = "NG"
                #     raise Exception(retdata['msg'])
                # 验证绑定码可用性 重复校验
                # # 原逻辑：镜头已使用时直接报错
                # SQL = "SELECT * FROM qr_confrimation_tab WHERE " + bind_name + " = '" + bind_code + "' and station_no = '" + Station_No + "'"
                # data = SQL_function3(SQL)
                # if not len(data) == 0:
                #     msg = "qr_confrimation_tab中已经存在 " + bind_name + ":" + bind_code + " 绑定,请检查"
                #     raise Exception(msg)
                # 新逻辑：镜头已使用时，解除该镜头的绑定关系，允许重新绑定
                SQL = "SELECT * FROM qr_confrimation_tab WHERE " + bind_name + " = '" + bind_code + "' and station_no = '" + Station_No + "'"
                data = SQL_function3(SQL)
                if not len(data) == 0:
                    msg = bind_name + ":" + bind_code + " 已存在绑定关系，将解除绑定"
                    log.info(msg)
                    SQL = "UPDATE qr_confrimation_tab SET " + bind_name + " = '' WHERE " + bind_name + " = '" + bind_code + "' and station_no = '" + Station_No + "'"
                    if not SQL_function4(SQL):
                        msg = "解除" + bind_name + "绑定关系失败"
                        raise Exception(msg)

                SQL = "SELECT st_current_model FROM station_tab WHERE equipment_num = '" + Station_No + "' and gp_model = '" + current_model + "'"
                data = SQL_function(SQL)
                if data[0]['st_current_model'] == Gp_Model:
                    # ------------ 更新Station_No_test_tab 中的绑定内容--------------
                    SQL = "SELECT test_result FROM " + Station_No + "_test_tab " + "WHERE " + main_name + " = '" + main_code + "' and gp_model = '" + Gp_Model + "'"
                    data = SQL_function3(SQL)
                    if len(data) == 0:
                        # msg = "未找到产品在本工位的入站信息"
                        # 没找到就插入新的  和dataup相关
                        SQL = "INSERT INTO " + Station_No + "_test_tab (" + main_name + ",station_no,gp_model) values ('" + main_code + "','" + Station_No + "','" + Gp_Model + "')"
                        if SQL_function4(SQL) is False:
                            msg = "创建产品数据记录失败"
                            raise Exception(msg)
                    elif len(data) >= 1:
                        SQL = "UPDATE " + Station_No + "_test_tab SET " + bind_name + " = '" + bind_code + "' WHERE " + main_name + " = '" + main_code + "'"
                        if SQL_function4(SQL):
                            msg = Station_No + "_test_tab 更新绑定成功"
                            result = "OK"
                        else:
                            msg = Station_No + "_test_tab 更新绑定失败"
                    # ------------ 更新qr_confrimation_tab 中的绑定内容--------------
                    SQL = "UPDATE qr_confrimation_tab SET " + bind_name + " = '" + bind_code + "' WHERE " + main_name + " = '" + main_code + "'"
                    if SQL_function4(SQL):
                        msg = "qr_confrimation_tab 绑定更新成功"
                    else:
                        msg = "qr_confrimation_tab 绑定更新失败"
                        result = "NG"
                    # ------------ 更新qr_bind_tab 中的绑定内容--------------
                    SQL = "SELECT * FROM qr_bind_tab WHERE " + main_name + " = '" + main_code + "' and gp_model = '" + Gp_Model + "'"
                    data = SQL_function3(SQL)
                    if len(data) > 1:
                        msg = "qr_bind_tab找到多个信息，请检查"
                    elif len(data) == 1:
                        SQL = "UPDATE qr_bind_tab SET " + bind_name + " = '" + bind_code + "' WHERE " + main_name + " = '" + main_code + "'"
                        if SQL_function4(SQL):
                            msg = "主码" + main_name + ":" + main_code + "和:" + bind_name + ":" + bind_code + " 更新绑定成功"
                            result = "OK"
                        else:
                            msg = "qr_bind_tab更新绑定数据失败"
                    elif len(data) == 0:
                        SQL = "INSERT INTO qr_bind_tab (" + main_name + "," + bind_name + ",gp_model) values ('" + main_code + "','" + bind_code + "','" + Gp_Model + "')"
                        if SQL_function4(SQL):
                            msg = "主码" + main_name + ":" + main_code + "和" + bind_name + ":" + bind_code + " 添加绑定成功"
                            result = "OK"
                        else:
                            msg = "qr_bind_tab添加绑定数据失败"
                    # ------------ 更新ordersn_tab 中的绑定内容--------------
                    if not main_code or main_code.strip() == "":
                        msg = "传入条码不能为空"
                        log.error(msg)
                        raise Exception(msg)
                    SQL = "SELECT * FROM ordersn_tab WHERE " + main_name + " = '" + main_code + "'"
                    data = SQL_function3(SQL)
                    if len(data) > 1:
                        msg = "ordersn_tab找到多个信息，请检查"
                    elif len(data) == 0:
                        msg = "ordersn_tab未找到主码信息，请检查"
                    elif len(data) == 1:
                        SQL = "UPDATE ordersn_tab SET " + bind_name + " = '" + bind_code + "' WHERE " + main_name + " = '" + main_code + "'"
                        if SQL_function4(SQL):
                            msg = "主码" + main_name + ":" + main_code + "和:" + bind_name + ":" + bind_code + " 更新绑定成功"
                            result = "OK"
                        else:
                            msg = "ordersn_tab更新绑定数据失败"
                else:
                    msg = "绑定的型号和当前型号不一致"
                    raise Exception(msg)

                data_send = {
                    "Command": "0x03",
                    "Bind_Result":
                        {
                            "Result": result,
                            "Message": msg
                        }
                }
                log.info(data_send)
                SendMessage2Station(equip_topic, data_send)
                # lock2.release()
                print("lock2.release")
                log.info("lock2.release")
                return

        except Exception as err:
            type = -1
            if not (code_num == 0) or (code_num == 3):
                if code_num == 1:
                    bind_name = check_name
                if bind_name == 'qr_code1' or bind_name == 'qr_code2':
                    type = 0
                elif bind_name == 'pcba_code1' or bind_name == 'pcba_code2':
                    type = 1
                elif bind_name == 'lens':
                    type = 2
                elif bind_name == 'stand_code':
                    type = 3

            print(err)
            data_send = {
                "Command": "0x03",
                "Bind_Result":
                    {
                        "Result": result,
                        "Type": str(type),
                        "Message": str(err)
                    }
            }
            print(data_send)
            log.info(data_send)
            SendMessage2Station(equip_topic, data_send)
            # lock2.release()
            print("lock2.release")
            log.info("lock2.release")
            return

    elif command == '0x03':       # 将pcba12 qr12 lens 全部传入进行主码、绑定码识别和绑定。当只有一个有效数据时，为对该码进行重复性校验，未存在该码信息返回OK，否则为NG
        temp_num = 0
        try:
            print("0x03")
            current_model = cache.get('current_model')
            current_order = cache.get('current_order')

            Pcba1 = data['Bind']['Pcba1']
            Pcba2 = data['Bind']['Pcba2']
            Lens = data['Bind']['Lens']
            Stand = data['Bind']['Stand']
            Qr_code1 = data['Bind']['Qr_code1']
            Qr_code2 = data['Bind']['Qr_code2']

            #线体临时优化
            Qr_code2 = Qr_code2.replace(' ','')

            Station_No = data['Bind']['Station_No']
            Gp_Model = data['Bind']['Gp_Model']

            result = 'NG'
            msg = ''
            bind_code = ""
            bind_name = ""
            # 汇总绑定信息
            code_list = []
            code_list.append(Qr_code1)
            code_list.append(Pcba1)
            code_list.append(Qr_code2)
            code_list.append(Pcba2)
            code_list.append(Lens)
            code_list.append(Stand)
            print(code_list)
            print(code_list)
            name_list = ['qr_code1','pcba_code1','qr_code2','pcba_code2','lens','stand_code']
            print(name_list)

            # 确保绑定信息足够
            temp_num = 0
            # 对一主码 多个绑定码 情况做区分
            multi_bind_tag = False

            for item in code_list:
                if not item == "":
                    temp_num += 1
            if temp_num < 2:
                if temp_num == 0:
                    msg = "缺少绑定信息"
                    raise Exception(msg)
                elif temp_num == 1:
                    check_code = ""
                    check_name = ""
                    for i in range(0, len(code_list)):
                        print(code_list[i])
                        print(name_list[i])
                        if not code_list[i] == "" or code_list[i] == None:
                            check_code = code_list[i]
                            check_name = name_list[i]
                            break
                    # 验证绑定码可用性
                    SQL = "SELECT * FROM qr_confrimation_tab WHERE " + check_name + " = '" + check_code + "' and station_no = '" + Station_No + "'"
                    data = SQL_function3(SQL)
                    if not len(data) == 0:
                        msg = "qr_confrimation_tab中已经存在 " + check_name + ":" + check_code + " 绑定,请检查"
                        # 重复绑定码，返回OK
                        result = "NG"
                        raise Exception(msg)
                    else:
                        result = "OK"
                        raise Exception("无重复")
            elif temp_num > 2:
                multi_bind_tag = True
                raise Exception("三码绑定情况，暂时未实现")

            # 找到主码
            main_code = ""
            main_name = ""
            count_num = 0
            for i in range(0,len(code_list)):
                print(code_list[i])
                print(name_list[i])
                count_num += 1
                if not code_list[i] == "":
                    main_code = code_list[i]
                    main_name = name_list[i]
                    break
            # 验证主码可用性
            if not main_code or main_code.strip() == "":
                msg = "传入条码不能为空"
                log.error(msg)
                raise Exception(msg)
            SQL = "SELECT * FROM qr_confrimation_tab WHERE " + main_name + " = '" + main_code + "' and station_no = '" + Station_No + "'"
            data = SQL_function3(SQL)
            if len(data) == 0:
                msg = "qr_confrimation_tab未找到" + main_name + ":" + main_code + " 对应的绑定信息"
                raise Exception(msg)
            elif len(data) > 1:
                msg = "qr_confrimation_tab找到多个" + main_name + ":" + main_code + " 对应的绑定信息"
                raise Exception(msg)

            # 找到绑定码
            bind_code = ""
            bind_name = ""
            for i in range(count_num, len(code_list)):
                count_num += 1
                if not code_list[i] == "":
                    bind_code = code_list[i]
                    bind_name = name_list[i]
                    break
            # 验证绑定码可用性 物料号校验
            retdata = Partno_check(Station_No, bind_name, bind_code)
            if retdata['result'] == "NG":
                result = "NG"
                raise Exception(retdata['msg'])
            #获取绑定码对应的物料号和批次号
            partno_data = Getpartno_data("",bind_name,Gp_Model)
            partno_code = partno_data['partno_code']
            partbatch_code = partno_data['partbatch_code']
            # 验证绑定码可用性 重复校验
            # # 原逻辑：镜头已使用时直接报错
            # SQL = "SELECT * FROM qr_confrimation_tab WHERE " + bind_name + " = '" + bind_code + "' and station_no = '" + Station_No + "'"
            # data = SQL_function3(SQL)
            # if not len(data) == 0 :
            #     msg = "qr_confrimation_tab中已经存在 " + bind_name + ":" + bind_code + " 绑定,请检查"
            #     raise Exception(msg)
            # 新逻辑：镜头已使用时，解除该镜头的绑定关系，允许重新绑定
            SQL = "SELECT * FROM qr_confrimation_tab WHERE " + bind_name + " = '" + bind_code + "' and station_no = '" + Station_No + "'"
            data = SQL_function3(SQL)
            if not len(data) == 0 :
                msg = bind_name + ":" + bind_code + " 已存在绑定关系，将解除绑定"
                log.info(msg)
                SQL = "UPDATE qr_confrimation_tab SET " + bind_name + " = '' WHERE " + bind_name + " = '" + bind_code + "' and station_no = '" + Station_No + "'"
                if not SQL_function4(SQL):
                    msg = "解除" + bind_name + "绑定关系失败"
                    raise Exception(msg)
            # # 验证主码绑定状态
            # SQL = "SELECT * FROM ordersn_tab WHERE " + main_name + " = '" + main_code + "'"
            # sn_data = SQL_function3(SQL)
            # if not sn_data[0][bind_name] == "":
            #     msg = "该主码已绑定"
            #     raise Exception(msg)

            # else:
            #     SQL = "UPDATE qr_confrimation_tab SET " + bind_name + " = '" + bind_code + "' WHERE " + main_name + " = '" + main_code + "'"
            #     if SQL_function4(SQL):
            #         msg = "qr_confrimation_tab 绑定更新成功"
            #     else:
            #         msg = "qr_confrimation_tab 绑定更新失败"
            #         result = "NG"
            #     # 更新绑定码对应的物料号和批次号
            #     SQL = "UPDATE qr_confrimation_tab SET part_no = '" + partno_code + "',part_batch = '" + partbatch_code + "' WHERE " + main_name + " = '" + main_code + "'"
            #     if SQL_function4(SQL):
            #         msg = "物料号更新成功"
            #     else:
            #         msg = "物料号更新失败"
            #         result = "NG"
            SQL = "SELECT st_current_model FROM station_tab WHERE equipment_num = '" + Station_No + "' and gp_model = '" + current_model + "'"
            data = SQL_function(SQL)
            if data[0]['st_current_model'] == Gp_Model:
                # 更新qr_confrimation_tab 中的绑定内容
                SQL = "UPDATE qr_confrimation_tab SET " + bind_name + " = '" + bind_code + "' WHERE " + main_name + " = '" + main_code + "'"
                if SQL_function4(SQL):
                    msg = "qr_confrimation_tab 绑定更新成功"
                else:
                    msg = "qr_confrimation_tab 绑定更新失败"
                    result = "NG"
                # 更新绑定码对应的物料号和批次号  如果第一站有绑定功能那边该站点会存在 上料时的物料批次号 和 零件绑定时的物料批次号，因此存在一站记录多个物料批次号的情况存在
                SQL = "SELECT * FROM qr_confrimation_tab WHERE " + main_name + " = '" + main_code + "' and station_no = '" + Station_No + "'"
                data = SQL_function3(SQL)
                if not (data[0]['part_no'] == "" and data[0]['part_batch'] == ""):
                    if partno_code == "" and partbatch_code == "":
                        partno_code = data[0]['part_no']
                        partbatch_code = data[0]['part_batch']
                    partno_code = data[0]['part_no'] + "/" + partno_code
                    partbatch_code = data[0]['part_batch'] + "/" + partbatch_code
                SQL = "UPDATE qr_confrimation_tab SET part_no = '" + partno_code + "',part_batch = '" + partbatch_code + "' WHERE " + main_name + " = '" + main_code + "' and station_no = '" + Station_No + "'"
                if SQL_function4(SQL):
                    msg = "物料号更新成功"
                else:
                    msg = "物料号更新失败"
                    result = "NG"
                # ------------ 更新Station_No_test_tab 中的绑定内容 --------------
                SQL = "SELECT test_result FROM " + Station_No + "_test_tab " + "WHERE " + main_name + " = '" + main_code + "' and gp_model = '" + Gp_Model + "'"
                data = SQL_function3(SQL)
                if len(data) == 0:
                    # msg = "未找到产品在本工位的入站信息"
                    # 没找到就插入新的  和dataup相关
                    SQL = "INSERT INTO " + Station_No + "_test_tab (" + main_name + ",station_no,gp_model) values ('" + main_code + "','" + Station_No + "','" + Gp_Model + "')"
                    if SQL_function4(SQL) is False:
                        msg = "创建产品数据记录失败"
                        raise Exception(msg)
                elif len(data) >= 1:
                    SQL = "UPDATE " + Station_No + "_test_tab SET " + bind_name + " = '" + bind_code + "' WHERE " + main_name + " = '" + main_code + "'"
                    if SQL_function4(SQL):
                        msg = Station_No + "_test_tab 更新绑定成功"
                        result = "OK"
                    else:
                        msg = Station_No + "_test_tab 更新绑定失败"
                # ------------ 更新qr_bind_tab 中的绑定内容--------------
                SQL = "SELECT * FROM qr_bind_tab WHERE " + main_name + " = '" + main_code + "' and gp_model = '" + Gp_Model + "'"
                data = SQL_function3(SQL)
                if len(data) > 1:
                    msg = "qr_bind_tab找到多个信息，请检查"
                elif len(data) == 1:
                    SQL = "UPDATE qr_bind_tab SET " + bind_name + " = '" + bind_code + "' WHERE " + main_name + " = '" + main_code + "'"
                    if SQL_function4(SQL):
                        msg = "主码" + main_name + ":" + main_code + "和:" + bind_name + ":" + bind_code + " 更新绑定成功"
                        result = "OK"
                    else:
                        msg = "qr_bind_tab更新绑定数据失败"
                        raise Exception(msg)
                elif len(data) == 0:
                    SQL = "INSERT INTO qr_bind_tab (" + main_name + "," + bind_name + ",gp_model) values ('" + main_code + "','" + bind_code + "','" + Gp_Model + "')"
                    if SQL_function4(SQL):
                        msg = "主码" + main_name + ":" + main_code + "和" + bind_name + ":" + bind_code + " 添加绑定成功"
                        result = "OK"
                    else:
                        msg = "qr_bind_tab添加绑定数据失败"
                        raise Exception(msg)
                # ------------ 更新ordersn_tab 中的绑定内容--------------
                if not main_code or main_code.strip() == "":
                    msg = "传入条码不能为空"
                    log.error(msg)
                    raise Exception(msg)
                SQL = "SELECT * FROM ordersn_tab WHERE " + main_name + " = '" + main_code + "'"
                data = SQL_function3(SQL)
                if len(data) > 1:
                    msg = "ordersn_tab找到多个信息，请检查"
                    raise Exception(msg)
                elif len(data) == 0:
                    msg = "ordersn_tab未找到主码信息，请检查"
                    raise Exception(msg)
                elif len(data) == 1:
                    SQL = "UPDATE ordersn_tab SET " + bind_name + " = '" + bind_code + "' WHERE " + main_name + " = '" + main_code + "'"
                    if SQL_function4(SQL):
                        msg = "主码" + main_name + ":" + main_code + "和:" + bind_name + ":" + bind_code + " 更新绑定成功"
                        result = "OK"
                    else:
                        msg = "ordersn_tab更新绑定数据失败"
            else:
                result = "NG"
                msg = "绑定的型号和当前型号不一致"
                raise Exception(msg)

            if not PassAfterBind(Gp_Model,Station_No,main_name,main_code):
                log.info("PassAfterBind Fail")
                raise Exception("绑定成功,特殊站点出站失败")

            data_send = {
                "Command": "0x03",
                "Bind_Result":
                    {
                        "Result": result,
                        "Message": msg
                    }
            }
            log.info(data_send)
            SendMessage2Station(equip_topic, data_send)
            # lock2.release()
            print("lock2.release")
            log.info("lock2.release")
            return

        except Exception as err:
            type = -1
            if not (temp_num == 0) or (temp_num == 3):
                if temp_num == 1:
                    bind_name = check_name
                if bind_name == 'qr_code1' or bind_name == 'qr_code2':
                    type = 0
                elif bind_name == 'pcba_code1' or bind_name == 'pcba_code2':
                    type = 1
                elif bind_name == 'lens':
                    type = 2
                elif bind_name == 'stand_code':
                    type = 3

            print(err)
            data_send = {
                "Command": "0x03",
                "Bind_Result":
                    {
                        "Result": result,
                        "Type": str(type),
                        "Message": str(err)
                    }
            }
            print(data_send)
            log.info(data_send)
            SendMessage2Station(equip_topic, data_send)
            # lock2.release()
            print("lock2.release")
            log.info("lock2.release")
            return
    elif command == '0x04':                                 #数据上传指令 dateup
        try:
            print('0x04')
            Type = "0"

            Serial_No = data['DataUp']['Serial_No']

            # 线体临时优化
            Serial_No = Serial_No.replace(' ', '')

            Station_No = data['DataUp']['Station_No']
            Site_Name = data['DataUp']['SiteName']
            # Site_Name = "site_name"
            Type = str(data['DataUp']['Type'])
            Test_Result = data['DataUp']['Test_Result']   # 总结果
            Gp_Model = data['DataUp']['Gp_Model']
            Judge_Code = data['DataUp']['Judge_Code']

            Start_Time = data['DataUp']['Start_Time']
            End_Time = data['DataUp']['End_Time']

            Test_Value = data['DataUp']['Test_Value']     # {"Test_Item":"","Value":"","Result":""}
            msg = ""
            result = "NG"
            t = datetime.datetime.now()
            print(t)
            line_no = Getline_no()
            # 转换时间戳
            if not Start_Time == "" and not Start_Time == "":
                Start_Time = timestamp_to_timestr(Start_Time)
                End_Time = timestamp_to_timestr(End_Time)
            # 确定当前上传的条码类型 和 名称
            # 0前壳qrcode1     1  pcba1        2后壳qrcode2    3 pcba2
            code_name = ""
            if Type == "0":
                code_name = "qr_code1"
            elif Type == "1":
                code_name = "pcba_code1"
            elif Type == "2":
                code_name = "qr_code2"
            elif Type == "3":
                code_name = "pcba_code2"
            elif Type == "5":
                code_name = "lens"

            if code_name == "":
                msg = "code_name未匹配 Type=" + Type
                raise Exception(msg)

            # ------------------------------------- 查询当前sn的cheksn 和result 状态 ---------------------------------------------
            SQL = "SELECT check_result, test_result FROM qr_confrimation_tab WHERE " + code_name + " = '" + Serial_No + "' and station_no = '" + Station_No + "' and gp_model = '" + Gp_Model + "'"
            data = SQL_function3(SQL)
            if len(data) > 1:
                msg = "存在两条重复数据，请排查"
                raise Exception(msg)
            elif len(data) == 0:
                msg = "未查询到本站数据"
                raise Exception(msg)
            elif len(data) == 1:
               if data[0]['check_result'] == "NG":
                   msg = "本站的前功程确认已经失败，不能过站"
                   raise Exception(msg)
               elif data[0]['check_result'] == "NA":
                   msg = "工程确认未记录，不能过站"
                   raise Exception(msg)
               elif data[0]['check_result'] == "OK":
                   msg = "OK"
               else:
                   msg = "不能识别Check状态"
                   raise Exception(msg)
               if data[0]['test_result'] != "NA":
                   msg = "该站已存在测试记录,继续追加记录"
                   # raise Exception(msg)
               else:
                   msg = "OK"


            # 可复测站点识别
            SQL = "SELECT * FROM ordersn_tab WHERE " + code_name + " = '" + Serial_No + "'"
            ordersn_data = SQL_function3(SQL)
            if len(ordersn_data) == 0:
                msg = 'ordersn_tab 未查询到' + Serial_No
                raise Exception(msg)

            if Test_Result.upper() == "NG":
                if ordersn_data[0]['current_station'] == Station_No.upper():
                    if int(ordersn_data[0]['retest_num']) < 3:
                        passdevice = cache.get('PassDevice', [])
                        for it in passdevice:
                            if it.upper() == Station_No.upper():
                                result = "OK"
                                msg = Station_No + "当前产品NG " + ordersn_data[0]['retest_num'] + "次,不记录数据"
                                SQL = "UPDATE ordersn_tab set retest_num = " + str(
                                    int(ordersn_data[0]['retest_num']) + 1) \
                                      + " WHERE " + code_name + " = '" + Serial_No + "'"
                                if not SQL_function4(SQL):
                                    result = 'NG'
                                    msg = "retest_num 更新失败"
                                raise Exception(msg)
                else:
                    current_stnum = int(ordersn_data[0]['current_station'].replace("ST", ""))
                    stnum = int(Station_No.replace("ST", ""))
                    if stnum < current_stnum:
                        SQL = "DELETE FROM " + Station_No + "_test_tab WHERE " + code_name + " = '" + Serial_No + "'"
                        if not SQL_function4(SQL):
                            msg = "删除测试信息失败"
                            result = 'NG'
                            raise Exception(msg)

                    else:
                        result = "NG"
                        msg = "自动重投逻辑,测试数据站位异常"
                        raise Exception(msg)
            else:
                current_stnum = int(ordersn_data[0]['current_station'].replace("ST", ""))
                stnum = int(Station_No.replace("ST", ""))
                if stnum <= current_stnum:
                    SQL = "DELETE FROM " + Station_No + "_test_tab WHERE " + code_name + " = '" + Serial_No + "'"
                    if not SQL_function4(SQL):
                        msg = "删除测试信息失败"
                        result = 'NG'
                        raise Exception(msg)
                else:
                    result = "NG"
                    msg = "自动重投逻辑,测试数据站位异常"
                    raise Exception(msg)


            # Update_Product_Status
            UpdateResult = ""
            if Test_Result.upper() == "OK":
                UpdateResult = "OK"
            else:
                UpdateResult = "NG"
            # 更新 test_result 测试项数据
            SQL = "UPDATE qr_confrimation_tab set test_result = '" + UpdateResult + "', test_time = '" + str(t) + "', site_name = '" + Site_Name + "' WHERE " + code_name + " = '" + Serial_No + "' and station_no = '" + Station_No + "' and check_result = 'OK' and gp_model = '" + Gp_Model + "'"
            data = SQL_function4(SQL)
            if data:
                msg = "测试记录更新成功"
            else:
                msg = "产品信息更新失败"
                result = 'NG'
                raise Exception(msg)

            # OK品过站时重置retest_num为0
            if Test_Result.upper() == "OK":
                SQL = "UPDATE ordersn_tab SET retest_num = 0 WHERE " + code_name + " = '" + Serial_No + "'"
                if SQL_function4(SQL):
                    log.info("ordersn_tab已更新(retest_num=0)")
                else:
                    log.warning("ordersn_tab更新失败(retest_num重置)")

            # Insert_TestValue
            Insert_Tag = False
            Errcode = ""
            if Test_Result.upper() != "OK":
                if len(Judge_Code) != 0:
                    for i in range(0, len(Judge_Code)):
                        Errcode += str(Judge_Code[i])
                        if i < len(Judge_Code)-1:
                            Errcode += "-"
                else:
                    msg = "TestResut is NG,But Not UpLoad judgecode"
                    # raise Exception(msg)

            SQL = "SELECT column_name FROM information_schema.COLUMNS WHERE table_name = '" + Station_No + "_test_tab'"
            data_columns = SQL_function3(SQL)
            SQL = "INSERT INTO " + Station_No + "_test_tab " + "(" + code_name + ",station_no,test_result,gp_model,judge_code,start_time,end_time) values ('" + Serial_No + "','" + Station_No + "','" + Test_Result + "','" + Gp_Model + "','" + Errcode + "','" + Start_Time + "','" + End_Time + "')"
            AlterRet = True
            if len(Test_Value) != 0:
                for it in Test_Value:
                    if Select_Column_from_Tab(data_columns, it['Test_Item']):
                        if Alter_Column(Station_No + "_test_tab ", it['Test_Item']) is False:
                            AlterRet = False
            # # 重码数据上传判断
            # SQL_same = "SELECT * FROM " + Station_No + "_test_tab WHERE " + code_name + " = '" + Serial_No + "'"
            # data_same = SQL_function3(SQL)
            # if not len(data_same) == 0:
            #     SQL = SQL_same

            if AlterRet:
                Insert_Tag = SQL_function4(SQL)
                if Insert_Tag:
                    print("Insert success")
                else:
                    print("Insert fail")
            else:
                Insert_Tag = False

            if Insert_Tag:
                print("insert--------")
                equipnumgroup = cache.get('EquipNumGroup')
                current_order = cache.get('current_order')
                UpdateTestValue = ""
                Updata_Tag = False
                if len(Test_Value) != 0:
                    # Update_TestValue
                    for i in range(0, len(Test_Value)):
                        temp = Test_Value[i]['Test_Item'] + "='" + Test_Value[i]['Value'] + "'," + Test_Value[i]['Test_Item'] + "_Result='" + Test_Value[i]['Result'] + "'"
                        if i < len(Test_Value) - 1:
                            temp += ","
                        UpdateTestValue += temp
                    SQL = "UPDATE " + Station_No + "_test_tab set " + UpdateTestValue + " WHERE " + code_name + " = '" + Serial_No + "' and  station_no = '" + Station_No + "'"
                    if SQL_function4(SQL):
                        Updata_Tag = True
                    else:
                        Updata_Tag = False
                elif len(Test_Value) == 0:
                    Updata_Tag = True
    # ---------------------------------最后一站/ 测试解果为失败时候 存入product_statistics_tab----------------------
                if Updata_Tag:
                    print("updata------")
                    if Test_Result.upper() == "NG" or Station_No == equipnumgroup[len(equipnumgroup) - 1]:  #当成功到达最后一站的时候/测试结果为失败的时候
                        # 先查询搜索绑定信息，添加到product_statistics_tab时一并插入
                        SQL = "SELECT * FROM qr_confrimation_tab WHERE " + code_name + " = '" + Serial_No + "' AND station_no = '" + Station_No + "'"
                        bind_data = SQL_function3(SQL)
                        print(bind_data)
                        bind_qr_code1 = bind_data[0]['qr_code1']
                        bind_qr_code2 = bind_data[0]['qr_code2']
                        bind_pcba_code1 = bind_data[0]['pcba_code1']
                        bind_pcba_code2 = bind_data[0]['pcba_code2']
                        # product_statistics_tab  为记录sn成功/失败总结果。和型号对应
                        SQL = "INSERT INTO product_statistics_tab (qr_code1,qr_code2,pcba_code1,pcba_code2,test_result,gp_model) Values ('" + bind_qr_code1 + "','" + bind_qr_code2 + "','" + bind_pcba_code1 + "','" + bind_pcba_code2 + "','" + Test_Result + "','" + Gp_Model + "')"
                        if SQL_function4(SQL):
                            if Update_Model_Quantity(Gp_Model, Test_Result):
                                result = "OK"
                            else:
                                result = "NG"
                                msg = "添加型号产量失败"
                        else:
                            result = "NG"
                            msg = "添加产品测试结果失败"

                        # ordersn_tab 记录sn成功/失败总结果。和工单对应
                        # 时间记录2 站台单站记录  产品NG下线/OK下线 记录offline_time 和 result
                        SQL = "UPDATE ordersn_tab SET result = '"+ Test_Result.upper() +"', offline_time = '" + str(
                            t) + "' WHERE " + code_name + " = '" + Serial_No + "'"
                        if not SQL_function4(SQL):
                            result = "NG"
                            msg = "Code:" + Serial_No + "下线更新失败"
                            raise Exception(msg)

                # -------------- 数据库记录时间2 ----------- NG / 最后一站OK  发送产品信息给MOM ------------------------
                        # if not (Test_Result.upper() == "NG" and Station_No == equipnumgroup[len(equipnumgroup) - 1]):

                        SQL = "SELECT * FROM ordersn_tab WHERE " + code_name + " = '" + Serial_No + "'"
                        pro_data = SQL_function3(SQL)
                        if len(pro_data) == 0:
                            result = "NG"
                            msg = "ordersn_tab未查询到Code: " + Serial_No
                            raise Exception(msg)

                        SQL = "SELECT gp_model FROM qr_confrimation_tab WHERE " + code_name + " = '" + Serial_No + "'"
                        conf_data = SQL_function3(SQL)
                        if len(conf_data) == 0:
                            result = "NG"
                            msg = "qr_confrimation_tab未查询到Code: " + Serial_No
                            raise Exception(msg)

                        SQL = "SELECT * FROM planorder_partno_tab WHERE gp_model = '" + conf_data[0]['gp_model'] + "'"
                        partno_data = SQL_function3(SQL)

                        SQL = "SELECT * FROM planorder_tab WHERE order_no = '" + pro_data[0]['order_no'] + "'"
                        order_data = SQL_function3(SQL)

                        sta_delta_t = (t - datetime.datetime.strptime(pro_data[0]['laststation_time'],'%Y-%m-%d %H:%M:%S')).seconds

                        mom_uuid1 = t.strftime('%Y%m%d')
                        mom_uuid2 = ""

                        SQL = "SELECT * FROM qr_confrimation_tab WHERE " + code_name + " = '" + Serial_No + "'"
                        sta_data = SQL_function3(SQL)

                        # 临时多线程表
                        log.info("---------------------- Threads start")
                        threads = []

                        for it in sta_data:
                            mom_uuid2 = Getuuid_num(t)
                            SQL_function4(SQL)
                            if not it['test_time'] == "":
                                sta_delta_t = (datetime.datetime.strptime(it['test_time'],'%Y-%m-%d %H:%M:%S') - datetime.datetime.strptime(it['check_time'],'%Y-%m-%d %H:%M:%S')).seconds
                            else:
                                sta_delta_t = "0"
                                it['test_time'] = it['check_time']
                            SQL = "SELECT * FROM planorder_tab WHERE order_no = '" + current_order + "'"
                            linedata = SQL_function3(SQL)
                            Data2mom = {
                                "UUID": mom_uuid1 + "L" + line_no + mom_uuid2,
                                "STATION_NO": it['station_no'] + "-" + linedata[0]['line_no'],
                                "CODE": "100",
                                # "OFFLINE_TIME": pro_data[0]['offline_time'],
                                "OFFLINE_TIME": it['test_time'],
                                "WORK_TIME": sta_delta_t,
                                "K_PART_NO": "",
                                "K_PART_BATCH": "",
                                "Q_PART_NO": partno_data[0]['Q_PART_NO'],
                                "Q_PART_BATCH": partno_data[0]['Q_PART_BATCH'],
                                "J_PART_NO": "",
                                "J_PART_BATCH": "",
                                "H_PART_NO": partno_data[0]['H_PART_NO'],
                                "H_PART_BATCH": partno_data[0]['H_PART_BATCH'],
                                "F_PART_NO": "",
                                "F_PART_BATCH": "",
                                "L_PART_NO": partno_data[0]['L_PART_NO'],
                                "L_PART_BATCH": partno_data[0]['L_PART_BATCH'],
                                "Z_PART_NO": partno_data[0]['Z_PART_NO'],
                                "Z_PART_BATCH": partno_data[0]['Z_PART_BATCH'],
                                "PCBA_1": it['pcba_code1'],
                                "PCBA_2": it['pcba_code2'],
                                "SN": Serial_No,
                                "PART_NO": order_data[0]['part_no'],
                                "STATION_STATUS": Test_Result.upper(),
                            }
                            # # ------------单站依次顺序发送---------------
                            # # 发送单站状态给MOM ---- 生产过程信息接口
                            # if Planorder_ismomcheck(code_name,Serial_No):
                            #     ret_data = ProcessInfo(Data2mom,Test_Result.upper())
                            #     # 如果发送失败应该保存到本地重传界面 供手动重传
                            #     if ret_data['STATUS'] == "NG":
                            #         result = "NG"
                            #         raise Exception(ret_data['ERRORMSG'])

                            # ------------多线程创建---------------
                            thread = threading.Thread(target=ProcessInfo, args=(Data2mom, Test_Result.upper(),))
                            threads.append(thread)
                            thread.start()
                            log.info("---------------------- Threads create")
                        # ------------多线程执行完---------------
                        # for therad in threads:
                        #     therad.join()
                        log.info("---------------------- Threads success")


                # -------------------------- 发送NG或最终OK 给看板 ------------------------------
                        # 发送产品最终生产信息给看板统计
                        #（只需要发送最后一站/失败的dataup结果，也就是最终产品的生产成败信息）
                        model_tag = cache.get('ModelSetFlag', default=0)
                        current_model = cache.get('current_model')
                        current_order = cache.get('current_order')

                        if model_tag == 1 or model_tag == 0:  # 1 一键下发  2  选择机台下发
                            st_current_model = cache.get('current_model')
                        elif model_tag == 2:
                            SQL = "SELECT st_current_model FROM station_tab WHERE gp_model = '" + current_model + "' and equipment_num = '" + Station_No + "'"
                            data = SQL_function3(SQL)
                            st_current_model = data[0]
                        viewboard_topic = "Msg2Station/ViewBoard"
                        viewboard_data_send = {
                            "Command": "S001",
                            "Station_No": Station_No,
                            "Gp_Model": st_current_model,
                            "ETP": Test_Result.upper()
                        }
                        SendMessage2Station(viewboard_topic, viewboard_data_send)

                # ------------------------ 最后一个产品OK 工单完成成功 ----------------------------
                        SQL = "SELECT * FROM planorder_tab WHERE order_no = '" + current_order + "'"
                        data = SQL_function3(SQL)
                        if len(data) == 0:
                            result = "NG"
                            msg = "未找到工单:" + current_order
                            raise Exception(msg)
                        # 工单已经CLOSE 生产了一个OK ，但不能确定是最后一个（可能最后一个刚进站使得工单Close，此时就有一个OK出站）
                        if Test_Result.upper() == "OK":
                            print("------------------------------------报工")
                            if Planorder_ismomcheck(code_name,Serial_No):
                                mom_ret = PlanOrderReport(code_name, Serial_No, Station_No)
                                if mom_ret is False:
                                    result = "NG"
                                    raise Exception("报工上传MOM失败")
                    else:
                        result = "OK"
                else:
                    result = "NG"
                    msg = "添加产品测试项数据失败"
                    raise Exception(msg)
            else:
                result = "NG"
                msg = "添加产品测试基本数据失败"
                raise Exception(msg)

        except Exception as err:
            # 报工等处理超时失败,产品结果记录为NG
            if Test_Result.upper() == "OK":
                SQL = "UPDATE qr_confrimation_tab set test_result = 'NG' WHERE " + code_name + " = '" + Serial_No + "' and station_no = '" + Station_No + "' and check_result = 'OK'"
                if SQL_function4(SQL):
                    log.info("Code:" + Serial_No + "处理NG,下线更新成功")

            data_send = {
                "Command": "0x04",
                "DataUp_Result":
                    {
                        "Serial_No": Serial_No,
                        "Station_No": Station_No,
                        "Result": result,
                        "Message": str(err)
                    }
            }
            log.info(data_send)
            SendMessage2Station(equip_topic, data_send)
            # lock2.release()
            print("lock2.release")
            log.info("lock2.release")
            return

        data_send = {
            "Command": "0x04",
            "DataUp_Result":
                {
                    "Serial_No": Serial_No,
                    "Station_No": Station_No,
                    "Result": result,
                    "Message": msg
                }
        }
        log.info(data_send)
        print(msg)
        #返回给机台的信息
        SendMessage2Station(equip_topic, data_send)
        # lock2.release()
        print("lock2.release")
        log.info("lock2.release")
        return
    elif command == '0x05':
        print('0x05')
        ReciveOrder_Analysis(data)
        # lock2.release()
        print("lock2.release")
        log.info("lock2.release")
    elif command == '0x06':
        print('0x06')
        ReciveOrder_Analysis(data)
        # lock2.release()
        print("lock2.release")
        log.info("lock2.release")
    elif command == '0x07':
        print('0x07')
        ReciveOrder_Analysis(data)
        # lock2.release()
        print("lock2.release")
        log.info("lock2.release")
    elif command == '0x08':
        print('0x08')
        ReciveOrder_Analysis(data)
        # lock2.release()
        print("lock2.release")
        log.info("lock2.release")
    elif command == '0x09':
        print('0x09')
        ReciveOrder_Analysis(data)
        # lock2.release()
        print("lock2.release")
        log.info("lock2.release")
    elif command == '0x10':                         #托盘绑定   panid和sn绑定到panseries_tab
        try:
            print('0x10')
            Station_No = data['BindPanId']['Station_No']
            Serial_no = data['BindPanId']['Serial_no']
            Pan_Id = data['BindPanId']['Pan_Id']
            Status = data['BindPanId']['Status']

            Tag = False
            msg = ""
            result = "NG"

            SQL = "SELECT panno FROM pan_tab WHERE panno = '" + Pan_Id + "'"
            data = SQL_function(SQL)
            if len(data) == 0:
                msg = "未找到料盘号:" + Pan_Id
                raise Exception(msg)
            elif len(data) > 1:
                msg = "找到多个料盘号:"+ Pan_Id +",请检查"
                raise Exception(msg)
            elif len(data) == 1:
                Tag = True
            if Tag:
                SQL = "SELECT * FROM panseries_tab WHERE panno = '" + Pan_Id + "' and sn = '" + Serial_no + "'"
                data = SQL_function(SQL)
                if len(data) == 0:
                    if Status == 0:
                        SQL = "DELETE FROM panseries_tab WHERE panno = '" + Pan_Id + "'"
                        if SQL_function2(SQL) is False:
                            msg = "SQL清空panno:" + Pan_Id + "失败"
                    SQL = "INSERT INTO panseries_tab (panno,sn) Values ('" + Pan_Id + "','" + Serial_no + "')"
                    if SQL_function2(SQL):
                        result = "OK"
                        msg = "SQL绑定写入成功"
                    else:
                        msg = "SQL绑定写入失败"
                        raise Exception(msg)
                else:
                    msg = "已经存在该绑定，请检查"
                    raise Exception(msg)
        except Exception as err:
            data_send = {
                "Command": "0x10",
                "BindPanId_Result":
                    {
                        "Serial_no": Serial_no,
                        "Pan_Id": Pan_Id,
                        "Result": result,
                        "Message": str(err)
                    }
            }
            SendMessage2Station(equip_topic, data_send)
            # lock2.release()
            print("lock2.release")
            log.info("lock2.release")
            return
        data_send = {
            "Command": "0x10",
            "BindPanId_Result":
                {
                    "Serial_no": Serial_no,
                    "Pan_Id": Pan_Id,
                    "Result": result,
                    "Message": msg
                }
        }
        SendMessage2Station(equip_topic, data_send)
        # lock2.release()
        print("lock2.release")
        log.info("lock2.release")
        return
    elif command == '0x11':                            # 获取条码绑定的Sensor
        try:
            print('0x11')
            Station_No = data['GetSensor']['Station_No']
            Serial_No = data['GetSensor']['Serial_No']
            current_model = cache.get('current_model')

            msg = ""
            result = "NG"
            SensorCode = ""

            SQL = "SELECT pcba_code1 FROM qr_bind_tab WHERE qr_code ='" + Serial_No + "' and gp_model='" + current_model + "'"
            data = SQL_function(SQL)
            if len(data) == 0:
                msg = "获取Sensor失败"
            elif len(data) > 1:
                msg = "获取多个数据，请检查"
            elif len(data) == 1:
                result = "OK"
                msg = "获取Sensor成功"
                SensorCode = data[0]['pcba_code1']
        except Exception as err:
            data_send = {
                "Command": "0x11",
                "GetSensor_Result":
                    {
                        "Serial_No": Serial_No,
                        "Sensor_No": "",
                        "Result": "NG",
                        "Message": str(err)
                    }
            }
            SendMessage2Station(equip_topic, data_send)
            # lock2.release()
            print("lock2.release")
            log.info("lock2.release")
            return
        data_send = {
            "Command": "0x11",
            "GetSensor_Result":
                {
                    "Serial_No": Serial_No,
                    "Sensor_No": SensorCode,
                    "Result": result,
                    "Message": msg
                }
        }
        SendMessage2Station(equip_topic, data_send)
        # lock2.release()
        print("lock2.release")
        log.info("lock2.release")
        return
    elif command == '0x12':                     #查询料盘绑定的产品信息   panid 查 sn
        try:
            print('0x12')
            PanId = data['GetPanBind']['PanId']
            Station_No = data['GetPanBind']['Station_No']
            Sn_List = []

            result = "NG"
            msg = ""
            Tag = False

            SQL = "SELECT panno FROM pan_tab WHERE panno = '" + PanId + "'"
            data = SQL_function(SQL)
            if len(data) == 0:
                msg = "未找到料盘号:" + PanId
                raise Exception(msg)
            elif len(data) > 1:
                msg = "找到多个料盘号:" + PanId + "，请检查"
                raise Exception(msg)
            elif len(data) == 1:
                Tag = True
            if Tag:
                SQL = "SELECT sn FROM panseries_tab WHERE panno = '" + PanId + "'"
                data = SQL_function(SQL)
                if len(data) == 0:
                    msg = "未找到绑定的SN信息"
                    raise Exception(msg)
                else:
                    for it in data:
                        Sn_List.append(it['sn'])
                    result = "OK"


        except Exception as err:
            data_send = {
                "Command": "0x12",
                "GetPanBind_Result":
                    {
                        "PanId": PanId,
                        "Sn_List": [],
                        "Result": result,
                        "Message": str(err)
                    }
            }
            SendMessage2Station(equip_topic, data_send)
            # lock2.release()
            print("lock2.release")
            log.info("lock2.release")
            return
        data_send = {
            "Command": "0x12",
            "GetPanBind_Result":
                {
                    "PanId": PanId,
                    "Sn_List": Sn_List,
                    "Result": result,
                    "Message": msg
                }
        }
        SendMessage2Station(equip_topic, data_send)
        # lock2.release()
        print("lock2.release")
        log.info("lock2.release")
        return

    # 下发Mes选项
    elif command == '0x13':
        print('0x13')
        ReciveOrder_Analysis(data)
        # lock2.release()
        print("lock2.release")
        log.info("lock2.release")
    # 故障上传
    elif command == '0x14':
        try:
            msg = ""
            result = "NG"
            print('0x14')
            #发送给看板viewboard
            viewboard_topic = "Msg2Station/ViewBoard"
            STNO = data['Station_No']
            msg = data['Message']
            viewboard_data_send = {
                "Command": "S002",
                "Station_No": STNO,
                "Status": 2,                        #0正常  1断开  2故障
                "Message": msg
            }

            SendMessage2Station(viewboard_topic, viewboard_data_send)

            result = "OK"

            # #保存时间
            # Time_Record(data['Station_No'], 3)
        except:
            data_send = {
                "Command": "0x14",
                "Station_No": data['Station_No'],
                "Result": result
            }
            SendMessage2Station(equip_topic, data_send)
            # lock2.release()
            print("lock2.release")
            log.info("lock2.release")
            return

        data_send = {
            "Command": "0x14",
            "Station_No": data['Station_No'],
            "Result": result
        }
        SendMessage2Station(equip_topic, data_send)
        # lock2.release()
        print("lock2.release")
        log.info("lock2.release")
        return
    elif command == '0x15':         #治具检验
        print('0x15')
        ReciveOrder_Analysis(data)
        # lock2.release()
        print("lock2.release")
        log.info("lock2.release")
    elif command == '0x16':         #点检(未使用，留存)
        print('0x16')
        ReciveOrder_Analysis(data)
        # lock2.release()
        print("lock2.release")
        log.info("lock2.release")
    elif command == '0x17':         #设备状态 0正常 1停机 2报警
        try:
            print('0x17')
            log.info("0x17")
            Status = int(data['Status'])
            STNO = data['Station_No']

            device_class = cache.get('DeviceClass')
            for it in device_class:
                if it["EquipNumber"] == STNO:
                    if not it["EquipStatus"]:
                        it["EquipStatus"] = True
                        cache.set('DeviceClass', device_class)
                        break

            st_tag = True
            equipnumgroup = cache.get('EquipNumGroup')
            for it in equipnumgroup:
                if str(it) == str(STNO):
                    st_tag = False

            # 待添加 未完成 、、、换型之后用不到的机器也得获取他的状态并记录为stop时间、、、目前为了测试简化数据先不处理这部分
            if st_tag:
                print(str(STNO) + "机台不是当前型号下的设备，记录进停机时间")
                log.info(str(STNO) + "机台不是当前型号下的设备，记录进停机时间")
                Time_Record_StopOnline(STNO)

                # 退出时候不要忘记lock锁释放
                # lock2.release()
                print("lock2.release")
                log.info("lock2.release")
                return

            log.info(str(STNO) + "---->" + str(Status) + "   设备状态 0正常 1停机 2报警")

            if Status == 0:  # 变正常
                equip_time = cache.get('EquipTime', default=None)
                equip_status = cache.get('Equip_Status', default=None)
                if equip_time['Status'] == 3:  # 如果之前是报警，现在要变正常，修改报警设备的信息

                    st_name = ""
                    # 记录到缓存中设备状态位，首页会自动更新
                    device_class = cache.get('DeviceClass')
                    for it in device_class:
                        if it['EquipNumber'] == STNO:
                            it['EquipError'] = False
                            st_name = it['EquipName']
                    Cache_writer('DeviceClass', device_class, None)

                    # 发送给看板
                    viewboard_topic = "Msg2Station/ViewBoard"
                    viewboard_data_send = {
                        "Command": "S002",
                        "Station_No": STNO,
                        "Station_Name": st_name,
                        "Status": 0,  # 0正常  1断开  2故障
                        "Message": ""
                    }
                    # viewboard_data_send = str(json.dumps(viewboard_data_send))
                    SendMessage2Station(viewboard_topic, viewboard_data_send)

                    # 先改设备状态，时间记录内部需要调用设备状态查看是否全部完成，方便修改时间状态
                    for item in equip_status:
                        if item['EquipNumber'] == STNO:
                            item['EquipOrder'] = "Start"
                            item['EquipResult'] = "OK"
                    Cache_writer('Equip_Status', equip_status, None)
                    if cache.get('ModelSetFlag', default=0) == 1 or cache.get('ModelSetFlag',
                                                                              default=0) == 0:  # 1一键 2 选择机台
                        Time_Record(STNO, 0, False)
                    elif cache.get('ModelSetFlag', default=0) == 2:
                        Time_Record(STNO, 0, True)

                elif equip_time['Status'] == 2:  # 如果之前是stop，现在要变正常，修改stop设备的信息
                    # 先改设备状态，时间记录内部需要调用设备状态查看是否全部完成，方便修改时间状态
                    for item in equip_status:
                        if item['EquipNumber'] == STNO:
                            item['EquipOrder'] = "Start"
                            item['EquipResult'] = "OK"
                    Cache_writer('Equip_Status', equip_status, None)
                    if cache.get('ModelSetFlag', default=0) == 1 or cache.get('ModelSetFlag',
                                                                              default=0) == 0:  # 1 一键 2 选择机台
                        Time_Record(STNO, 0, False)
                    elif cache.get('ModelSetFlag', default=0) == 2:
                        Time_Record(STNO, 0, True)

                elif equip_time['Status'] == 1:  # 如果之前是remodel(点检)，现在要变正常，修改stop设备的信息
                    # 未完成 待补充
                    for item in equip_status:
                        if item['EquipNumber'] == STNO:
                            item['EquipOrder'] = "Start"
                            item['EquipResult'] = "OK"
                    Cache_writer('Equip_Status', equip_status, None)
                    if cache.get('ModelSetFlag', default=0) == 1 or cache.get('ModelSetFlag',
                                                                              default=0) == 0:  # 1 一键 2 选择机台
                        Time_Record(STNO, 0, False)
                    elif cache.get('ModelSetFlag', default=0) == 2:
                        Time_Record(STNO, 0, True)

                elif equip_time['Status'] == 0:  # 如果是正常/点检    变正常
                    # 未完成 待补充
                    for item in equip_status:
                        if item['EquipNumber'] == STNO:
                            # if item['EquipOrder'].upper() == "CHECKDEVICE" :
                            item['EquipOrder'] = "Start"
                            item['EquipResult'] = "OK"
                    Cache_writer('Equip_Status', equip_status, None)

                    if cache.get('ModelSetFlag', default=0) == 1 or cache.get('ModelSetFlag',
                                                                              default=0) == 0:  # 1 一键 2 选择机台
                        # 在此处对机台进行区分，只有第一个机台 在点检--开始后 进行starttime的记录，后续的不记录
                        # 8/11 更新 点检逻辑为换型后只点检一次，利用心跳来记录产线工作时间，此时以第一台机器为锚点修改全线机台工作时间，其余机器不单独记录
                        if STNO == "ST01":  # 检查当前工站第一个吗
                            Time_Record(STNO, 0, False)
                        print(str(STNO) + "正常--正常")
                        log.info(str(STNO) + "正常--正常")
                    elif cache.get('ModelSetFlag', default=0) == 2:
                        # 单机换型所用的点检表可能不一样，生产的型号可能是新的工单下的
                        # 未完成
                        # Time_Record(STNO, 0, True)
                        print(".....")

            elif Status == 1:  # 变停机

                equip_time = cache.get('EquipTime', default=None)
                equip_time_st = cache.get('EquipTimeST', default=None)
                equip_status = cache.get('Equip_Status', default=None)

                st_name = ""
                # 记录到缓存中设备状态位，首页会自动更新
                device_class = cache.get('DeviceClass')
                for it in device_class:
                    if it['EquipNumber'] == STNO:
                        it['EquipError'] = False
                        st_name = it['EquipName']
                Cache_writer('DeviceClass', device_class, None)
                # 发送给看板
                viewboard_topic = "Msg2Station/ViewBoard"
                viewboard_data_send = {
                    "Command": "S002",
                    "Station_No": STNO,
                    "Station_Name": st_name,
                    "Status": 0,  # 0正常  1断开  2故障
                    "Message": ""
                }
                SendMessage2Station(viewboard_topic, viewboard_data_send)
                # for item in equip_status:
                #     if item['EquipNumber'] == STNO:
                #         item['EquipOrder'] = "STOP"
                #         item['EquipResult'] = "OK"
                # Cache_writer('Equip_Status', equip_status, None)

                if cache.get('ModelSetFlag', default=0) == 1 or cache.get('ModelSetFlag',
                                                                          default=0) == 0:  # 1 一键 2 选择机台
                    if equip_time['Status'] == 1 or equip_time['Status'] == 2:
                        print("全线:当前状态为remodel/stop,不修改")
                        log.info("全线:当前状态为remodel/stop,不修改")
                    elif equip_time['Status'] == 0:  # 0正常生产 变1停机， 可以是start--remodel  start--stop
                        for item in equip_status:
                            if item['EquipNumber'] == STNO:
                                if item['EquipOrder'].upper() == "REMODEL":
                                    item['EquipOrder'] = "REMODEL"
                                else:
                                    item['EquipOrder'] = "STOP"
                                item['EquipResult'] = "OK"
                                # Time_Record(STNO, 2, False)
                                print("全线:正常--STOP/REMODEL:" + str(STNO))
                                log.info("全线:正常--STOP/REMODEL:" + str(STNO))
                        Cache_writer('Equip_Status', equip_status, None)  # 先保存状态再记录时间
                        Time_Record(STNO, 2, False)

                    elif equip_time['Status'] == 3:
                        for item in equip_status:
                            if item['EquipNumber'] == STNO:
                                item['EquipOrder'] = "STOP"
                                item['EquipResult'] = "OK"
                                log.info("全线:ERROR--STOP:" + str(STNO))
                        Cache_writer('Equip_Status', equip_status, None)  # 先保存状态再记录时间
                        Time_Record(STNO, 2, False)

                elif cache.get('ModelSetFlag', default=0) == 2:
                    for it in equip_time_st:
                        if it['STNO'] == STNO:
                            if it['Status'] == 1 or it['Status'] == 2:
                                print("单机:当前状态为remodel/stop，停机不修改属性")
                            elif it['Status'] == 0:
                                for item in equip_status:
                                    if item['EquipNumber'] == STNO:
                                        item['EquipOrder'] = "STOP"
                                        item['EquipResult'] = "OK"
                                        print("单机:正常--STOP:" + str(STNO))
                                        log.info("单机:正常--STOP:" + str(STNO))
                                Cache_writer('Equip_Status', equip_status, None)
                                Time_Record(STNO, 2, True)
                            elif equip_time['Status'] == 3:
                                print("单机:当前状态为error，不能修改为stop，请检查")
                                log.info("单机:当前状态为error，不能修改为stop，请检查")

            elif Status == 2:  # 变报警
                st_name = ""
                # 记录到缓存中设备状态位，首页会自动更新
                device_class = cache.get('DeviceClass')
                equip_status = cache.get('Equip_Status', default=None)
                for it in device_class:
                    if it['EquipNumber'] == STNO:
                        it['EquipError'] = True
                        st_name = it['EquipName']
                Cache_writer('DeviceClass', device_class, None)

                # 发送给看板

                viewboard_topic = "Msg2Station/ViewBoard"
                viewboard_data_send = {
                    "Command": "S002",
                    "Station_No": STNO,
                    "Station_Name": st_name,
                    "Status": 2,  # 0正常  1断开  2故障
                    "Message": ""
                }
                # viewboard_data_send = str(json.dumps(viewboard_data_send))
                SendMessage2Station(viewboard_topic, viewboard_data_send)

                # 修改缓存中设备状态信息
                for item in equip_status:
                    if item['EquipNumber'] == STNO:
                        item['EquipOrder'] = "Error"
                        item['EquipResult'] = "NA"
                Cache_writer('Equip_Status', equip_status, None)

                equip_time = cache.get('EquipTime', default=None)
                equip_time_st = cache.get('EquipTimeST', default=None)
                equip_status = cache.get('Equip_Status', default=None)

                if cache.get('ModelSetFlag', default=0) == 1 or cache.get('ModelSetFlag',
                                                                          default=0) == 0:  # 1 一键 2 选择机台
                    Time_Record(STNO, 3, False)
                elif cache.get('ModelSetFlag', default=0) == 2:  # 2 选择机台
                    Time_Record(STNO, 3, True)
                    # equip_time['Status'] = 3
                    # temptag = True
                    # for item in equip_time_st:
                    #     if item['STNO'] == STNO:
                    #         temptag = False
                    #         item['ErrorTime'] = t
                    #         item['Status'] = 3
                    # if temptag:
                    #     print(STNO + "报警信息修改失败,未在equip_time_st找到对应机台")
                    #     equip_time_st.append({"StartTime": t, "ErrorTime": t, "EndTime": t, "Status": 1, "STNO": STNO})
                    #     print('添加:' + str({"StartTime": t, "ErrorTime": t, "EndTime": t, "Status": 1, "STNO": STNO}))
                    # Cache_writer('EquipTime', equip_time, None)
                    # Cache_writer('EquipTimeST', equip_time_st, None)

            # ReciveOrder_Analysis(data)
            # lock2.release()
            print("lock2.release")
            log.info("lock2.release")
        except Exception as err:
            # lock2.release()
            print("lock2.release")
            log.info("lock2.release")
            print(err)
    elif command == '0x18':  #AGV 叫料上传MOM  Type 1 叫料 3 取料
        try:
            print('0x18')
            log.info("0x18")
            current_model = cache.get('current_model')
            Num = data['Num']
            Type = data['Status']
            STPO = data['Station_Point']
            STNO = data['Station_No']
            t = datetime.datetime.now()

            SQL = "SELECT st_current_model FROM station_tab WHERE equipment_num = '" + STNO + "' and gp_model = '" + current_model + "'"
            data = SQL_function3(SQL)
            st_current_model =  data[0]['st_current_model']

            # 获取当前工单号对应的料号
            SQL = "SELECT * FROM mom_setting"
            data = SQL_function3(SQL)
            SQL = "SELECT * FROM planorder_partno_stpo_tab WHERE station_point = '" + STPO + "' AND gp_model = '" + st_current_model + "'"
            stpo_data = SQL_function3(SQL)
            # part_no_name = ['Q_PART_NO','H_PART_NO','P_PART_NO','J_PART_NO','ZC_PART_NO']
            # material_no = ""
            # for it in part_no_name:
            #     if not stpo_data[0][it] == "":
            #         material_no = stpo_data[0][it]
            part_no_name = stpo_data[0]['PART_NO_NAME']
            SQL = "SELECT " + part_no_name + " FROM planorder_partno_tab WHERE gp_model = '" + st_current_model + "'"
            partno_data = SQL_function3(SQL)
            material_no = partno_data[0][part_no_name]

            if stpo_data[0]['agv_send'].upper() == 'TRUE':               # 如果为上料
                # 组装信息
                Data2Mom = {
                    "REQ_QTY": str(Num),
                    "LINE_NO": data[0]['LINENO'],
                    "SHIFT_NO": "0",
                    "POINT_NO": STPO,
                    "PRODUCT_DATE": t.strftime('%Y-%m-%d'),
                    # "MATERIAL_NO": "37760003990A0A00"
                    "MATERIAL_NO":material_no
                }
                print(Data2Mom)
                # 发送叫料信息给MOM
                ret = SendMessage2MOM(Data2Mom, url['CreateSheetPull'])
                log.info("--------ret")
                log.info(ret)
                ret = json.loads(ret)
                print(ret['STATUS'])
                # 返回信息给叫料的机台
                data = {
                    "Command": "0x18",
                    "Station_Point": STPO,
                    "Result": "NG"
                }
                if ret['STATUS'] == "OK":
                    data['Result'] = "OK"
                    # 统计叫料数量
                    Data2Mom['REQ_QTY']
                    Data2Mom['MATERIAL_NO']
                print("sta")
                print(data)
                print(STNO)
                SendMessage2Station("Msg2Station/" + STNO, data)

            elif stpo_data[0]['agv_get'].upper() == 'TRUE':               # 如果为下料
                Data2Mom = {
                    "LINE_NO": data[0]['LINENO'],
                    "POINT_NO": STPO,
                    "PARTNO": material_no,
                }
                print(Data2Mom)
                ret = SendMessage2MOM(Data2Mom, url['CallAGVOffline'])
                ret = json.loads(ret)
                # 返回信息给的机台
                data = {
                    "Command": "0x18",
                    "Station_Point": STPO,
                    "Result": "NG"
                }
                if ret['STATUS'] == "OK":
                    data['Result'] = "OK"

                SendMessage2Station("Msg2Station/" + STNO, data)

            # lock2.release()
            print("lock2.release")
            log.info("lock2.release")
        except Exception as err:
            # lock2.release()
            print("lock2.release")
            log.info("lock2.release")
            print("------------------------------")
            print(err)
            data = {
                "Command": "0x18",
                "Station_Point": STPO,
                "Result": "NG"
            }
            SendMessage2Station("Msg2Station/" + STNO, data)


    # elif command == '0x18':  #AGV 叫料上传MOM  Type 1 叫料 3 取料
    #     try:
    #         print('0x18')
    #         log.info("0x18")
    #         Num = data['Num']
    #         Type = data['Status']
    #         STPO = data['Station_Point']
    #         STNO = data['Station_No']
    #         t = datetime.datetime.now()
    #         # 获取当前工单号对应的料号
    #         SQL = "SELECT * FROM mom_setting"
    #         data = SQL_function3(SQL)
    #         data = {
    #             "Command": "0x18",
    #             "Station_Point": STPO,
    #             "Result": "OK"
    #         }
    #         SendMessage2Station("Msg2Station/" + STNO, data)
    #         raise Exception("OK")
    #
    #         if Type == '1':
    #             # 组装信息
    #             Data2Mom = {
    #                 "REQ_QTY": str(Num),
    #                 "LINE_NO": data[0]['LINENO'],
    #                 "SHIFT_NO": "0",
    #                 "POINT_NO": STPO,
    #                 "PRODUCT_DATE": t.strftime('%Y-%m-%d'),
    #                 "MATERIAL_NO": "37760003990A0A00"
    #             }
    #             print(Data2Mom)
    #             # 发送叫料信息给MOM
    #             ret = SendMessage2MOM(Data2Mom, url['CreateSheetPull'])
    #             print(ret)
    #             ret = json.loads(ret)
    #             print(ret['STATUS'])
    #             # 返回信息给叫料的机台
    #             data = {
    #                 "Command": "0x18",
    #                 "Station_Point": STPO,
    #                 "Result": "NG"
    #             }
    #             if ret['STATUS'] == "OK":
    #                 data['Result'] = "OK"
    #                 # 统计叫料数量
    #                 Data2Mom['REQ_QTY']
    #                 Data2Mom['MATERIAL_NO']
    #             print("sta")
    #             print(data)
    #             print(STNO)
    #             SendMessage2Station("Msg2Station/" + STNO, data)
    #
    #         elif Type == "3":
    #             Data2Mom = {
    #                 "LINE_NO": data[0]['LINENO'],
    #                 "POINT_NO": STPO,
    #                 "PART_NO": "",
    #             }
    #             print(Data2Mom)
    #             ret = SendMessage2MOM(Data2Mom, url['CallAGVOffline'])
    #
    #             # 返回信息给的机台
    #             data = {
    #                 "Command": "0x18",
    #                 "Station_Point": STPO,
    #                 "Result": "NG"
    #             }
    #             if ret['STATUS'] == "OK":
    #                 data['Result'] = "OK"
    #
    #             SendMessage2Station("Msg2Station/" + STNO, data)
    #
    #         # lock2.release()
    #         print("lock2.release")
    #         log.info("lock2.release")
    #     except Exception as err:
    #         # lock2.release()
    #         print("lock2.release")
    #         log.info("lock2.release")
    #         print("------------------------------")
    #         print(err)

    elif command == '0x19':  # 0镭雕 SN  1 扫码
        try:
            print('0x19')
            log.info("0x19")

            SN = ""
            msg = ""
            t = datetime.datetime.now()
            current_order = cache.get('current_order')
            current_model = cache.get('current_model')
            STNO = data['Station_No']

            filepath = GetFilePath("SoftWare.ini")
            conf = ConfigParser()  # 需要实例化一个ConfigParser对象
            conf.read(filepath)  # 需要添加上config.ini的路径，不需要open打开，直接给文件路径就读取，也可以指定encoding='utf-8'
            line_no = conf['CommonUse']['line_no']
            sn_head = conf['CommonUse']['sn_head']

            # 先查看当前型号是否是镭雕上料的
            SQL = "SELECT * FROM model_tab WHERE gp_model = '" + current_model + "'"
            data = SQL_function3(SQL)
            if data[0]['sn_way'] == "":
                msg = "当前型号未找到上料方式,请检查"
                raise Exception(msg)
            elif data[0]['sn_way'] == "1":
                msg = "当前为扫码上料，请换型到镭雕上料型号"
                raise Exception(msg)

            SQL = "SELECT * FROM planorder_tab WHERE order_no = '" + current_order + "'"
            data = SQL_function3(SQL)
            if len(data) == 0:
                msg = "当前订单:" + current_order + " 未找到"
                raise Exception(msg)
            if data[0]['status'].upper() == "CLOSE":
                msg = "当前工单已关闭"
                raise Exception(msg)
            # 生产一个新的sn码提供使用
            x = Getsn_num(t)
            part_no = data[0]['part_no']
            year = str(t.year)[2:4]
            month = str(t.month)
            day = str(t.day)
            SN = part_no + line_no + year + month.zfill(2) + day.zfill(2) + str(x).zfill(4)
            print(SN)
            if not sn_head == "":
                SN = sn_head + SN

            msg = "生成SN码成功"
            data = {
                "Command": "0x19",
                "Station_No": STNO,
                "Sn": SN,
                "Message": msg
            }
            SendMessage2Station("Msg2Station/" + STNO, data)
        except Exception as err:
            print(err)
            data = {
                "Command": "0x19",
                "Station_No": STNO,
                "Sn": "",
                "Message": str(err)
            }
            SendMessage2Station("Msg2Station/" + STNO, data)

        # lock2.release()
        print("lock2.release")
        log.info("lock2.release")
    elif command == '0x21':  # 胶水物料号上传校验接口      MES胶水码存放在ini文件中和内存中，线体校验结果，校验时间存放内存中
        try:
            t = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            JS_PART_NO = data['JS_PART_NO']
            STNO = data['Station_No']
            backdata = {
                "Command": "0x21",
                "Result":"NG",
            }
            # 先对比本地维护的胶水物料号和机台上传的胶水物料号
            Getjs_part_no_msg()
            if JS_PART_NO == "":
                msg = "点胶站胶水码为空"
                Cache_writer("JS_PART_NO_FLAG", "false")
                Cache_writer("JS_PART_NO_MSG", msg)
                Cache_writer("JS_PART_NO_TIME", str(t))
                raise Exception(msg)
            if not JS_PART_NO == cache.get('JS_PART_NO'):
                msg = "点胶站上传胶水码MES不匹配"
                Cache_writer("JS_PART_NO_FLAG", "false")
                Cache_writer("JS_PART_NO_MSG", msg)
                Cache_writer("JS_PART_NO_TIME", str(t))
                raise Exception(msg)

            # 与MOM校验本机胶水号
            Data2mom = {
                "NO": JS_PART_NO,
            }
            Back_Data = SendMessage2MOM(Data2mom, url['GlueUseConfirm'])
            # Back_Data = {
            #     "STATUS": "OK",
            #     "ERRORMSG": "过期"
            # }
            Back_Data = json.loads(json.dumps(eval(str(Back_Data))))
            if Back_Data['STATUS'] == "NG":
                Cache_writer("JS_PART_NO_FLAG", "false")
                Cache_writer("JS_PART_NO_MSG", Back_Data['ERRORMSG'])
                Cache_writer("JS_PART_NO_TIME", str(t))
                raise Exception(Back_Data['ERRORMSG'])
            elif Back_Data['STATUS'] == "OK":
                # 修改software.ini 文件中的数据,和内存中的数据
                Setjs_part_no_msg(JS_PART_NO,"true",str(t))
                Cache_writer("JS_PART_NO_FLAG","true")
                Cache_writer("JS_PART_NO_MSG", "校验成功")
                Cache_writer("JS_PART_NO_TIME", str(t))
            backdata['Result'] = "OK"
        except Exception as err:
            log.info("0x21 ERROR:" + str(err))
        SendMessage2Station("Msg2Station/" + STNO, backdata)

    else:
        # lock2.release()
        print("lock2.release")
        log.info("lock2.release")
        print("未找到command对应格式")

    return


def TConn(client_Id, client_Ip, client_Port, link):
    print(">>>>>TConn")
    log.info(">>>>>TConn")
    # 上锁
    global lock
    warn_msg = ""
    lock.acquire()
    log.info("lock.acquire")
    try:
        equip_connect = cache.get('EquipConnect', default=None)
        device_class = cache.get('DeviceClass', default=None)
        log.info("equip_connect:" + str(equip_connect))
        log.info("device_class:" + str(device_class))
        if equip_connect is None:
            equip_connect = {}
        if device_class is None:
            warn_msg = '[msg_operation] DeviceClass is None'
            print(warn_msg)
            raise Exception(warn_msg)
        print(equip_connect)
        print(device_class)

        SQL = "SELECT equipment_num, equipment_name FROM equipment_tab where equipment_ip = '" + client_Ip + "'"
        data = SQL_function3(SQL)
        sta_num = -1
        if link:
            sta_num = 0
        else:
            sta_num = 1

        if len(data) == 0:
            print("未在设备表equipment_tab中找到该连接的设备信息")
            log.info("未在设备表equipment_tab中找到该连接的设备信息")
        elif len(data) == 1:
            # 发送给看板viewboard
            viewboard_topic = "Msg2Station/ViewBoard"
            viewboard_data_send = {
                "Command": "S002",
                "Station_No": data[0]['equipment_num'],
                "Station_Name": data[0]['equipment_name'],
                "Status": sta_num,  # 0正常  1断开  2故障  3上传MOM失败
                "Message": ""
            }
            # viewboard_data_send = str(json.dumps(viewboard_data_send))
            SendMessage2Station(viewboard_topic, viewboard_data_send)
        else:
            print("在设备表equipment_tab中找到多个设备信息，请检查")
            log.info("在设备表equipment_tab中找到多个设备信息，请检查")

        if equip_connect is not None:
            if link:
                equip_connect[str(client_Id)] = str(client_Ip) + ':' + str(client_Port)
                Cache_writer('EquipConnect', equip_connect, None)
            else:
                equip_connect.pop(str(client_Id))
                Cache_writer('EquipConnect', equip_connect, None)
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
                Cache_writer('DeviceClass', device_class, None)
            else:
                warn_msg = '[msg_operation] Can not find same device in DeviceClass 没有在当前型号下的机台找到相同IP的设备'
                print(warn_msg)
                raise Exception(warn_msg)
        else:
            warn_msg = '[msg_operation] DeviceClass is None ,can not change'
            print(warn_msg)
            raise Exception(warn_msg)
        print(device_class)

        lock.release()
        log.info("lock.release")
        log.info("--------" + str(client_Ip) + "状态" + str(link) + "更新成功")
        log.info("equip_connect:"  + str(equip_connect))
        log.info("device_class:"  + str(device_class))
    except Exception as err:
        lock.release()
        log.info("lock.release")
        log.info(str(err))
# 接收MQTT消息
def Recv(client_Ip, data, topic):
    try:
        # thread_name("Recv")
        # future = threadPool.submit(TRecv, client_Ip, data, topic)
        # TRecv(client_Ip, data, topic)
        t1 = threading.Thread(target=TRecv, args=(client_Ip, data, topic,))
        t1.start()
        return
    except Exception as err:
        log.info("Recv_err:" + str(err))

# 建立、断开了MQTT连接
def Conn(client_Id, client_Ip, client_Port, link):
    log.info(">>>>>>Conn")
    # t = Thread(target=TConn(client_Id, client_Ip, client_Port, link))
    # t.start()
    t1 = threading.Thread(target=TConn, args=(client_Id, client_Ip, client_Port, link,))
    t1.start()
    # future = threadPool.submit(TConn, client_Id, client_Ip, client_Port, link)
    return

# ----------------------------------------工单相关处理函数---------------------------------------------
# 添加SN到  某订单
# def AddOrderSN(order_no, num):         # order_no工单号    num要添加新的SN的个数
#     # 获取当前SN总生成个数，继续生成num个sn
#     num = int(num)
#     print(type(num))
#     SN_Counter = 0
#     sn = ""
#
#     SQL = "SELECT num_real FROM planorder_tab WHERE order_no = '" + order_no + "'"
#     data = SQL_function3(SQL)
#     SN_Counter = int (data[0]['num_real'])
#
#     SQL = "UPDATE planorder_tab SET num_real = '" + str(SN_Counter + num) + "' WHERE order_no = '" + order_no + "'"
#     if SQL_function4(SQL):
#         print("更新num_real 成功")
#
#     # 自动生成工单号下的产品sn
#     for i in range(int(num)):
#         # 未完成待补充  sn生成格式未确定
#         sn = order_no + "N" + str(SN_Counter + i)
#         SQL = "INSERT INTO ordersn_tab (order_no,sn) VALUES ('" + order_no + "','" + sn + "')"
#         print(SQL)
#         if not SQL_function4(SQL):
#             print("SQL执行失败: " + SQL)
#             return ("False")
#         elif num == 1:
#             return sn

# 生产计划获取接口   验证--请求--保存--上报--返回
def GetPlanOrder(productdate):
    try:
        t = datetime.datetime.now()
        current_model = cache.get('current_model')
        current_order = cache.get('current_order')
        # productdate = str(datetime.datetime.strptime(productdate, '%Y-%m-%d'))
        # 检查旧工单是否关闭
        if not current_order == "":
            SQL = "SELECT * FROM planorder_tab WHERE order_no = '" + current_order + "'"
            data = SQL_function3(SQL)
            if len(data) == 0:
                msg = "未查询到当前工单,请检查"
                raise Exception(msg)
            # if not data[0]['status'].upper() == "CLOSE":
            #     msg = "当前工单未完成,无法请求新的工单,请检查"
            #     raise Exception(msg)
        SQL = "SELECT * FROM mom_setting"
        data = SQL_function3(SQL)
        # 请求工单接口
        Data2mom = {
            "FACTORYCODE": data[0]['FACTORYCODE'],
            "LINENO": data[0]['LINENO'],
            "PRODUCTDATE": productdate,
            "SHIFTNO": "0",
        }
        Back_Data = SendMessage2MOM(Data2mom, url['GetPlanOrder'])
        Back_Data = json.loads(Back_Data)
        if Back_Data['STATUS'] == "NG" or len(Back_Data['Data']) == 0:
            raise Exception(Back_Data['ERRORMSG'])

        # # 将当前摄像头工单切换为新工单，保存到本地ini文件中
        # current_order = Back_Data['Data'][0]['ORDERNO']
        # Cache_writer('current_order', current_order, None)
        # filepath = GetFilePath("SoftWare.ini")
        # conf = ConfigParser()  # 需要实例化一个ConfigParser对象
        # conf.read(filepath)  # 需要添加上config.ini的路径，不需要open打开，直接给文件路径就读取，也可以指定encoding='utf-8'
        # print(conf['CommonUse']['CurrentOrder'])
        # conf.set('CommonUse', 'CurrentOrder', str(current_order))
        # with open(filepath, 'w', encoding='utf-8') as f:
        #     conf.write(f)
        # print(conf['CommonUse']['CurrentOrder'])

        # 2024/4/1 新增了part_name描述当前工单的生产物料型号， 用闲置的gp_model 位置存储
        # 对获取的摄像头订单保存到数据库
        retdata = PlanOrderRecord(Back_Data['Data'][0]['FACTORYCODE'], Back_Data['Data'][0]['ORDERNO'], Back_Data['Data'][0]['PARTNO'],
                        Back_Data['Data'][0]['SOFT_VER'], Back_Data['Data'][0]['NUM'], Back_Data['Data'][0]['LINENO'],
                        Back_Data['Data'][0]['SHIFTNO'], Back_Data['Data'][0]['PARTNAME'], 0)
        if retdata['STATUS'] == "NG":
            raise Exception("请求工单成功保存失败")
        # 上报MOM收到的单号信息
        back_data = PlanOrderConfirm(Back_Data['Data'][0]['FACTORYCODE'], Back_Data['Data'][0]['LINENO'], Back_Data['Data'][0]['ORDERNO'])
        back_data = json.loads(back_data)
        print(back_data['result'])
        if back_data['result'] == "NG":
            raise Exception(back_data['msg'])
        ret_data = {
            "result": "True",
            "msg": back_data['msg']
        }
        return json.dumps(ret_data)

    except Exception as err:
        # 请求工单、保存工单、回传工单 失败导致。保存请求，消息发送至看板。
        print(err)
        log.info(err)
        ret_data = {
            "result": "False",
            "msg": str(err)
        }

        return json.dumps(ret_data)

def GetPlanOrder_stand(productdate):
    try:
        t = datetime.datetime.now()
        current_order_stand = cache.get('current_order_stand')
        print(current_order_stand)
        # productdate = str(datetime.datetime.strptime(productdate, '%Y-%m-%d'))
        # 检查旧工单是否关闭
        if not current_order_stand == "":
            SQL = "SELECT * FROM planorder_stand_tab WHERE order_no = '" + current_order_stand + "'"
            data = SQL_function3(SQL)
            if len(data) == 0:
                msg = "未查询到当前工单,请检查"
                raise Exception(msg)
            # if not data[0]['status'].upper() == "CLOSE":
            #     msg = "当前工单未完成,无法请求新的工单,请检查"
            #     raise Exception(msg)
        SQL = "SELECT * FROM mom_setting"
        
        data = SQL_function3(SQL)
        # 请求工单接口
        Data2mom = {
            "FACTORYCODE": data[0]['FACTORYCODE'],
            "LINENO": data[0]['LINENO_STAND'],
            "PRODUCTDATE": productdate,
            "SHIFTNO": "0",
        }
        Back_Data = SendMessage2MOM(Data2mom, url['GetPlanOrder'])
        Back_Data = json.loads(Back_Data)
        if Back_Data['STATUS'] == "NG" or len(Back_Data['Data']) == 0:
            raise Exception(Back_Data['ERRORMSG'])
        # # 将当前摄像头工单切换为新工单，保存到本地ini文件中
        # current_order_stand = Back_Data['Data'][0]['ORDERNO']
        # Cache_writer('current_order_stand', current_order_stand, None)
        # filepath = GetFilePath("SoftWare.ini")
        # conf = ConfigParser()  # 需要实例化一个ConfigParser对象
        # conf.read(filepath)  # 需要添加上config.ini的路径，不需要open打开，直接给文件路径就读取，也可以指定encoding='utf-8'
        # print(conf['CommonUse']['CurrentOrder_Stand'])
        # conf.set('CommonUse', 'CurrentOrder_Stand', str(current_order_stand))
        # with open(filepath, 'w', encoding='utf-8') as f:
        #     conf.write(f)
        # print(conf['CommonUse']['CurrentOrder_Stand'])

        # 对获取的摄像头订单保存到数据库
        retdata = PlanOrderRecord_stand(Back_Data['Data'][0]['FACTORYCODE'], Back_Data['Data'][0]['ORDERNO'], Back_Data['Data'][0]['PARTNO'],
                        Back_Data['Data'][0]['SOFT_VER'], Back_Data['Data'][0]['NUM'], Back_Data['Data'][0]['LINENO'],
                        Back_Data['Data'][0]['SHIFTNO'], Back_Data['Data'][0]['PARTNAME'], 0)
        if retdata['STATUS'] == "NG":
            raise Exception("请求工单成功保存失败")
        # 上报MOM收到的单号信息
        back_data = PlanOrderConfirm(Back_Data['Data'][0]['FACTORYCODE'], Back_Data['Data'][0]['LINENO'], Back_Data['Data'][0]['ORDERNO'])
        back_data = json.loads(back_data)
        print(back_data['result'])
        if back_data['result'] == "NG":
            raise Exception(back_data['msg'])
        ret_data = {
            "result": "True",
            "msg": back_data['msg']
        }
        return json.dumps(ret_data)

    except Exception as err:
        # 请求工单、保存工单、回传工单 失败导致。保存请求，消息发送至看板。
        print(err)
        log.info(err)
        ret_data = {
            "result": "False",
            "msg": str(err)
        }

        return json.dumps(ret_data)
# 生产工单报工接口
def PlanOrderReport(CodeName, SN, STNO):
    # current_order = cache.get('current_order')
    t = datetime.datetime.now()


    SQL = "SELECT * FROM ordersn_tab WHERE " + CodeName + " = '" + SN + "'"
    data2 = SQL_function3(SQL)

    if len(data2) == 0:
        msg = "Code:" + SN + " ordersn_tab未找到信息"
        raise Exception(msg)

    SQL = "SELECT * FROM planorder_tab WHERE order_no = '" + data2[0]['order_no'] + "'"
    data = SQL_function3(SQL)

    Data2Mom = {
        "FACTORYCODE": data[0]['factory_code'],
        "ORDERNO": data2[0]['order_no'],
        "PARTNO": data[0]['part_no'],
        "CODE": "100",
        "SN": SN,
        "LINENO": data[0]['line_no'],
        "STATIONNO": STNO,
        "ONLINETIME": data2[0]['online_time'],
        "OFFLINETIME": data2[0]['offline_time'],
        "PRODUCT_DATE": t.strftime('%Y-%m-%d'),
        "PRODUCT_SHIFT": data[0]['shift_no'],
    }
    Data2Mom_list = []
    Data2Mom_list.append(Data2Mom)
    Back_Data = SendMessage2MOM(Data2Mom_list, url['PlanOrderReport'])
    log.info("-----------------------------PlanOrderReport-------------------------")
    log.info("Back_Data")
    Back_Data = json.loads(str(Back_Data).replace("'",'"'))
    if Back_Data[0]['STATUS'] == "NG":
        print("PlanOrderReport 失败")
        print(Back_Data[0]['ERRORMSG'])
        print(Back_Data[0]['SN'])
        if "数据已存在" in Back_Data[0]['ERRORMSG']:
            return True
        return False
    else:
        print("PlanOrderReport 成功")
        return True
def PlanOrderReport_SP(CodeName, SN, STNO):
    print("-------------PlanOrderReport_SP")
    current_order = cache.get('current_order_stand')
    t = datetime.datetime.now()
    SQL = "SELECT * FROM ordersn_tab WHERE " + CodeName + " = '" + SN + "'"
    code_data = SQL_function3(SQL)
    if code_data[0]['stand_code'] == "":
        raise Exception("支架码为空")

    SQL = "SELECT * FROM planorder_stand_tab WHERE order_no = '" + current_order + "'"
    data = SQL_function3(SQL)

    SQL = "SELECT * FROM qr_confrimation_tab WHERE " + CodeName + " = '" + SN + "'"
    data1 = SQL_function3(SQL)

    SQL = "SELECT * FROM qr_confrimation_tab_sp WHERE " + CodeName + " = '" + SN + "' AND station_no = '" + STNO + "'"
    data2 = SQL_function3(SQL)

    Data2Mom = {
        "FACTORYCODE": data[0]['factory_code'],
        "ORDERNO": current_order,
        "PARTNO": data[0]['part_no'],
        "CODE": "100",
        "SN": code_data[0]['stand_code'],
        "LINENO": data[0]['line_no'],
        "STATIONNO": STNO,
        "ONLINETIME": data2[0]['check_time'],
        # "OFFLINETIME": data2[0]['test_time'],
        # 测试时间为空时，默认当前时间
        "OFFLINETIME": data2[0]['test_time'] if data2[0]['test_time'] else datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "PRODUCT_DATE": t.strftime('%Y-%m-%d'),
        "PRODUCT_SHIFT": data[0]['shift_no'],
    }
    Data2Mom_list = []
    Data2Mom_list.append(Data2Mom)
    Back_Data = SendMessage2MOM(Data2Mom_list, url['PlanOrderReport'])
    log.info("-----------------------------PlanOrderReport_SP-------------------------")
    log.info("Back_Data")
    Back_Data = json.loads(str(Back_Data).replace("'", '"'))
    if isinstance(Back_Data,list):
        result = Back_Data[0]['STATUS']
        msg = Back_Data[0]['ERRORMSG']
    else:
        result = Back_Data['STATUS']
        msg = Back_Data['ERRORMSG']

    if result == "NG":
        print("PlanOrderReport_SP 失败")
        if isinstance(Back_Data, list):
            print(Back_Data[0]['ERRORMSG'])
        else:
            print(Back_Data['ERRORMSG'])
        if "数据已存在" in Back_Data[0]['ERRORMSG']:
            return True
        return False
    else:
        print("PlanOrderReport_SP 成功")
        return True
# 当前工单类型检查 MOM下发工单则需要同步信息至MOM、否则不需要同步信息至MOM   type 0 为mom下发  1 为手动创建
def Planorder_ismomcheck(code_name,code_num):
    current_order = cache.get("current_order")
    SQL = "SELECT * FROM ordersn_tab WHERE " + code_name + " = '" + code_num + "'"
    data = SQL_function3(SQL)
    SQL = "SELECT * FROM planorder_tab WHERE order_no = '" + data[0]['order_no'] + "'"
    data = SQL_function3(SQL)
    if data[0]['type'] == '0':
        return True
    else:
        return False
# 当前工单类型检查 MOM下发工单则需要同步信息至MOM、否则不需要同步信息至MOM   type 0 为mom下发  1 为手动创建
def Planorder_stand_ismomcheck():
    current_order_stand = cache.get("current_order_stand")
    SQL = "SELECT * FROM planorder_stand_tab WHERE order_no = '" + current_order_stand + "'"
    data = SQL_function3(SQL)
    if data[0]['type'] == "0":
        return True
    else:
        return False
# 生产过程信息接口
def ProcessInfo(data, test_result = ""):
    ret_data = SendMessage2MOM(data, url['ProcessInfo'], test_result)
    ret_data = json.loads(str(ret_data).replace("'", '"'))
    log.info(">>>>>>>>ProcessInfo ret:" + str(ret_data))
    try:
        # 对NG返回情况进行区分 本地发送导致的失败通过NGSOURCE，MOM返回的无NGSOURCE
        if ret_data['STATUS'] == "NG" and ret_data['NGSOURCE'].upper() == "TIMEOUT":
            if not MomAlerm_Check():
                ret_data['STATUS'] = "OK"
        return ret_data
    except Exception as err:
        return ret_data

# 生产计划获取回传接口
def PlanOrderConfirm(FACTORYCODE, LINENO, ORDERNO):
    Data2Mom = {
        "FACTORYCODE": FACTORYCODE,
        "LINENO": LINENO,
        "ORDERNO": ORDERNO
    }
    Back_Data = SendMessage2MOM(Data2Mom, url['PlanOrderConfirm'])
    Back_Data = json.loads(Back_Data)
    # # 测试数据
    # Back_Data = {
    #     "STATUS": "OK",
    #     "ERRORMSG": ""
    # }

    if Back_Data['STATUS'] == "NG":
        print("PlanOrderConfirm 失败")
        print(Back_Data['ERRORMSG'])
        log.info(Back_Data['ERRORMSG'])

        ret_data = {
            "result": "NG",
            "msg": Back_Data['ERRORMSG'],
        }
    else:
        print("PlanOrderConfirm 成功")
        ret_data = {
            "result": "OK",
            "msg": "",
        }
    return (json.dumps(ret_data))


# 获得到工单请求信息，生产工单  本地创建/MOM下发      type 为0是MOM下发  为1是本地创建
def PlanOrderRecord(factory_code, order_no, part_no, soft_ver, num, line_no, shift_no, gp_model, type):
    log.info(">>>>>>>PlanOrderRecord")
    Data0 = {
        "FACTORYCODE": factory_code,
        "ORDER_NO": order_no,
        "SOFT_VER": soft_ver,
        "NUM": num,
        "LINENO": line_no,
        "SHIFTNO": shift_no
    }
    try:
        t = datetime.datetime.now()
        # 验证 order_no 工单号的唯一性
        SQL = "SELECT * FROM planorder_tab WHERE order_no = '" + order_no + "'"
        print(SQL)
        data = sql_list(SQL)
        if len(data) != 0:
            raise Exception("已经存在" + order_no)

        # online_time为记录工单获取时间   datatime为工单实际使用最新时间
        SQL = "INSERT INTO planorder_tab (order_no,num,num_real,gp_model,factory_code,soft_ver,shift_no,line_no,part_no,online_time,type,sn_num) VALUES ('" \
              + order_no + "','" + num + "','" + str(0) + "','" + gp_model + "','" + factory_code + "','" + soft_ver + "','" \
              + shift_no + "','" + line_no + "','" + part_no + "','" + str(t) + "','" + str(type) + "','" + "0" + "')"
        print(SQL)
        if not SQL_function4(SQL):
            raise Exception('SQL执行失败！   ' + SQL)
        # SQL = "UPDATE planorder_tab SET status = 'Start' WHERE order_no = '" + order_no + "'"
        # if not SQL_function4(SQL):
        #     raise Exception('SQL执行失败！   ' + SQL)

        # 生成对应的SN号码
        # AddOrderSN(order_no, num)

        backdata0 = {
            "STATUS": "OK",
            "ERRORMSG": "",
            "Data": Data0
        }

        Data1 = {}
        meta1 = {
            "msg": "添加成功!",
            "result": "OK"
        }
        backdata1 = {
            "data": Data1,
            "meta": meta1,
        }

    except Exception as err:
        log.info(">>>>>>>PlanOrderRecord ERROR " + str(err))
        print(err)
        backdata0 = {
            "STATUS": "NG",
            "ERRORMSG": "err",
            "Data": Data0
        }

        Data1 = {}
        meta1 = {
            "msg": str(err),
            "result": "NG"
        }
        backdata1 = {
            "data": Data1,
            "meta": meta1,
        }

    if type == 0:
        return backdata0
    elif type == 1:
        return backdata1
def PlanOrderRecord_stand(factory_code, order_no, part_no, soft_ver, num, line_no, shift_no, gp_model, type):
    log.info(">>>>>>>PlanOrderRecord_stand")
    Data0 = {
        "FACTORYCODE": factory_code,
        "ORDER_NO": order_no,
        "SOFT_VER": soft_ver,
        "NUM": num,
        "LINENO": line_no,
        "SHIFTNO": shift_no
    }
    try:
        t = datetime.datetime.now()
        # 验证 order_no 工单号的唯一性
        SQL = "SELECT * FROM planorder_stand_tab WHERE order_no = '" + order_no + "'"
        print(SQL)
        data = sql_list(SQL)
        if len(data) != 0:
            raise Exception("已经存在" + order_no)


        SQL = "INSERT INTO planorder_stand_tab (order_no,num,num_real,gp_model,factory_code,soft_ver,shift_no,line_no,part_no,online_time,type,sn_num_stand) VALUES ('" \
              + order_no + "','" + num + "','" + str(0) + "','" + gp_model + "','" + factory_code + "','" + soft_ver + "','" \
              + shift_no + "','" + line_no + "','" + part_no + "','" + str(t) + "','" + str(type) + "','" + "0" + "')"
        print(SQL)
        if not sql_execute(SQL):
            raise Exception('SQL执行失败！   ' + SQL)
        # SQL = "UPDATE planorder_stand_tab SET status = 'Start' WHERE order_no = '" + order_no + "'"
        # if not SQL_function4(SQL):
        #     raise Exception('SQL执行失败！   ' + SQL)
        # 生成对应的SN号码
        # AddOrderSN(order_no, num)

        backdata0 = {
            "STATUS": "OK",
            "ERRORMSG": "",
            "Data": Data0
        }

        Data1 = {}
        meta1 = {
            "msg": "添加成功!",
            "result": "OK"
        }
        backdata1 = {
            "data": Data1,
            "meta": meta1,
        }

    except Exception as err:
        log.info("PlanOrderRecord_stand ERROR " + str(err))
        backdata0 = {
            "STATUS": "NG",
            "ERRORMSG": "err",
            "Data": Data0
        }

        Data1 = {}
        meta1 = {
            "msg": str(err),
            "result": "NG"
        }
        backdata1 = {
            "data": Data1,
            "meta": meta1,
        }

    if type == 0:
        return backdata0
    elif type == 1:
        return backdata1

def Ram_clean():
    try:
        dump_string = "Clean success\n"
        gc.collect()
    except Exception as err:
        dump_string = "%s\n" % str(err)

    return dump_string

def my_sql_test(SQL):
    thread_name("my_sql_test")
    client_Ip = "10.150.21.89"
    data = '{"Command": "0x02","Check":{"Serial_No": "sn002","Type":"0","Station_No": "ST02","Gp_Model":"B06_1M_HS_Z"}}'
    topic = 'Msg2Mes/'
    TRecv(client_Ip, data, topic)
    data = "OK"
    return data

def thread_name(name):
    import threading
    print("--------start------------>" + str(name))
    print("当前活跃线程数量为", threading.active_count())
    print("当前所有线程信息", threading.enumerate())  # 返回值类型为数组
    print("当前线程信息", threading.current_thread())
    print("--------end-------------->" + str(name))
