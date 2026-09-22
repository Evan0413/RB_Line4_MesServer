import configparser
import copy
import os.path
import socket
import  asyncio
import gc

import requests
from django.shortcuts import render

from django.db import connection, connections

from django.shortcuts import render
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import faker, json
from django.middleware.csrf import get_token
from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect, reverse
from ManDe.models import *
from django.db.models import Q
# Create your views here.
from django.shortcuts import render, reverse, redirect
from rest_framework.settings import api_settings
# from rest_framework_jwt.settings import api_settings
import jwt
from django.forms.models import model_to_dict
from configparser import ConfigParser
from COMMON.ora import *
from COMMON.file_operation import *
from COMMON.msg_operation import *
from COMMON.logBasic import *
# from COMMON.logConfig import *

from django.core.cache import cache

from COMMON.getmqtt import publish, Send_Message, Send_WaitMessage
from django.db import transaction
import uuid
import time
import datetime
from django.http import StreamingHttpResponse

from ManDe import models as md
from django.core import serializers

log = logger

# import logging
def board(request):
    back_data_list = []
    product_tab = []
    meta = {}
    try:
        equip_status = cache.get('Equip_Status')
        device_class = cache.get('DeviceClass')
        for it in device_class:
            if it["EquipStatus"]:
                status = 1
            else:
                status = 0
            data = {
                "equipment_name": it["EquipName"], "equipment_num": it["EquipNumber"],
                "equipment_ip": it['EquipIP'], "equipment_serial": it['EquipSerial'],
                "equipOrder": '', "equipResult": '',
                "equipStatus": status, "equipError": it['EquipError'], "msg": ""
            }
            back_data_list.append(data)
        for it1 in equip_status:
            for it2 in back_data_list:
                if it1['EquipNumber'] == it2['equipment_num']:
                    it2['equipOrder'] = it1['EquipOrder']
                    it2['equipResult'] = it1['EquipResult']
        meta = {
            "msg": "board信息获取成功",
            "result": "OK"
        }
        # 生产面板信息
        SQL = "SELECT Pass FROM model_tab WHERE gp_model = '" + cache.get('current_model') + "'"
        # print(SQL)
        result = sql_list(SQL)
        # The dashboard is polled even before model data has been restored.
        # Display zero counters instead of returning NG for an empty database.
        Pass_num = int(result[0][0]) if result else 0
        SQL = "SELECT Fail FROM model_tab WHERE gp_model = '" + cache.get('current_model') + "'"
        # print(SQL)
        result = sql_list(SQL)
        Fail_num = int(result[0][0]) if result else 0

        sum = Pass_num + Fail_num
        if sum == 0:
            ProductSum = str(sum)
            yields = '{:.2%}'.format(0)
            Accept = str(Pass_num)
            Reject = str(Fail_num)
        else:
            ProductSum = str(sum)
            yields = '{:.2%}'.format(Pass_num/sum)
            Accept = str(Pass_num)
            Reject = str(Fail_num)

        Product_Tab = {
            "ProductSum": ProductSum,   #生产的总数 成功＋失败
            "Accept": Accept,           #成功数字
            "Reject": Reject,           #失败数字
            "yields": yields            #成功所占百分比
        }
    except Exception as err:
        print(str(err))
        meta = {
            "msg": str(err),
            "result": "NG"
        }
        Product_Tab = {
            "ProductSum": "0",  # 生产的总数 成功＋失败
            "Accept": "0",  # 成功数字
            "Reject": "0",  # 失败数字
            "yields": "0"  # 成功所占百分比
        }
    # 添加胶水料号 胶水信息 胶水校验时间
    Getjs_part_no_msg()
    backdata = {
        "localmodel": cache.get('current_model'),
        "JS_PART_NO": cache.get('JS_PART_NO',""),
        "JS_PART_NO_MSG": "通过" if cache.get("js_part_no_flag", "") == "true" else "未通过"  + " " + cache.get("JS_PART_NO_MSG",""),
        "JS_PART_NO_TIME": cache.get("JS_PART_NO_TIME",""),
        "data": back_data_list,
        "meta": meta,
        "ProductTab": Product_Tab
    }
    # print("-------------------board backdata-------------------")
    return HttpResponse(json.dumps(backdata, ensure_ascii=False))
# 保存录入的胶水号,在生产时和上传的当前胶水号做比较
def Save_JS_PART_NO(request):
    meta = {
        "msg": "胶水码保存成功",
        "result": "OK"
    }
    data = {}
    try:
        JS_PART_NO = request.GET.get('JS_PART_NO')
        Setjs_part_no(JS_PART_NO)
        backdata = {
            "data": data,
            "meta": meta,
        }
        return HttpResponse(json.dumps(backdata, ensure_ascii=False))
    except Exception as err:
        log.info(str(err))
        meta = {
            "msg": str(err),
            "result": "NG"
        }
        data = {}
        backdata = {
            "data": data,
            "meta": meta,
        }
        return HttpResponse(json.dumps(backdata, ensure_ascii=False))
        
def urltest(request):
    # 总的全局外部url
    # url = {
    #     "GetPlanOrder": "http://10.251.84.54:8181/mes.asmx",
    #     "PlanOrderConfirm": "http://10.251.84.54:8181/mes.asmx",
    #     "ProcessInfo": "http://10.251.84.54:8181/mes.asmx",
    #     "PlanOrderReport": "http://10.251.84.54:8181/mes.asmx",
    #     "CreateSheetPull": "http://10.251.84.54:8181/mes.asmx",
    #     "CallAGVOffline": "http://10.251.84.54:8181/mes.asmx"
    # }
    print(request.GET.get('type'))
    if request.GET.get('type') == "1":
        GetPlanOrder()
    elif request.GET.get('type') == "2":
        ProcessInfo()
    elif request.GET.get('type') == "3":
        PlanOrderReport()
    elif request.GET.get('type') == "4":
        CreateSheetPull()
    elif request.GET.get('type') == "5":
        CallAGVOffline()
def test(request):
    # import subprocess
    # t = datetime.datetime.now()
    # year = t.year
    # mon = t.month
    # day = t.day
    #
    # username = 'root'
    # password = '123456'
    # database_name = 'aview_mysql'
    # path = "D:\\MESDATA\\SQL\\"
    # filename = 'backup_' + str(year) + '_' + str(mon) + '_' + str(day) + '.sql'
    #
    # type = request.GET.get('type')
    # if int(type) == 1:
    #     command = f'mysqldump -u {username} -p{password} --databases {database_name}'
    #     with open(path + filename, 'w') as backup_file:
    #         subprocess.run(command, stdout=backup_file, shell=True)


    if PassAfterBind("C01_2M_CS_ZQ_YQ","ST08","pcba_code1","37763990A0A23092100778"):
        print("-------------test")
    else:
        print("-------------test2")

    return HttpResponse(json.dumps("OK", ensure_ascii=False))


##简单定义返回报文
res =  {
        "status": "",
        "date":datetime.datetime.now(),
        "msg":""
}
@csrf_exempt
def test1(request):
    print(request.method)
    body = eval(request.body)
    print(">>>>>body: ")
    print(body)
    if request.method == 'POST':
        ##判断POST请求body是否为空
        if request.body.decode() == '':
            res['status'] = "Error"
            res['msg'] = "body is Null!"
            return JsonResponse(res)
        ##不为空就将body转换成字典
        else:
            body = eval(request.body)
            # print(">>>>>body: ")
            # print(body)
        ##确保字段不为空
        if body['x'] == '' or body['y'] == '':
            res['status'] = "Error"
            res['msg'] = "please check body!"
            return JsonResponse(res)
        else:
            res['status'] = "Success"
            res['msg'] = body['x'] + body['y']
            return JsonResponse(res)
    else:
        res['status'] = "Error"
        res['msg'] = "request method not is POST!"

def ws(request):
    print("ws")
    type = request.GET.get('type')
    print(type)
    # datasend = {"JsonStr": str(data)}
    # url = "http://10.44.199.166:9000/api/test"
    t = datetime.datetime.now()
    # SQL = "SELECT * FROM ordersn_tab WHERE order_no = 'OR231111000002'"
    # print(SQL)
    # data = easy_sql_reader(SQL)
    # print(data)
    # for it in data:
    if type == "1":
        url = "http://10.246.140.225:9000/mes.asmx/GetPlanOrder"
        data = {"FACTORYCODE": "B620", "LINENO": "SXTMZ01", "PRODUCTDATE": "2023-11-14", "SHIFTNO": "0"}
    elif type == "2":
        url = "http://10.251.84.54:8181/mes.asmx/PlanOrderConfirm"
        data = {"FACTORYCODE": "B620", "LINENO": "SXTMZ01", "ORDERNO": "OR231020000004"}
    elif type == "3":
        url = "http://10.251.84.54:8181/mes.asmx/ProcessInfo"
        data = {"UUID": "2023-10-20-0001", "STATION_NO": "S100", "CODE": "100", "OFFLINE_TIME": "2023-10-08 11:03",
                "WORK_TIME": "20", "K_PART_NO": "K_PART_NO", "K_PART_BATCH": "K_PART_BATCH",
                "Q_PART_NO": "Q_PART_NO",
                "Q_PART_BATCH": "Q_PART_BATCH", "J_PART_NO": "J_PART_NO", "J_PART_BATCH": "J_PART_BATCH",
                "H_PART_NO": "H_PART_NO", "H_PART_BATCH": "H_PART_BATCH",
                "F_PART_NO": "F_PART_NO", "F_PART_BATCH": "F_PART_BATCH", "L_PART_NO": "L_PART_NO",
                "L_PART_BATCH": "L_PART_BATCH", "Z_PART_NO": "Z_PART_NO", "Z_PART_BATCH": "Z_PART_BATCH",
                "T_PART_NO": "T_PART_NO", "T_PART_BATCH": "T_PART_BATCH", "P_PART_NO": "P_PART_NO",
                "P_PART_BATCH": "P_PART_BATCH", "S_PART_NO": "S_PART_NO", "S_PART_BATCH": "S_PART_BATCH",
                "PABA_1": "PABA_1", "PCBA_2": "PCBA_2", "SOFT_VERSION": "SOFT_VERSION", "SN": "SN",
                "PART_NO": "PART_NO", "STATION_STATUS": "1"}
    elif type == "4":
        url = "http://10.246.140.225:9000/mes.asmx/PlanOrderReport"
        data = [{"FACTORYCODE": "B620", "ORDERNO": "OR231111000002", "PARTNO": "37760L01990A0A00",
                 "CODE": "100", "SN": "test", "LINENO": "SXTMZ01",
                 "STATIONNO": "ST11", "ONLINETIME": "2023-10-11 15:44:38", "OFFLINETIME": "2023-10-11 22:00:00",
                 "PRODUCT_DATE": "2023-11-13", "PRODUCT_SHIFT": "0"}]
        # print(data)
    elif type == "5":
        url = "http://10.246.140.225:9000/mes.asmx/CreateSheetPull"
        data = {"LINE_NO": "SXTMZ01", "SHIFT_NO": "0", "PRODUCT_DATE": "2024-01-04", "POINT_NO": "2001",
                "MATERIAL_NO": "37760003990A0A00"}
    elif type == "6":
        url = "http://10.246.140.225:9000/mes.asmx/CallAGVOffline"
        data = {"LINE_NO": "SXTMZ01","POINT_NO": "2001","PART_NO": ""}  # 改站点没有AGV的时候，MOM不反回信息，待MOM优化

    ret = SendMessage2MOM(data, url)
    print(url)
    print("ws_request:")
    print(data)
    print("ws_reuturn:")
    print(ret)
    ret = json.loads(ret)
        # print(ret['ERRORMSG'])

    # return JsonResponse(ret)
    # HttpResponse(json.dumps(ret, ensure_ascii=False))
    return HttpResponse(json.dumps(ret, ensure_ascii=False))
def test2(request):
    try:

        # qr_code2 = request.GET.get('qr_code2')
        # num = int(request.GET.get('num'))

        filepath = GetFilePath("error.txt")
        print(filepath)
        conf = ConfigParser(allow_no_value=True)  # 需要实例化一个ConfigParser对象
        conf.read(filepath)  # 需要添加上config.ini的路径，不需要open打开，直接给文件路径就读取，也可以指定encoding='utf-8'
        code = conf['CommonUse']['code']
        print("---------")
        print(type(code))
        print(len(code))
        # code.replace("\n",",")
        print(type(code))
        print(len(code))
        code_list = code.split("\n")
        print(type(code_list))
        print(len(code_list))

        # print(code_list)
        # code_list = ['4PSGKCDRLP377601RR990L0A00L2404220559']

        num = 2404252001

        for it1 in code_list:
            SQL = "SELECT * FROM ordersn_tab WHERE stand_code = '" + it1 + "'"
            or_data = SQL_function3(SQL)
            order_no = or_data[0]['stand_order_no']

            SQL = "SELECT * FROM planorder_stand_tab WHERE order_no = '" + order_no + "'"
            par_data = SQL_function3(SQL)
            part_no = par_data[0]['part_no']

            print(it1)
            print("---------")
            SQL = "SELECT * FROM qr_confrimation_tab_sp WHERE stand_code = '" + it1 + "'"
            data = SQL_function3(SQL)
            if not len(data) == 1:
                raise Exception("len not 1")

            for it in data:
                # SQL = "SELECT * FROM ordersn_tab WHERE stand_code = '" + data[0]['stand_code'] + "'"
                # ordata = SQL_function3(SQL)
                # SQL = "SELECT * FROM planorder_stand_tab WHERE order_no = '" + ordata[0]['order_no'] + "'"
                # order_data = SQL_function3(SQL)
                num += 1
                Data2mom = {
                    "UUID": str(num),
                    "STATION_NO": it['station_no'],
                    "CODE": "100",
                    # "OFFLINE_TIME": pro_data[0]['offline_time'],
                    "OFFLINE_TIME": it['test_time'],
                    "WORK_TIME": 1,
                    "K_PART_NO": "K_PART_NO",
                    "K_PART_BATCH": "K_PART_BATCH",
                    "Q_PART_NO": "Q_PART_NO",
                    "Q_PART_BATCH": "Q_PART_BATCH",
                    "J_PART_NO": "J_PART_NO",
                    "J_PART_BATCH": "J_PART_BATCH",
                    "H_PART_NO": "H_PART_NO",
                    "H_PART_BATCH": "H_PART_BATCH",
                    "F_PART_NO": "F_PART_NO",
                    "F_PART_BATCH": "F_PART_BATCH",
                    "L_PART_NO": "L_PART_NO",
                    "L_PART_BATCH": "L_PART_BATCH",
                    "Z_PART_NO": "Z_PART_NO",
                    "Z_PART_BATCH": "Z_PART_BATCH",
                    "PCBA_1": it['pcba_code1'],
                    "PCBA_2": it['pcba_code2'],
                    "SN": it['stand_code'],
                    "PART_NO": part_no,
                    "STATION_STATUS": "OK",
                }
                # num += 1
                ret_data = ProcessInfo(Data2mom)
                if ret_data['STATUS'] == "NG":
                    raise Exception(ret_data['ERRORMSG'])
                print(it['check_time'])
                print(it['test_time'])
                # print(datetime.datetime.strptime(it['check_time'], '%Y-%m-%d'))
                Data2Mom = {
                    "FACTORYCODE": "B620",
                    "ORDERNO": order_no,
                    "PARTNO": part_no,
                    "CODE": "100",
                    "SN": it['stand_code'],
                    "LINENO": "SXTZC01",
                    "STATIONNO": "SP21",
                    "ONLINETIME": it['check_time'],
                    "OFFLINETIME": it['test_time'],
                    "PRODUCT_DATE": str(
                        datetime.datetime.strptime(it['check_time'], '%Y-%m-%d %H:%M:%S').year) + "-0" + str(
                        datetime.datetime.strptime(it['check_time'], '%Y-%m-%d %H:%M:%S').month) + "-" + str(
                        datetime.datetime.strptime(it['check_time'], '%Y-%m-%d %H:%M:%S').day),
                    "PRODUCT_SHIFT": "0",
                }
                Data2Mom_list = []
                Data2Mom_list.append(Data2Mom)
                Back_Data = SendMessage2MOM(Data2Mom_list, "http://10.246.140.225:9000/mes.asmx/PlanOrderReport")
                # num += 1
                ret = {"msg": "OK"}
    except Exception as err:
        print(str(err))
        ret = {"msg": str(err)}
        print("xxxxxxxxxxxxxx")
    print("---------------------------")

    return HttpResponse(json.dumps(ret, ensure_ascii=False))

def test_database(request):
    ret = {
        "data1":"",
        "data2":"",
        "data3":"",
        "data4":""
    }
    SQL1 = "SELECT * FROM planorder_tab"
    print(SQL1)
    data = easy_sql_reader(SQL1)
    print(data)
    ret['data1'] = data

    SQL2 = "SELECT * FROM qr_confrimation_tab"
    print(SQL2)
    data = easy_sql_reader(SQL2)
    print(data)
    ret['data2'] = data

    data = SQL_function3(SQL1)
    print(data)
    ret['data3'] = data

    data = SQL_function3(SQL2)
    print(data)
    ret['data4'] = data

    return HttpResponse(json.dumps(ret, ensure_ascii=False))
# --------------------------------------URL MOM  功能实现-----------------------------------------------

#工单接收接口
# def PlanOrderList(request):
#     print(request.method)
#     body = eval(request.body)
#     print(">>>>>body: ")
#     print(body)
#     try:
#         if request.method == 'POST':
#             ##判断POST请求body是否为空
#             if request.body.decode() == '':
#                 raise Exception("body is Null!")
#             ##不为空就将body转换成字典
#             else:
#                 body = eval(request.body)
#                 # 解析body中的内容生成工单
#                 factory_code = body['FACTORYCODE']
#                 order_no = body['ORDER_NO']
#                 part_no = body['PARTNO']                        #   物料编码
#                 soft_ver = body['SOFT_VER']
#                 num = body['NUM']
#                 line_no = body['LINENO']
#                 shift_no = body['SHIFTNO']
#                 gp_model = ""                                   # MOM 下面发应该包含型号信息    未完成待添加
#                 PlanOrderRecord(factory_code, order_no, part_no, soft_ver, num, line_no, shift_no, gp_model, 0)
#
#                 # # 切换检查当前工单是否已经完成
#                 # SQL = "SELECT * FROM planorder_tab WHERE plan_no = '" + cache.get('current_plan')
#                 # data = sql_list(SQL)
#                 # print(data)
#                 # if len(data) != 1:
#                 #     raise Exception("查找产品在当前工单" + current_plan + "失败")
#                 # if data[0][1] < data[0][2]:
#
#                 # 切换到新的工单
#
#
#         else:
#             raise Exception("request method not is POST!")
#     except Exception as err:
#         print(err)

#工单数量削减接口
def CancelPlanOrderList(request):
    print(request.method)
    body = eval(request.body)
    print(">>>>>body: ")
    print(body)
    try:
        if request.method == 'POST':
            ##判断POST请求body是否为空
            if request.body.decode() == '':
                raise Exception("body is Null!")
            ##不为空就将body转换成字典
            else:
                body = eval(request.body)
                # 解析body中的内容生成工单
                # factory_code = body['FACTORYCODE']
                order_no = body['ORDER_NO']
                # part_no = body['PARTNO']  # 物料编码
                # soft_ver = body['SOFT_VER']
                num = body['NUM']          # 需要减少多少？   or    需要减少到多少？
                # line_no = body['LINENO']
                # shift_no = body['SHIFTNO']

                # 检查料盘余料还能生产多少，返回最多减产结果给MOM
                # SQL
                # plan_no


        else:
            raise Exception("request method not is POST!")
    except Exception as err:
        print(err)



#------------------------------------ WEB URL 功能实现--------------------------------------------
@csrf_exempt
def login(request):
    log.info("----------------login-------------------")
    if request.method == 'POST':
        try:
            ascii_values = ""
            request.POST.get('username', None)
            for character in request.POST.get("password", None):
                ascii_values += str(ord(character))
            SQL = "select ID,userid from employee_tab WHERE userid='" + request.POST.get('username', None) + "'"
            data = SQL_function3(SQL)
            if data:
                SQL = " select ID,userid,password,level from employee_tab WHERE userid='" + request.POST.get('username',
                                                                                                             None) + "'" \
                                                                                                                     " and password='" + ascii_values + "'"

                data = SQL_function3(SQL)
                if data:
                    b = {'username': request.POST.get('username'), 'password': request.POST.get('password')}
                    token = "Bearer " + jwt.encode(b, 'sercet', algorithm='HS256')
                    # 用户名和密码都满足，保存token到表中
                    user_uuid = uuid.uuid1().hex
                    print(user_uuid)
                    user_cache = {
                        "userid": data[0]['userid'],
                        "username": request.POST.get('username'),
                        "level": data[0]['level']
                    }
                    Cache_writer(user_uuid, List_Json(user_cache))
                    a = cache.get(user_uuid, default=None)

                    #-------------获取board信息--------------
                    back_data_list = []
                    equip_status = cache.get('Equip_Status')
                    device_class = cache.get('DeviceClass')
                    for it in device_class:
                        if it["EquipStatus"]:
                            status = 1
                        else:
                            status = 0
                        data_board = {
                            "equipment_name": it["EquipName"], "equipment_num": it["EquipNumber"],
                            "equipment_ip": it['EquipIP'], "equipment_serial": it['EquipSerial'],
                            "equipOrder": '', "equipResult": '',
                            "equipStatus": status, "equipError": it['EquipError'], "msg": ""
                        }
                        back_data_list.append(data_board)
                    for it1 in equip_status:
                        for it2 in back_data_list:
                            if it1['EquipNumber'] == it2['equipment_num']:
                                it2['equipOrder'] = it1['EquipOrder']
                                it2['equipResult'] = it1['EquipResult']

                    # 生产面板信息
                    SQL = "SELECT Pass FROM model_tab WHERE gp_model = '" + cache.get('current_model') + "'"
                    result = SQL_function3(SQL)
                    # A newly deployed server may not have restored model data
                    # yet.  Authentication should still succeed and show an
                    # empty production dashboard in that case.
                    Pass_num = int(result[0]['Pass']) if result else 0
                    SQL = "SELECT Fail FROM model_tab WHERE gp_model = '" + cache.get('current_model') + "'"
                    print(SQL)
                    result = SQL_function3(SQL)
                    Fail_num = int(result[0]['Fail']) if result else 0

                    sum = Pass_num + Fail_num
                    if sum == 0:
                        ProductSum = str(sum)
                        yields = '{:.2%}'.format(0)
                        Accept = str(Pass_num)
                        Reject = str(Fail_num)
                    else:
                        ProductSum = str(sum)
                        yields = '{:.2%}'.format(Pass_num / sum)
                        Accept = str(Pass_num)
                        Reject = str(Fail_num)
                    Product_Tab = {
                        "ProductSum": ProductSum,  # 生产的总数 成功＋失败
                        "Accept": Accept,  # 成功数字
                        "Reject": Reject,
                        "yields": yields  # 成功所占百分比
                    }
                    # -------------获取board信息 结束--------------

                    Data = {
                        "username": request.POST.get('username'),
                        "password": request.POST.get('password'),
                        "token": token,
                        "level": data[0]['level'],
                        "uuid": user_uuid,
                        "data": back_data_list,
                        "ProductTab": Product_Tab
                    }
                    meta = {
                        "msg": "账号密码正确!",
                        "result": "OK"
                    }
                    backdata = {
                        "data": Data,
                        "meta": meta,
                    }
                    print(Data)
                    # 登录初始化全局变量
                    # GolbalGroup_Ini()

                    return HttpResponse(List_Json(backdata))

                else:
                    Data = {
                        "username": request.POST.get('username'),
                        "password": request.POST.get('password'),
                        "token": "",
                        "level": "",
                        "data": []
                    }
                    meta = {
                        "msg": "该账号密码不正确，请重新输入!",
                        "result": "NG"
                    }
                    backdata = {
                        "data": Data,
                        "meta": meta,
                    }
                    return HttpResponse(List_Json(backdata))

            else:

                Data = {
                    "username": request.POST.get('username'),
                    "password": request.POST.get('password'),
                    "token": "",
                    "level": "",
                    "data": []
                }
                meta = {
                    "msg": "无此用户",
                    "result": "NG"
                }
                request.session.delete()
                backdata = {
                    "data": Data,
                    "meta": meta,
                }
                return HttpResponse(List_Json(backdata))

        except Exception as err:
            log.info("Login ERROR" + str(err))
            meta = {
                "msg": "登录失败-" + str(err),
                "result": "NG"
            }
            return HttpResponse(List_Json({"data": {}, "meta": meta}), status=500)
    else:
        if request.session.get('username', None) == None:
            return redirect('/')
        else:
            return render(request, 'login.html')


@csrf_exempt
def main(request):
    try:
        user_uuid = request.GET.get('uuid', '')
        log.debug("menus uuid=%s", user_uuid)

        # # 验证缓存中的uuid 判断身份并且刷新uuid过期时限
        # print(cache.get(user_uuid, default=None))
        # if cache.get(user_uuid, default=None) == None:
        #     Data = {
        #
        #     }
        #     meta = {
        #         "msg": "获取菜单列表失败:uuid不存在",
        #         "result": "NG"
        #     }
        #
        #     backdata = {
        #         "data": Data,
        #         "meta": meta,
        #     }
        #     return HttpResponse(json.dumps(backdata, ensure_ascii=False))
        # cache.touch(user_uuid)

        # #获取该uuid的身份等级信息，进行权限判断
        # user_cache = json.loads(cache.get(user_uuid, default=None))
        # if user_cache['level'] == "1":
        #     print("1")

        groups = group.objects.all().filter(group_main_id="0")
        menus = menu.objects.all()
        i = 0
        menu_chk = []
        r_arr = []
        menulist = []
        for o in groups:
            temp = model_to_dict(o)
            menulist.append(temp)
        for o in menus:
            r_arr.append(o.toDict())

        for menu_d in r_arr:
            menu_chk.append(menu_d)
        # print(menus)

        meta = {
            "msg": "获取菜单列表成功!",
            "result": "OK"
        }

        Data = {'menulist': menulist, "menu_chk": menu_chk}

        backdata = {
            "data": Data,
            "meta": meta,
        }
        log.info("菜单列表获取成功 group=%s menu=%s", len(menulist), len(menu_chk))

        return HttpResponse(json.dumps(backdata, ensure_ascii=False))

    except Exception as err:
        log.error("菜单列表获取失败: %s", err)
        Data = {

        }
        meta = {
            "msg": "获取菜单列表失败",
            "result": "NG"
        }

        backdata = {
            "data": Data,
            "meta": meta,
        }
        # print(err)
        return HttpResponse(json.dumps(backdata, ensure_ascii=False))


@csrf_exempt
def local_users(request):
    try:
        loginName = request.GET.get('loginName', '')
        if (loginName == 'administrator'):
            SQL = " select ID,userid,password,level from employee_tab"
        else:
            SQL = " select ID,userid,password,level from employee_tab WHERE userid='" + loginName + "'"

        data = easy_sql_reader(SQL)
        meta = {
            "msg": "查询成功!",
            "result": "OK"
        }
        backdata = {
            "data": data,
            "meta": meta,
        }
        log.info("local_users 查询成功 count=%s", len(data) if data else 0)

        return HttpResponse(List_Json(backdata))

        # return render(request, 'main.html', context=context)
    except Exception as err:
        Data = {

        }
        meta = {
            "msg": "获取菜单列表失败",
            "result": "NG"
        }

        backdata = {
            "data": Data,
            "meta": meta,
        }
        print(err)
        return HttpResponse(List_Json(backdata))
        # print(err)
        # return redirect('/LO/')


@csrf_exempt
def changpsw(request):
    try:

        ascii_value = ""
        print(request.POST.get("oldpassword", None))
        for character1 in request.POST.get("oldpassword", None):
            ascii_value += str(ord(character1))
        print(ascii_value)

        SQL = "SELECT password FROM employee_tab WHERE id='" + request.POST.get('usernameid',
                                                                                "") + "'and password='" + ascii_value + "'"
        cs = connection.cursor()
        cs.execute(SQL)
        data = cs.fetchone()
        cs.close()
        print(SQL)
        print(data)
        if not data:
            raise Exception("旧密码输入不正确！")
        ascii_values = ""
        for character1 in request.POST.get("newpassword", None):
            ascii_values += str(ord(character1))
        # print(ascii_values)

        SQL = "UPDATE employee_tab SET PASSWORD='" + ascii_values + "' WHERE id='" + request.POST.get('usernameid',
                                                                                                      "") + "'"
        # print(SQL)
        cs = connection.cursor()
        cs.execute(SQL)
        cs.close()
        Data = {
            "id": request.POST.get('usernameid', ""),
            "password": request.POST.get("newpassword", None)
        }

        meta = {
            "msg": "修改用户密码成功",
            "result": "OK"
        }

        backdata = {
            "data": Data,
            "meta": meta,
        }
        # print(List_Json(backdata))
        return HttpResponse(List_Json(backdata))


    except Exception as err:

        Data = {
            "id": request.POST.get('usernameid', ""),
            "password": request.POST.get("oldpassword", None)
        }
        meta = {
            "msg": "修改用户密码失败-" + str(err),
            "result": "NG"
        }

        backdata = {
            "data": Data,
            "meta": meta,
        }

        return HttpResponse(List_Json(backdata))


# --------------------------------获取用户列表----------------------------
@csrf_exempt
def users(request):
    try:
        query = request.GET.get('query', '')
        pagenum = request.GET.get('pagenum', '')
        pagesize = request.GET.get('pagesize', '')

        SQL = "select ID,userid,password,level from employee_tab"
        if len(query) != 0:
            SQL += " WHERE userid like '%" + query + "%'"

        data = aview_easy_sql_reader_page1(SQL, pagenum, pagesize)
        meta = {
            "msg": "获取用户列表成功!",
            "result": "OK"
        }
        backdata = {
            "data": data,
            "meta": meta,
        }
        log.info("用户列表获取成功 total=%s", data.get('total') if isinstance(data, dict) else "")
        return HttpResponse(List_Json(backdata))

    except Exception as err:
        Data = {

        }
        meta = {
            "msg": "获取用户列表失败",
            "result": "NG"
        }

        backdata = {
            "data": Data,
            "meta": meta,
        }
        # print(err)
        return HttpResponse(List_Json(backdata))


# --------------------------------删除用户列表----------------------------

@csrf_exempt
def Deleteusers(request):
    try:
        print(request)
        id = request.POST.get('id', '')
        print(int(id))

        SQL = " delete from employee_tab where id= " + id + ""
        if not sql_execute(SQL):
            raise Exception('SQL执行失败！')

        # print(SQL)
        meta = {
            "msg": "删除成功!",
            "result": "OK"
        }
        backdata = {
            "data": {},
            "meta": meta,
        }

        return HttpResponse(List_Json(backdata))

    except Exception as err:
        Data = {

        }
        meta = {
            "msg": "获取用户列表失败",
            "result": "NG"
        }

        backdata = {
            "data": Data,
            "meta": meta,
        }
        print(err)
        return HttpResponse(List_Json(backdata))
        # print(err)
        # return redirect('/LO/')


# --------------------------------添加用户列表----------------------------

@csrf_exempt
def Addusers(request):
    try:
        print(request)
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        level = request.POST.get('level', '')
        ascii_values = ""
        for character in password:
            ascii_values += str(ord(character))
        SQL = "INSERT INTO employee_tab(userid,password,level)VALUES ('" + username + "','" + ascii_values + "','" + level + "')"
        print(SQL)

        if not sql_execute(SQL):
            raise Exception('SQL执行失败！')

        print(SQL)
        meta = {
            "msg": "添加用户成功!",
            "result": "OK"
        }
        backdata = {
            "data": {
                "username": request.POST.get('username', ''),
                "password": request.POST.get('password', '')
            },
            "meta": meta,
        }

        return HttpResponse(List_Json(backdata))

    except Exception as err:
        Data = {

        }
        meta = {
            "msg": "添加用户失败",
            "result": "NG"
        }

        backdata = {
            "data": Data,
            "meta": meta,
        }
        print(err)
        return HttpResponse(List_Json(backdata))
        # print(err)
        # return redirect('/LO/')


# --------------------------------获取某个用户信息----------------------------
@csrf_exempt
def usersid(request):
    try:
        id = request.GET.get('localid', '')

        print(id)

        SQL = " select ID,userid,password,level from employee_tab where id= " + id + ""

        print(SQL)
        data = easy_sql_reader1(SQL)

        # data = aview_easy_sql_reader_page1(SQL)
        print(data)
        meta = {
            "msg": "获取用户信息成功!",
            "result": "OK"
        }
        backdata = {
            "data": data,
            "meta": meta,
        }

        # print(backdata)
        # print(SQL)
        print(List_Json(backdata))
        return HttpResponse(List_Json(backdata))

    except Exception as err:
        Data = {

        }
        meta = {
            "msg": "获取用户信息失败",
            "result": "NG"
        }

        backdata = {
            "data": Data,
            "meta": meta,
        }
        # print(err)
        return HttpResponse(List_Json(backdata))


# --------------------------------修改用户信息----------------------------
@csrf_exempt
def EditUsersInfo(request):
    try:
        print(request)
        id = request.POST.get('ID', '')
        level = request.POST.get('level', '')

        print(id)

        # SQL = " select ID,userid,password,level from employee_tab where id= "+id+""

        SQL = "UPDATE employee_tab SET level='" + str(level) + "' WHERE id=" + id + ""

        print(SQL)
        # data = easy_sql_reader1(SQL)
        cs = connection.cursor()
        cs.execute(SQL)
        cs.close()

        # data = aview_easy_sql_reader_page1(SQL)
        # print(data)
        meta = {
            "msg": "修改用户信息成功!",
            "result": "OK"
        }
        backdata = {
            "data": {
                "ID": id,
                "level": level,
            },
            "meta": meta,
        }

        print(backdata)
        print(SQL)
        print(List_Json(backdata))
        return HttpResponse(List_Json(backdata))

    except Exception as err:
        Data = {

        }
        meta = {
            "msg": "获取用户信息失败",
            "result": "NG"
        }

        backdata = {
            "data": Data,
            "meta": meta,
        }
        # print(err)
        return HttpResponse(List_Json(backdata))


# ----------------------------------设备管理-------------------------------------------

# --------------------------------获取设备列表----------------------------

def updateCarrierStatus(request):
    print("---------------updateCarrierStatus----------------")
    device_class = cache.get('DeviceClass')
    back_data_list= []
    for it in device_class:
        status_num = 0
        if it["EquipStatus"]:
            status_num = 1
        data = {
            "equipment_name": it["EquipName"], "equipment_num": it["EquipNumber"], "equipment_ip": it['EquipIP'],
            "equipment_serial": it['EquipSerial'],
            "equipOrder": "", "equipResult": "", "checkDevice": "/", "checkResult": "",
            "equipStatus": status_num, "equipError": it['EquipError']
        }

        # 获取最新的设备状态
        checkdevice = cache.get('CheckDevice')
        equip_status = cache.get('Equip_Status')
        # print(equip_status)
        for it1 in equip_status:
            if it1['EquipNumber'] == data['equipment_num']:
                data['equipOrder'] = it1['EquipOrder']
                data['equipResult'] = it1['EquipResult']
                data['checkDevice'] = it1['CheckDevice']
                data['checkResult'] = it1['CheckResult']

        for it2 in checkdevice:
            if it2 == data['equipment_num']:
                data['checkDevice'] = 'YES'

        back_data_list.append(data)
    back_data = {
        "localmodel": cache.get('current_model'),
        "data": back_data_list,
        # "table": [{"ProductSum": "", "ProductQuantity": "", "Accept": "", "Yield": ""}]
    }
    back_meta = {
        "msg": "",
        "result": "OK"
    }
    # print(">>>>>>>back_data")
    # print(back_data)
    backdata = {
        "data": back_data,
        "meta": back_meta,
    }
    print(backdata)
    return HttpResponse(List_Json(backdata))


@csrf_exempt
def devices(request):
    # print("------------------------set tag success-------------------------")
    try:
        query = request.GET.get('query', '')
        pagenum = request.GET.get('pagenum', '')
        pagesize = request.GET.get('pagesize', '')
        SQL = "select id,equipment_name,equipment_num,equipment_ip,equipment_serial from equipment_tab"
        if len(query) != 0:
            SQL += " WHERE equipment_name like '%" + query + "%'"

        data = aview_easy_sql_reader_page1(SQL, pagenum, pagesize)
        # 冒泡
        n = len(data['data'])
        for i in range(n):
            # Last i elements are already in place
            for j in range(0, n - i - 1):
                if int(data['data'][j]['equipment_serial']) > int(data['data'][j + 1]['equipment_serial']):
                    data['data'][j], data['data'][j + 1] = data['data'][j + 1], data['data'][j]

        meta = {
            "msg": "获取设备列表成功!",
            "result": "OK"
        }
        backdata = {
            "data": data,
            "meta": meta,
        }
        log.info("设备列表获取成功 total=%s", data.get('total') if isinstance(data, dict) else n)
        return HttpResponse(List_Json(backdata))

    except Exception as err:
        Data = {

        }
        meta = {
            "msg": "获取设备列表失败",
            "result": "NG"
        }

        backdata = {
            "data": Data,
            "meta": meta,
        }
        print(err)
        return HttpResponse(List_Json(backdata))


# --------------------------------删除设备列表----------------------------

@csrf_exempt
def DeleteDevice(request):
    try:
        print('###########################')
        print(request)
        id = request.POST.get('id', '')
        name = request.POST.get('name', '')
        device_class = cache.get('DeviceClass')
        msg = ""
        Tag = False
        for it in device_class:
            if it['EquipName'] == name and it['EquipStatus']:
                msg = "当前设备已连接，请断开"
                Tag = True
        if Tag:
            raise Exception(msg)

        SQL = "SELECT equipment_name FROM station_tab WHERE gp_model = '" + str(cache.get('current_model')) + "'"
        result = sql_list(SQL)
        print(result)
        Tag = False
        for it in result:
            if it[0] == name:
                Tag = True


        SQL = " delete from equipment_tab where id= " + id + ""
        print(SQL)
        if not sql_execute(SQL):
            raise Exception('SQL执行失败！')
        SQL = " delete from station_tab where equipment_name= '" + name + "'"
        print(SQL)
        if not sql_execute(SQL):
            raise Exception('SQL执行失败！')

        # print(SQL)
        meta = {
            "msg": "删除成功!",
            "result": "OK"
        }
        backdata = {
            "data": {},
            "meta": meta,
        }

        if Tag:
            SQL = "SELECT * FROM station_tab WHERE gp_model = '" + cache.get('current_model') + "'"
            print(SQL)
            data = easy_sql_reader(SQL)
            print(data)
            # EquipNumGrop
            data = EquipNumGroup_Ini(data)

            # Equip_Status
            equip_status = cache.get('Equip_Status')
            print(">>>>>>")
            print(equip_status)
            for i in range(len(equip_status)):
                if equip_status[i]['EquipName'] == name:
                    equip_status.pop(i)
                    break
            print(equip_status)
            Cache_writer('Equip_Status', equip_status, None)

            # DeviceClass
            device_class = cache.get('DeviceClass')
            print(">>>>>>")
            print(device_class)
            for i in range(len(device_class)):
                if device_class[i]['EquipName'] == name:
                    device_class.pop(i)
                    break
            print(device_class)
            Cache_writer('DeviceClass', device_class, None)

        return HttpResponse(List_Json(backdata))

    except Exception as err:
        print(err)
        Data = {

        }
        meta = {
            "msg": str(err),
            "result": "NG"
        }

        backdata = {
            "data": Data,
            "meta": meta,
        }
        return HttpResponse(List_Json(backdata))


# --------------------------------添加设备列表----------------------------

@csrf_exempt
def AddDevice(request):
    try:
        Data = {}
        meta = {}
        equipment_name = request.POST.get('equipment_name', '')
        equipment_num = request.POST.get('equipment_num', '')
        equipment_ip = request.POST.get('equipment_ip', '')
        equipment_serial = request.POST.get('equipment_serial', '')

        if equipment_name == '' or equipment_num == '' or equipment_ip == '' or equipment_serial == '':
            Data = {
                "equipment_name": request.POST.get('equipment_name', ''),
                "equipment_num": request.POST.get('equipment_num', ''),
                "equipment_ip": request.POST.get('equipment_ip', ''),
                "equipment_serial": request.POST.get('equipment_serial', ''),
            }
            meta = {
                "msg": "信息不可为空",
                "result": "NG"
            }
            backdata = {
                "data": Data,
                "meta": meta,
            }
            return HttpResponse(List_Json(backdata))
        print(">>>>>>>")
        SQL = "select id from equipment_tab where equipment_name='" + equipment_name + "' or equipment_num='" + equipment_num + "' or equipment_serial='" + equipment_serial + "'"
        if not sql_execute(SQL):
            raise Exception('SQL执行失败！')
        print(SQL)
        data1 = sql_list_first(SQL)
        print(data1)
        if data1:

            meta = {
                "msg": "已经包含重复属性的设备！！！!",
                "result": "NG"
            }
        else:

            SQL = "INSERT INTO equipment_tab(equipment_name,equipment_num,equipment_ip,equipment_serial)VALUES ('" + equipment_name + "','" + equipment_num + "','" + equipment_ip + "','" + equipment_serial + "')"
            print(SQL)

            if not sql_execute(SQL):
                raise Exception('SQL执行失败！')

            # 在新设备添加的时候，型号默认当前使用的Model
            # SQL = "INSERT INTO station_tab(equipment_name,equipment_num,equipment_ip,equipment_serial,gp_model)VALUES ('" + equipment_name + "','" + equipment_num + "','" + equipment_ip + "','" + equipment_serial + "','" + str(cache.get('current_model')) + "')"
            # if not sql_execute(SQL):
            #     raise Exception('SQL执行失败！')
            # print(SQL)

            meta = {
                "msg": "添加设备成功!",
                "result": "OK"
            }

        backdata = {
            "data": {
                "equipment_name": request.POST.get('equipment_name', ''),
                "equipment_num": request.POST.get('equipment_num', ''),
                "equipment_ip": request.POST.get('equipment_ip', ''),
                "equipment_serial": request.POST.get('equipment_serial', ''),
            },
            "meta": meta,
        }

        return HttpResponse(List_Json(backdata))

    except Exception as err:
        Data = {
            "equipment_name": request.POST.get('equipment_name', ''),
            "equipment_num": request.POST.get('equipment_num', ''),
            "equipment_ip": request.POST.get('equipment_ip', ''),
            "equipment_serial": request.POST.get('equipment_serial', ''),
        }
        meta = {
            "msg": "添加设备" + request.POST.get('equipment_name', '') + "失败",
            "result": "NG"
        }

        backdata = {
            "data": Data,
            "meta": meta,
        }
        print(err)
        return HttpResponse(List_Json(backdata))


# --------------------------------获取某个设备信息----------------------------
@csrf_exempt
def deviceid(request):
    try:
        id = request.GET.get('localid', '')

        print(id)

        SQL = "select id,equipment_name,equipment_num,equipment_ip,equipment_serial from equipment_tab where id= " + id + ""

        print(SQL)
        data = easy_sql_reader1(SQL)

        # data = aview_easy_sql_reader_page1(SQL)
        print(data)
        meta = {
            "msg": "获取设备信息成功!",
            "result": "OK"
        }
        backdata = {
            "data": data,
            "meta": meta,
        }

        # print(backdata)
        # print(SQL)
        print(List_Json(backdata))
        return HttpResponse(List_Json(backdata))

    except Exception as err:
        Data = {

        }
        meta = {
            "msg": "获取用户信息失败",
            "result": "NG"
        }

        backdata = {
            "data": Data,
            "meta": meta,
        }
        # print(err)
        return HttpResponse(List_Json(backdata))


# --------------------------------修改设备信息----------------------------
@csrf_exempt
def EditDeviceInfo(request):
    try:
        print("EditDeviceInfo>>>>>>>>>>>>>>")
        print(request.POST)
        # 存放数据库属性不存在的值
        First_list = {}
        # 存放从前端传过来的值
        re_list = {}
        id = request.POST.get('id', '')

        equipment_num = request.POST.get('equipment_num', '')
        re_list["equipment_num"] = equipment_num
        equipment_ip = request.POST.get('equipment_ip', '')
        re_list["equipment_ip"] = equipment_ip
        equipment_serial = request.POST.get('equipment_serial', '')
        re_list["equipment_serial"] = equipment_serial
        #   equipment_name要放到最后使用，否则在更新 station_tab 时用equipment_name做WHERE判断会导致其余内容赋值失败
        equipment_name = request.POST.get('equipment_name', '')
        re_list["equipment_name"] = equipment_name
        print(re_list)

        device_class = cache.get('DeviceClass')

        for key, value in re_list.items():
            if value != "":
                # 同一台电脑可开多个工位软件，允许 equipment_ip 重复
                if key == "equipment_ip":
                    First_list[key] = value
                    continue
                SQL = "select id from equipment_tab where  " + key + "='" + value + "' and id != '" + id + "'"
                print(SQL)
                data1 = sql_list_first(SQL)
                if data1:
                    raise Exception("设备已经包含重复属性" + value + "！！！")
                else:
                    First_list[key] = value
                    # print(First_list)

        SQL = "select equipment_name from equipment_tab where id='" + str(id) + "'"
        print(SQL)
        data1 = sql_list_first(SQL)
        print(data1)
        if data1 is None:
            raise Exception("id:" + str(id) + "无设备对应")
        SQL = "SELECT * FROM equipment_tab WHERE id= '" + id + "'"
        print(SQL)
        result = sql_list(SQL)
        print(result)
        re_list["equipment_name"] = result[0][2]
        re_list["equipment_num"] = result[0][3]
        re_list["equipment_ip"] = result[0][4]
        re_list["equipment_serial"] = result[0][5]
        print(re_list)
        for it in device_class:
            if it['EquipStatus'] and it['EquipName'] == re_list["equipment_name"]:
                raise Exception("设备:" + re_list["equipment_name"] + "已经连接，请断开后再修改")

        for key, value in First_list.items():
            SQL = "UPDATE equipment_tab SET " + key + "='" + value + "' WHERE id= '" + id + "'"
            print(SQL)
            if not sql_execute(SQL):
                raise Exception('修改设备信息失败！')
            SQL = "UPDATE station_tab SET " + key + "='" + value + "' WHERE equipment_name='" + data1[0] + "'"
            print(SQL)
            if not sql_execute(SQL):
                raise Exception('修改设备信息失败！')
        SQL = "SELECT gp_model from station_tab WHERE equipment_name = '" + equipment_name + "'"
        print(SQL)
        result = sql_list(SQL)
        print(result)
        # equip_connect = cache.get('EquipConnect', default=None)
        # SQL = "SELECT equipment_ip from equipment_tab WHERE id = '" + id + "'"
        # print(SQL)
        # result = sql_list(SQL)
        # print(result)
        # for it in equip_connect:
        #     if result[0] == it['EquipIP']:
        for it in result:
            if cache.get('current_model') == it[0]:
                print(it[0])
                SQL = "SELECT * FROM station_tab WHERE gp_model = '" + cache.get('current_model') + "'"
                print(SQL)
                data = easy_sql_reader(SQL)

                # EquipNumGrop
                EquipNumGroup_Ini(data)

                # Equip_Status
                equip_status = cache.get('Equip_Status')
                print(">>>>>>>>Equip_Status")
                print(equip_status)
                for it in equip_status:
                    if it['EquipName'] == data1[0]:
                        it['EquipName'] = equipment_name
                        it['EquipNumber'] = equipment_num
                Cache_writer('Equip_Status', equip_status, None)
                print(cache.get('Equip_Status'))

                # DeviceClass
                equip_connect = cache.get('EquipConnect')
                device_class = cache.get('DeviceClass')
                print(">>>>>>>>DeviceClass")
                print(device_class)
                for it in device_class:
                    if it['EquipName'] == data1[0]:
                        it['EquipName'] = equipment_name
                        it['EquipNumber'] = equipment_num
                        it['EquipIP'] = equipment_ip
                        it['EquipSerial'] = equipment_serial

                ApplyEquipConnectStatus(device_class, equip_connect)
                Cache_writer('DeviceClass', device_class, None)
                print(cache.get('DeviceClass'))

        # if cache.get('current_model') == result[0][0]:
        #     SQL = "SELECT * FROM station_tab WHERE gp_model = '" + cache.get('current_model') + "'"
        #     print(SQL)
        #     data = easy_sql_reader(SQL)
        #
        #     # EquipNumGrop
        #     EquipNumGroup_Ini(data)
        #
        #     # Equip_Status
        #     equip_status = cache.get('Equip_Status')
        #     print(">>>>>>>>Equip_Status")
        #     print(equip_status)
        #     for it in equip_status:
        #         if it['EquipName'] == data1[0]:
        #             it['EquipName'] = equipment_name
        #             it['EquipNumber'] = equipment_num
        #     Cache_writer('Equip_Status', equip_status, None)
        #     print(cache.get('Equip_Status'))
        #
        #     # DeviceClass
        #     device_class = cache.get('DeviceClass')
        #     print(">>>>>>>>DeviceClass")
        #     print(device_class)
        #     for it in device_class:
        #         if it['EquipName'] == data1[0]:
        #             it['EquipName'] = equipment_name
        #             it['EquipNumber'] = equipment_num
        #             it['EquipIP'] = equipment_ip
        #             it['EquipSerial'] = equipment_serial
        #     Cache_writer('DeviceClass', device_class, None)
        #     print(cache.get('DeviceClass'))

        meta = {
            "msg": "修改设备信息成功!",
            "result": "OK"
        }
        backdata = {
            "data": {
                "id": id,
            },
            "meta": meta,
        }

        print(backdata)
        # print(SQL)
        # print(List_Json(backdata))
        return HttpResponse(List_Json(backdata))

    except Exception as err:
        print(str(err))
        meta = {
            "msg": str(err).replace("\"", ""),
            "result": "NG"
        }

        backdata = {
            "data": {
                "id": id,
            },
            "meta": meta,
        }
        print(backdata)
        return HttpResponse(List_Json(backdata))

def CheckDevice(request):
    try:
        equipstatus = cache.get('Equip_Status')
        checkdevice = cache.get('CheckDevice')

        meta = {
            "msg": "获取设备列表成功!",
            "result": "OK"
        }
        backdata = {
            "data": equipstatus,
            "meta": meta,
        }
        log.info(
            "点检设备列表获取成功 status=%s check=%s",
            len(equipstatus) if equipstatus else 0,
            len(checkdevice) if checkdevice else 0,
        )
        return HttpResponse(List_Json(backdata))

    except Exception as err:
        Data = {

        }
        meta = {
            "msg": str(err),
            "result": "NG"
        }

        backdata = {
            "data": Data,
            "meta": meta,
        }
        return HttpResponse(List_Json(backdata))

def EditCheckDevice(request):
    try:
        checklist = request.POST.get('checklist', '')
        print("checklist:")
        print(checklist)
        print(type(checklist))
        checklist = json.loads(checklist)
        print(type(checklist))
        stno_list = []
        for item in checklist:
            stno_list.append(item['EquipNumber'])
        print(stno_list)

        # 将点检的机台信息更新到 equipstatus中
        equipstatus = cache.get('Equip_Status')
        for it1 in equipstatus:
            it1['CheckDevice'] = "/"
        for it1 in equipstatus:
            for it2 in stno_list:
                if it1['EquipNumber'] == it2:
                    it1['CheckDevice'] = "YES"
        Cache_writer('Equip_Status', equipstatus, None)

        # 更新单独存储点检机台的表
        Cache_writer('CheckDevice', stno_list, None)

        # 更新checklist 到ini文件
        # ------------------保存点检数据到 ini 文件中 --------------------
        filepath = GetFilePath("SoftWare.ini")
        conf = ConfigParser()  # 需要实例化一个ConfigParser对象
        conf.read(filepath)  # 需要添加上config.ini的路径，不需要open打开，直接给文件路径就读取，也可以指定encoding='utf-8'
        print(conf['CommonUse']['CheckDevice'])
        conf.set('CommonUse', 'CheckDevice', str(stno_list))
        with open(filepath, 'w', encoding='utf-8') as f:
            conf.write(f)
        print(conf['CommonUse']['CheckDevice'])

        meta = {
            "msg": "修改点检设备列表成功!",
            "result": "OK"
        }
        backdata = {
            "data": equipstatus,
            "meta": meta,
        }

        print(backdata)
        # print(SQL)
        return HttpResponse(List_Json(backdata))
    except Exception as err:
        Data = {

        }
        meta = {
            "msg": str(err),
            "result": "NG"
        }

        backdata = {
            "data": Data,
            "meta": meta,
        }
        return HttpResponse(List_Json(backdata))
# ---------------------------------设备控制------------------------------

# --------------获取型号&设备列表-------------------
def GetLocalModel_Equipment(request): # equipstatus 代表连接状态未连接为0，连接为1.  后端内是用True 和 False来记录1
    try:
        back_data = {}
        back_data_list = []
        back_meta = {}

        # filepath = GetFilePath("SoftWare.ini")
        # conf = ConfigParser()  # 需要实例化一个ConfigParser对象
        # conf.read(filepath)  # 需要添加上config.ini的路径，不需要open打开，直接给文件路径就读取，也可以指定encoding='utf-8'
        # curren_model = conf['CommonUse']['CurrentModel']  # 读取user段的name变量的值，字符串格式
        # print(curren_model)
        current_model = cache.get('current_model')
        current_order = cache.get('current_order')
        SQL = "SELECT equipment_name, equipment_num, equipment_ip, equipment_serial FROM station_tab WHERE gp_model ='" + current_model + "'"
        cs = connection.cursor()
        cs.execute(SQL)
        result = cs.fetchall()
        cs.close()
        device_class = cache.get('DeviceClass')
        equipstatus = cache.get('Equip_Status')
        checkdevice = cache.get('CheckDevice', default=None)


        for it in result:
            back_data_list.append(
                {"equipment_name": it[0], "equipment_num": it[1], "equipment_ip": it[2], "equipment_serial": it[3],
                 "equipStatus": 0, "equipOrder": "NA", "equipResult": "NA", "checkDevice": "/", "checkResult": ""})
        # 冒泡
        n = len(back_data_list)
        for i in range(n):
            # Last i elements are already in place
            for j in range(0, n - i - 1):
                if int(back_data_list[j]['equipment_serial']) > int(back_data_list[j + 1]['equipment_serial']):
                    back_data_list[j], back_data_list[j + 1] = back_data_list[j + 1], back_data_list[j]

        for it1 in device_class:
            if it1["EquipStatus"] is True:
                for it2 in back_data_list:
                    if it1["EquipName"] == it2["equipment_name"]:
                        it2["equipStatus"] = 1

        for it1 in equipstatus:
            for it2 in back_data_list:
                if it1['EquipNumber'] == it2['equipment_num']:
                    it2['equipOrder'] = it1['EquipOrder']
                    it2['equipResult'] = it1['EquipResult']

        for it1 in checkdevice:
            for it2 in back_data_list:
                if it1 == it2['equipment_num']:
                    it2['checkDevice'] = 'YES'


        back_data = {
            "localmodel": current_model,
            "localorder": current_order,
            "data": back_data_list
        }
        back_meta = {
            "msg": "获取成功",
            "result": "OK"
        }
    except Exception as err:
        print(str(err))
        back_meta = {
            "msg": str(err).replace("\"", ""),
            "result": "NG"
        }

    backdata = {
        "data": back_data,
        "meta": back_meta,
    }
    log.info("GetLocalModel_Equipment 获取成功 count=%s", len(back_data_list) if back_data_list else 0)
    return HttpResponse(List_Json(backdata))


# --------------功能按钮-------------------
def Function_Btn(request):
    # from django.core.cache import cache
    try:
        back_data = {}
        back_meta = {
            "msg": "操作成功",
            "result": "OK"
        }
        equipnumgroup = cache.get('EquipNumGroup')
        equip_status = cache.get('Equip_Status')
        device_class = cache.get('DeviceClass')
        equip_time = cache.get('EquipTime')
        type_name = request.POST.get('Function_Type', '')
        condition = request.POST.get('Condition', '')


        print(">>>>>>>>>>>>>>>Function_Type :" + str(type_name))
        match type_name:
            case "0":
                print("start")                 #开始    确保对复位成功的设备执行开始操作
                back_data_list = []
                send_tag = True
                if condition == "YES":
                    print("YES")
                    # 检查是否可以群发  机台的状态是否符合条件
                    equip_status = cache.get('Equip_Status')
                    equip_time = cache.get('EquipTime', default=None)
                    equip_time_st = cache.get('EquipTimeST', default=None)
                    if equip_time['Status'] == 0:   # 正常生产: start(点检) -- start
                        #查设备状态进行卡控
                        for item in equip_status:
                            if item['CheckDevice'].upper() == "YES":
                                if item['EquipOrder'].upper() != 'CHECKDEVICE' or item['EquipResult'] != 'OK':
                                    msg = "设备不符合操作要求:" + item['EquipName'] + "," + item[
                                        'EquipNumber'] + "," + item['EquipOrder'] + "," + item['EquipResult']
                                    raise Exception(msg)
                            elif item['CheckDevice'].upper() == "/":
                                if item['EquipOrder'].upper() != 'RESET' or item['EquipResult'] != 'OK':
                                    if item['EquipOrder'].upper() != 'START':
                                        msg = "设备不符合操作要求:" + item['EquipName'] + "," + item[
                                            'EquipNumber'] + "," + item['EquipOrder'] + "," + item['EquipResult']
                                        raise Exception(msg)
                        # back_meta = {
                        #     "msg": "当前状态已经是开始",
                        #     "result": "OK"
                        # }
                    elif equip_time['Status'] == 1:   # remodel(换 复 点检) -- start
                        # 未完成 待补充   换型后: 复位-点检检测-开始
                        print("remodel(换 复 点检) -- start 未完成 待补充")

                        # equip_status = cache.get('Equip_Status')
                        for item in equip_status:
                            if item['CheckDevice'].upper() == "YES":
                                if item['EquipOrder'].upper() != 'CHECKDEVICE' or item['EquipResult'] != 'OK':
                                    msg = "设备不符合操作要求:" + item['EquipName'] + "," + item[
                                        'EquipNumber'] + "," + item['EquipOrder'] + "," + item['EquipResult']
                                    raise Exception(msg)
                            elif item['CheckDevice'].upper() == "/":
                                if item['EquipOrder'].upper() != 'RESET' or item['EquipResult'] != 'OK':
                                    if item['EquipOrder'].upper() != 'START':
                                        msg = "设备不符合操作要求:" + item['EquipName'] + "," + item[
                                            'EquipNumber'] + "," + item['EquipOrder'] + "," + item['EquipResult']
                                        raise Exception(msg)

                    elif equip_time['Status'] == 2:   # stop -- start
                        for item in equip_status:
                            if item['EquipOrder'].upper() != 'STOP' or item['EquipResult'] != 'OK':
                                if item['EquipOrder'].upper() != 'RESET' or item['EquipResult'] != 'OK':
                                    msg = "设备不符合操作要求:" + item['EquipName'] + "," + item['EquipNumber'] + "," + item['EquipOrder'] + "," + item['EquipResult']
                                    raise Exception(msg)
                    elif equip_time['Status'] == 3:   # error -- start
                        msg = "当前存在设备Error,请排除故障后开始"
                        raise Exception(msg)

                    # #记录时间信息
                    # for item in equipnumgroup:
                    #     Time_Record(item, 0, False)

                    # 群发复位信息给station   Send_Message()
                    data = {
                        "Command": "0x07",
                        "Instruct": "start"
                    }
                    # 对所有机台群发指令
                    Send_Message(data)
                    # 最多等待3秒 等待机台回复
                    wait_tag = 3
                    send_tag = True
                    while wait_tag > 0:
                        send_tag = True
                        equip_status = cache.get('Equip_Status')
                        for item in equip_status:
                            if item['EquipOrder'].upper() != 'START' or item['EquipResult'] != 'OK':
                                send_tag = False
                                break
                        if send_tag is True:
                            break
                        wait_tag -= 1
                        print("sleep")
                        time.sleep(1)

                    # if send_tag is True:
                    #     # 记录时间信息
                    #     for item in equipnumgroup:
                    #         Time_Record(item, 0, False)

                    if send_tag is True:
                        back_meta = {
                            "msg": "开始成功",
                            "result": "OK"
                        }
                    else:
                        back_meta = {
                            "msg": "部分机台开始失败，请检查",
                            "result": "NG"
                        }


                elif condition == "NO":
                    print("NO")
                    equips_list = request.POST.get('EquipList', '')
                    print(type(equips_list))
                    # equips_list = eval(equips_list)
                    equips_list = json.loads(equips_list)
                    print(type(equips_list))

                    print(">>>>>equips_list")
                    print(equips_list)
                    # 检测返回的设备的状态是否符合条件
                    # 未完成 待完善      换型后: 复位-点检检测-开始、      正常生产: 点检-开始、    停机:stop-开始
                    equip_status = cache.get('Equip_Status')
                    # equip_time = cache.get('EquipTime', default=None)
                    # if equip_time['Status'] == 2:


                    for item1 in equip_status:
                        for item2 in equips_list:
                            # print(type(item2))
                            # print(item1['EquipNumber'])
                            # print(item2['equipment_num'])
                            if item1['EquipNumber'] == item2['equipment_num']:
                                if item1['CheckDevice'].upper() == "YES":
                                    if item1['EquipOrder'].upper() != 'CHECKDEVICE' or item1['EquipResult'] != 'OK':
                                        if item1['EquipOrder'].upper() != 'START':
                                            msg = "设备不符合操作要求:" + item1['EquipName'] + "," + item1[
                                                'EquipNumber'] + "," + item1['EquipOrder'] + "," + item1['EquipResult']
                                        raise Exception(msg)
                                elif item1['CheckDevice'].upper() == "/":
                                    if item1['EquipOrder'].upper() != 'RESET' or item1['EquipResult'] != 'OK':
                                        if item1['EquipOrder'].upper() != 'START':
                                            msg = "设备不符合操作要求:" + item1['EquipName'] + "," + item1[
                                                'EquipNumber'] + "," + item1['EquipOrder'] + "," + item1['EquipResult']
                                            raise Exception(msg)
                                # if item1['EquipOrder'].upper() != 'RESET' or item1['EquipResult'] != 'OK':
                                #     msg = "设备不符合操作要求:" + item1['EquipName'] + "," + item1[
                                #         'EquipNumber'] + "," + item1['EquipOrder'] + "," + item1['EquipResult']
                                #     raise Exception(msg)


                    # 初始化机台信息/机台重复操作预防
                    # 根据返回的设备列表下发指令
                    for it in equips_list:
                        topic = "Msg2Station/" + it['equipment_num']
                        data = {
                            "Command": "0x07",
                            "Instruct": "start"
                        }
                        publish(topic, data)
                    # 最多等待3秒 等待机台回复
                    wait_tag = 3
                    send_tag = True
                    while wait_tag > 0:
                        send_tag = True
                        equip_status = cache.get('Equip_Status')
                        for item1 in equip_status:
                            for item2 in equips_list:
                                if item1['EquipNumber'] == item2['equipment_num']:
                                    if item1['EquipOrder'].upper() != 'START' or item1['EquipResult'] != 'OK':
                                        send_tag = False
                                        break
                            if send_tag is False:
                                break
                        if send_tag is True:
                            break
                        wait_tag -= 1
                        print("sleep")
                        time.sleep(1)

                # back_data_list 状态同步，返回换型结果给前端
                print("#----------------------返回开始结果给前端----------------------")
                if send_tag is True:
                    back_meta = {
                        "msg": "开始成功",
                        "result": "OK"
                    }
                else:
                    back_meta = {
                        "msg": "部分机台开始失败，请检查",
                        "result": "NG"
                    }

                for it in device_class:
                    status_num = 0
                    if it["EquipStatus"]:
                        status_num = 1
                    data = {
                        "equipment_name": it["EquipName"], "equipment_num": it["EquipNumber"], "equipment_ip": it['EquipIP'], "equipment_serial": it['EquipSerial'],
                        "equipOrder": "", "equipResult": "", "checkDevice": "/", "checkResult": "",
                        "equipStatus": status_num, "equipError": it['EquipError']
                    }
                    # 获取最新的设备状态
                    equip_status = cache.get('Equip_Status')
                    checkdevice = cache.get('CheckDevice', default=None)
                    print(equip_status)
                    for it1 in equip_status:
                        if it1['EquipNumber'] == data['equipment_num']:
                            data['equipOrder'] = it1['EquipOrder']
                            data['equipResult'] = it1['EquipResult']
                            data['checkDevice'] = it1['CheckDevice']
                            data['checkResult'] = it1['CheckResult']
                    for it2 in checkdevice:
                        if it2 == data['equipment_num']:
                            data['checkDevice'] = 'YES'
                    back_data_list.append(data)
                back_data = {
                    "localmodel": cache.get('current_model'),
                    "data": back_data_list,
                    # "table": [{"ProductSum": "", "ProductQuantity": "", "Accept": "", "Yield": ""}]
                }
                print(">>>>>>>back_data")
                print(back_data)
            case "1":
                print("stop")  # 停止  确保对所有设备执行停止操作
                back_data_list = []
                send_tag = True
                if condition == "YES":
                    print("YES")
                    equip_status = cache.get('Equip_Status')
                    for item in equip_status:
                        if item['EquipOrder'].upper() == "ERROR":
                            msg = "设备里存在ERROR 无法停止"
                            raise Exception(msg)

                    # for item in equip_status:
                    #     if item['EquipOrder'].upper() != "START":
                    #         msg = "全部设备开始 才可使用一键停止"
                    #         raise Exception(msg)

                    # 群发信息给station   Send_Message()
                    data = {
                        "Command": "0x08",
                        "Instruct": "stop"
                    }

                    # 记录时间信息
                    # for item in equip_status:
                    #     Time_Record(item['EquipNumber'], 2, False)

                    # equipnumgroup = cache.get('EquipNumGroup')
                    # for it in equipnumgroup:
                    #     Time_Record(it, 2, False)
                    # Time_Record("ST00", 2, False)

                    # 对所有机台群发指令
                    Send_Message(data)
                    # 最多等待3秒 等待机台回复
                    wait_tag = 10
                    send_tag = True
                    while wait_tag > 0:
                        send_tag = True
                        equip_status = cache.get('Equip_Status')
                        for item in equip_status:
                            if item['EquipOrder'].upper() != 'STOP' or item['EquipResult'] != 'OK':
                                send_tag = False
                                break
                        if send_tag is True:
                            break
                        wait_tag -= 1
                        print("sleep")
                        time.sleep(1)

                elif condition == "NO":
                    print("NO")
                    equips_list = request.POST.get('EquipList', '')
                    print(type(equips_list))
                    equips_list = json.loads(equips_list)
                    print(type(equips_list))

                    print(">>>>>equips_list")
                    # print(equips_list)

                    # # 记录时间
                    # for it in equips_list:
                    #     Time_Record(it['equipment_num'], 2, True)

                    # 根据返回的设备列表下发指令
                    for it in equips_list:
                        topic = "Msg2Station/" + it['equipment_num']
                        data = {
                            "Command": "0x08",
                            "Instruct": "stop"
                        }
                        publish(topic, data)
                    # 最多等待3秒 等待机台回复
                    wait_tag = 10
                    send_tag = True
                    while wait_tag > 0:
                        send_tag = True
                        equip_status = cache.get('Equip_Status')
                        for item1 in equip_status:
                            for item2 in equips_list:
                                if item1['EquipNumber'] == item2['equipment_num']:
                                    if item1['EquipOrder'].upper() != 'STOP' or item1['EquipResult'] != 'OK':
                                        send_tag = False
                                        break
                            if send_tag is False:
                                break
                        if send_tag is True:
                            break
                        wait_tag -= 1
                        print("sleep")
                        time.sleep(1)

                # back_data_list 状态同步，返回换型结果给前端
                print("#----------------------返回停止结果给前端----------------------")
                if send_tag is True:
                    back_meta = {
                        "msg": "停止成功",
                        "result": "OK"
                    }
                else:
                    back_meta = {
                        "msg": "部分机台停止失败，请检查",
                        "result": "NG"
                    }

                for it in device_class:
                    status_num = 0
                    if it["EquipStatus"]:
                        status_num = 1
                    data = {
                        "equipment_name": it["EquipName"], "equipment_num": it["EquipNumber"], "equipment_ip": it['EquipIP'], "equipment_serial": it['EquipSerial'],
                        "equipOrder": "", "equipResult": "", "checkDevice": "/", "checkResult": "",
                        "equipStatus": status_num, "equipError": it['EquipError']
                    }
                    # 获取最新的设备状态
                    equip_status = cache.get('Equip_Status')
                    checkdevice = cache.get('CheckDevice', default=None)
                    print(equip_status)
                    for it1 in equip_status:
                        if it1['EquipNumber'] == data['equipment_num']:
                            data['equipOrder'] = it1['EquipOrder']
                            data['equipResult'] = it1['EquipResult']
                            data['checkDevice'] = it1['CheckDevice']
                            data['checkResult'] = it1['CheckResult']
                    for it2 in checkdevice:
                        if it2 == data['equipment_num']:
                            data['checkDevice'] = 'YES'
                    back_data_list.append(data)
                back_data = {
                    "localmodel": cache.get('current_model'),
                    "data": back_data_list,
                    # "table": [{"ProductSum": "", "ProductQuantity": "", "Accept": "", "Yield": ""}]
                }
                print(">>>>>>>back_data")
                print(back_data)
            case "2":
                print("reset")              #复位  确保对换型成功的设备执行复位操作
                back_data_list = []
                send_tag = True
                if condition == "YES":
                    print("YES")
                    # 检查是否可以群发  机台的状态是否符合条件

                    equip_status = cache.get('Equip_Status')
                    for item in equip_status:
                        # 跳过治具校验，换型后/停止后 就可复位
                        # if item['EquipOrder'].upper() != 'CHECKCARRIER' or item['EquipResult'] != 'OK':
                        if item['EquipOrder'].upper() != 'REMODEL' or item['EquipResult'] != 'OK':
                            if item['EquipOrder'].upper() != 'STOP' or item['EquipResult'] != 'OK':
                                if item['EquipOrder'].upper() != 'RESET':
                                    msg = "设备不符合操作要求:" + item['EquipName'] + "," + item[
                                        'EquipNumber'] + "," + item['EquipOrder'] + "," + item['EquipResult']
                                    raise Exception(msg)
                    # 群发复位信息给station   Send_Message()
                    data = {
                        "Command": "0x09",
                        "Instruct": "reset"
                    }
                    # 对所有机台群发指令
                    Send_Message(data)
                    # 最多等待120秒 等待机台回复
                    wait_tag = 120
                    send_tag = True
                    while wait_tag > 0:
                        send_tag = True
                        equip_status = cache.get('Equip_Status')
                        for item in equip_status:
                            if item['EquipOrder'].upper() != 'RESET' or item['EquipResult'] != 'OK':
                                send_tag = False
                                break
                        if send_tag is True:
                            break
                        wait_tag -= 1
                        print("sleep")
                        time.sleep(1)

                elif condition == "NO":
                    print("NO")
                    equips_list = request.POST.get('EquipList', '')
                    print(type(equips_list))
                    # equips_list = eval(equips_list)
                    equips_list = json.loads(equips_list)
                    print(type(equips_list))

                    print(">>>>>equips_list")
                    print(equips_list)
                    # 检测返回的设备的状态是否符合条件
                    equip_status = cache.get('Equip_Status')
                    for item1 in equip_status:
                        for item2 in equips_list:
                            print(type(item2))
                            print(item1['EquipNumber'])
                            print(item2['equipment_num'])
                            if item1['EquipNumber'] == item2['equipment_num']:
                                if item1['EquipOrder'].upper() != 'CHECKCARRIER' or item1['EquipResult'] != 'OK':
                                    if item1['EquipOrder'].upper() != 'RESET':
                                        msg ="设备不符合操作要求:" + item1['EquipName'] + "," + item1['EquipNumber'] + "," + item1['EquipOrder'] + "," + item1['EquipResult']
                                        raise Exception(msg)

                    # 初始化机台信息/机台重复操作预防
                    # 根据返回的设备列表下发指令
                    for it in equips_list:
                        topic = "Msg2Station/" + it['equipment_num']
                        data = {
                            "Command": "0x09",
                            "Instruct": "reset"
                        }
                        publish(topic, data)
                    # 最多等待3秒 等待机台回复
                    wait_tag = 10
                    send_tag = True
                    while wait_tag > 0:
                        send_tag = True
                        equip_status = cache.get('Equip_Status')
                        for item1 in equip_status:
                            for item2 in equips_list:
                                if item1['EquipNumber'] == item2['equipment_num']:
                                    if item1['EquipOrder'].upper() != 'RESET' or item1['EquipResult'] != 'OK':
                                        send_tag = False
                                        break
                            if send_tag is False:
                                break
                        if send_tag is True:
                            break
                        wait_tag -= 1
                        print("sleep")
                        time.sleep(1)

                # back_data_list 状态同步，返回换型结果给前端
                print("#----------------------返回复位结果给前端----------------------")
                if send_tag is True:
                    back_meta = {
                        "msg": "复位成功",
                        "result": "OK"
                    }
                else:
                    back_meta = {
                        "msg": "部分机台复位失败，请检查",
                        "result": "NG"
                    }
                for it in device_class:
                    status_num = 0
                    if it["EquipStatus"]:
                        status_num = 1
                    data = {
                        "equipment_name": it["EquipName"], "equipment_num": it["EquipNumber"], "equipment_ip": it['EquipIP'], "equipment_serial": it['EquipSerial'],
                        "equipOrder": "", "equipResult": "", "checkDevice": "/", "checkResult": "",
                        "equipStatus": status_num, "equipError": it['EquipError']
                    }
                    # 获取最新的设备状态
                    checkdevice = cache.get('CheckDevice', default=None)
                    equip_status = cache.get('Equip_Status')
                    print(equip_status)
                    for it1 in equip_status:
                        if it1['EquipNumber'] == data['equipment_num']:
                            data['equipOrder'] = it1['EquipOrder']
                            data['equipResult'] = it1['EquipResult']
                            data['checkDevice'] = it1['CheckDevice']
                            data['checkResult'] = it1['CheckResult']

                    for it2 in checkdevice:
                        if it2 == data['equipment_num']:
                            data['checkDevice'] = 'YES'
                    back_data_list.append(data)
                back_data = {
                    "localmodel": cache.get('current_model'),
                    "data": back_data_list,
                    # "table": [{"ProductSum": "", "ProductQuantity": "", "Accept": "", "Yield": ""}]
                }
                print(">>>>>>>back_data")
                print(back_data)

            case "3":
                print("clean")  # 清空  确保对所有设备执行清空操作
                back_data_list = []
                send_tag = True
                if condition == "YES":
                    print("YES")
                    # 群发复位信息给station   Send_Message()
                    data = {
                        "Command": "0x06",
                        "Instruct": "clean"
                    }
                    # 对所有机台群发指令
                    Send_Message(data)
                    # 最多等待3秒 等待机台回复
                    wait_tag = 10
                    send_tag = True
                    while wait_tag > 0:
                        send_tag = True
                        equip_status = cache.get('Equip_Status')
                        # print(equip_status)
                        for item in equip_status:
                            if item['EquipOrder'].upper() != 'CLEAN' or item['EquipResult'] != 'OK':
                                send_tag = False
                                break
                        if send_tag is True:
                            break
                        wait_tag -= 1
                        print("sleep")
                        time.sleep(1)

                elif condition == "NO":
                    print("NO")
                    equips_list = request.POST.get('EquipList', '')
                    print(type(equips_list))
                    equips_list = json.loads(equips_list)
                    print(type(equips_list))

                    print(">>>>>equips_list")
                    print(equips_list)
                    # 根据返回的设备列表下发指令
                    for it in equips_list:
                        topic = "Msg2Station/" + it['equipment_num']
                        data = {
                            "Command": "0x06",
                            "Instruct": "clean"
                        }
                        publish(topic, data)
                    # 最多等待3秒 等待机台回复
                    wait_tag = 10
                    send_tag = True
                    while wait_tag > 0:
                        send_tag = True
                        equip_status = cache.get('Equip_Status')
                        # print(equip_status)
                        for item1 in equip_status:
                            for item2 in equips_list:
                                if item1['EquipNumber'] == item2['equipment_num']:
                                    if item1['EquipOrder'].upper() != 'CLEAN' or item1['EquipResult'] != 'OK':
                                        send_tag = False
                                        break
                            if send_tag is False:
                                break
                        if send_tag is True:
                            break
                        wait_tag -= 1
                        print("sleep")
                        time.sleep(1)

                # back_data_list 状态同步，返回换型结果给前端
                print("#----------------------返回复位结果给前端----------------------")
                if send_tag is True:
                    back_meta = {
                        "msg": "清料成功",
                        "result": "OK"
                    }
                else:
                    back_meta = {
                        "msg": "部分机台清料失败，请检查",
                        "result": "NG"
                    }
                for it in device_class:
                    status_num = 0
                    if it["EquipStatus"]:
                        status_num = 1
                    data = {
                        "equipment_name": it["EquipName"], "equipment_num": it["EquipNumber"], "equipment_ip": it['EquipIP'], "equipment_serial": it['EquipSerial'],
                        "equipOrder": "", "equipResult": "",
                        "equipStatus": status_num, "equipError": it['EquipError']
                    }
                    # 获取最新的设备状态
                    equip_status = cache.get('Equip_Status')
                    print(equip_status)
                    for it1 in equip_status:
                        if it1['EquipNumber'] == data['equipment_num']:
                            data['equipOrder'] = it1['EquipOrder']
                            data['equipResult'] = it1['EquipResult']
                    back_data_list.append(data)
                back_data = {
                    "localmodel": cache.get('current_model'),
                    "data": back_data_list,
                    # "table": [{"ProductSum": "", "ProductQuantity": "", "Accept": "", "Yield": ""}]
                }
                print(">>>>>>>back_data")
                print(back_data)
            case "4":
                print("CheckCarrier")  # 治具确认(比对) 治具校验 下发机台操作人员对当前机种载具扫码录入
                back_data_list = []
                send_tag = True
                if condition == "YES":
                    print("YES")
                    # 检查是否可以群发  机台的状态是否符合条件
                    equip_status = cache.get('Equip_Status')
                    for item in equip_status:
                        if item['EquipOrder'].upper() != 'REMODEL' or item['EquipResult'] != 'OK':
                            if item['EquipOrder'].upper() != 'CHECKCARRIER':
                                msg = "设备不符合操作要求:" + item['EquipName'] + "," + item[
                                    'EquipNumber'] + "," + item['EquipOrder'] + "," + item['EquipResult']
                                raise Exception(msg)

                    # 群发复位信息给station   Send_Message()
                    data = {
                        "Command": "0x15",
                        "Message": ""
                    }
                    # 对所有机台群发指令
                    # Send_Message(data)
                    #只对第一台机器发治具确认指令
                    publish("Msg2Station/ST01", json.dumps(data))
                    # # 最多等待3秒 等待机台回复
                    # wait_tag = 10
                    # send_tag = True
                    # while wait_tag > 0:
                    #     send_tag = True
                    #     equip_status = cache.get('Equip_Status')
                    #     # print(equip_status)
                    #     for item in equip_status:
                    #         if item['EquipOrder'].upper() != 'CHECKCARRIER' or item['EquipResult'] != 'OK':
                    #             send_tag = False
                    #             break
                    #     if send_tag is True:
                    #         break
                    #     wait_tag -= 1
                    #     print("sleep")
                    #     time.sleep(1)


                elif condition == "NO":
                    print("NO")
                    equips_list = request.POST.get('EquipList', '')
                    print(type(equips_list))
                    equips_list = json.loads(equips_list)
                    print(type(equips_list))

                    print(">>>>>equips_list")
                    print(equips_list)

                    # 检查是否可以群发  机台的状态是否符合条件
                    equip_status = cache.get('Equip_Status')
                    for item1 in equips_list:
                        for item2 in equip_status:
                            if item1['equipment_num'] == item2['EquipNumber']:
                                if item2['EquipOrder'].upper() != 'REMODEL' or item2['EquipResult'] != 'OK':
                                    if item2['EquipOrder'].upper() != 'CHECKCARRIER':
                                        msg = "设备不符合操作要求:" + item2['EquipName'] + "," + item2[
                                            'EquipNumber'] + "," + item2['EquipOrder'] + "," + item2['EquipResult']
                                        raise Exception(msg)

                    # # 根据返回的设备列表下发指令
                    # for it in equips_list:
                    #     topic = "Msg2Station/" + it['equipment_num']
                    #     data = {
                    #         "Command": "0x15",
                    #         "Instruct": "CheckCarrier"
                    #     }
                    #     publish(topic, data)
                    # 只下发给第一台机器
                    data = {
                        "Command": "0x15",
                        "Message": ""
                    }
                    publish("Msg2Station/ST01", json.dumps(data))
                    # # 最多等待3秒 等待机台回复
                    # wait_tag = 10
                    # send_tag = True
                    # while wait_tag > 0:
                    #     send_tag = True
                    #     equip_status = cache.get('Equip_Status')
                    #     # print(equip_status)
                    #     for item1 in equip_status:
                    #         for item2 in equips_list:
                    #             if item1['EquipNumber'] == item2['equipment_num']:
                    #                 if item1['EquipOrder'].upper() != 'CHECK' or item1['EquipResult'] != 'OK':
                    #                     send_tag = False
                    #                     break
                    #         if send_tag is False:
                    #             break
                    #     if send_tag is True:
                    #         break
                    #     wait_tag -= 1
                    #     print("sleep")
                    #     time.sleep(1)

                # back_data_list 状态同步，返回换型结果给前端
                print("#----------------------返回治具确认结果给前端----------------------")
                back_meta = {
                    "msg": "已下发治具校验",
                    "result": "OK"
                }
                # if send_tag is True:
                #     back_meta = {
                #         "msg": "治具确认成功",
                #         "result": "OK"
                #     }
                # else:
                #     back_meta = {
                #         "msg": "部分机台治具确认失败，请检查",
                #         "result": "NG"
                #     }

                for it in device_class:
                    status_num = 0
                    if it["EquipStatus"]:
                        status_num = 1
                    data = {
                        "equipment_name": it["EquipName"], "equipment_num": it["EquipNumber"],
                        "equipment_ip": it['EquipIP'], "equipment_serial": it['EquipSerial'],
                        "equipOrder": "", "equipResult": "", "checkDevice": "/", "checkResult": "",
                        "equipStatus": status_num, "equipError": it['EquipError']
                    }
                    # 获取最新的设备状态
                    equip_status = cache.get('Equip_Status')
                    checkdevice = cache.get('CheckDevice', default=None)
                    print(equip_status)
                    for it1 in equip_status:
                        if it1['EquipNumber'] == data['equipment_num']:
                            data['equipOrder'] = it1['EquipOrder']
                            data['equipResult'] = it1['EquipResult']
                            data['checkDevice'] = it1['CheckDevice']
                            data['checkResult'] = it1['CheckResult']
                    for it2 in checkdevice:
                        if it2 == data['equipment_num']:
                            data['checkDevice'] = 'YES'

                    back_data_list.append(data)
                back_data = {
                    "localmodel": cache.get('current_model'),
                    "data": back_data_list,
                    # "table": [{"ProductSum": "", "ProductQuantity": "", "Accept": "", "Yield": ""}]
                }
                print(">>>>>>>back_data")
                print(back_data)
            case "5":
                print("CheckDevice")  # 点检
                back_data_list = []
                send_tag = True
                if condition == "YES":
                    print("YES")
                    # 群发复位信息给station   Send_Message()
                    data = {
                        "Command": "0x16",
                        "Instruct": "CheckDevice"
                    }
                    # 对所有机台群发指令
                    Send_Message(data)
                    # 最多等待3秒 等待机台回复
                    wait_tag = 10
                    send_tag = True
                    while wait_tag > 0:
                        send_tag = True
                        equip_status = cache.get('Equip_Status')
                        # print(equip_status)
                        for item in equip_status:
                            if item['EquipOrder'].upper() != 'CHECK' or item['EquipResult'] != 'OK':
                                send_tag = False
                                break
                        if send_tag is True:
                            break
                        wait_tag -= 1
                        print("sleep")
                        time.sleep(1)

                elif condition == "NO":
                    print("NO")
                    equips_list = request.POST.get('EquipList', '')
                    print(type(equips_list))
                    equips_list = json.loads(equips_list)
                    print(type(equips_list))

                    print(">>>>>equips_list")
                    print(equips_list)
                    # 根据返回的设备列表下发指令
                    for it in equips_list:
                        topic = "Msg2Station/" + it['equipment_num']
                        data = {
                            "Command": "0x16",
                            "Instruct": "CheckDevice"
                        }
                        publish(topic, data)
                    # 最多等待3秒 等待机台回复
                    wait_tag = 10
                    send_tag = True
                    while wait_tag > 0:
                        send_tag = True
                        equip_status = cache.get('Equip_Status')
                        # print(equip_status)
                        for item1 in equip_status:
                            for item2 in equips_list:
                                if item1['EquipNumber'] == item2['equipment_num']:
                                    if item1['EquipOrder'].upper() != 'CHECK' or item1['EquipResult'] != 'OK':
                                        send_tag = False
                                        break
                            if send_tag is False:
                                break
                        if send_tag is True:
                            break
                        wait_tag -= 1
                        print("sleep")
                        time.sleep(1)

                # back_data_list 状态同步，返回换型结果给前端
                print("#----------------------返回复位结果给前端----------------------")
                if send_tag is True:
                    back_meta = {
                        "msg": "点检成功",
                        "result": "OK"
                    }
                else:
                    back_meta = {
                        "msg": "部分机台点检失败，请检查",
                        "result": "NG"
                    }
                for it in device_class:
                    status_num = 0
                    if it["EquipStatus"]:
                        status_num = 1
                    data = {
                        "equipment_name": it["EquipName"], "equipment_num": it["EquipNumber"],
                        "equipment_ip": it['EquipIP'], "equipment_serial": it['EquipSerial'],
                        "equipOrder": "", "equipResult": "",
                        "equipStatus": status_num
                    }
                    # 获取最新的设备状态
                    equip_status = cache.get('Equip_Status')
                    print(equip_status)
                    for it1 in equip_status:
                        if it1['EquipNumber'] == data['equipment_num']:
                            data['equipOrder'] = it1['EquipOrder']
                            data['equipResult'] = it1['EquipResult']
                    back_data_list.append(data)
                back_data = {
                    "localmodel": cache.get('current_model'),
                    "data": back_data_list,
                    # "table": [{"ProductSum": "", "ProductQuantity": "", "Accept": "", "Yield": ""}]
                }
                print(">>>>>>>back_data")
                print(back_data)
            case "":
                print("error")
                back_meta = {
                    "msg": "错误：未识别操作字符，为空字符串",
                    "result": "NG"
                }
    except Exception as err:
        print(str(err))
        for it in device_class:
            status_num = 0
            if it["EquipStatus"]:
                status_num = 1
            data = {
                "equipment_name": it["EquipName"], "equipment_num": it["EquipNumber"], "equipment_ip": it['EquipIP'],
                "equipment_serial": it['EquipSerial'],
                "equipOrder": "", "equipResult": "", "checkDevice": "/", "checkResult": "NA",
                "equipStatus": status_num, "equipError": it['EquipError']
            }
            # 获取最新的设备状态
            equip_status = cache.get('Equip_Status')
            print(equip_status)
            for it1 in equip_status:
                if it1['EquipNumber'] == data['equipment_num']:
                    data['equipOrder'] = it1['EquipOrder']
                    data['equipResult'] = it1['EquipResult']
                    data['checkDevice'] = it1['CheckDevice']
                    data['checkResult'] = it1['CheckResult']

            back_data_list.append(data)
        back_data = {
            "localmodel": cache.get('current_model'),
            "data": back_data_list,
        }
        back_meta = {
            "msg": str(err).replace("\"", ""),
            "result": "NG"
        }
    backdata = {
        "data": back_data,
        "meta": back_meta,
    }
    print(backdata)
    return HttpResponse(List_Json(backdata))


# --------------换型-------------------
def Remodel(request):
    try:
        back_data = {}
        # back_data_list = []
        back_meta = {}
        Selected_Model = request.GET.get('selectvalue', '')
        Condition = request.GET.get('Condition').upper()
        current_model = cache.get('current_model')
        # if current_model == Selected_Model:
        #     raise Exception("换型型号与当前型号相同")
        if Condition == "YES":
            log.info("Remodel>>>>>>>>>>>  " + Selected_Model  + " : " + Condition)
            back_data = {}
            back_data_list = []
            back_meta = {}
            # if current_model == Selected_Model:
            #     msg = "换型型号与当前运行型号相同"
            #     print(msg)
            #     raise Exception(msg)
            if Selected_Model == '':
                msg = "Selected_Model为空"
                print(msg)
                raise Exception(msg)

            device_class = cache.get('DeviceClass', default=None)
            if device_class is None or device_class == []:
                print("DeviceClass为空")
                back_meta = {
                    "msg": "DeviceClass为空",
                    "result": "NG"
                }
                backdata = {
                    "data": back_data,
                    "meta": back_meta,
                }
                return HttpResponse(List_Json(backdata))

            # ----------------还原因为选择机台换型导致的st_current_model临时型号---------
            SQL = "UPDATE station_tab SET st_current_model = '" + current_model + "' WHERE gp_model = '" + current_model + "'"
            print(SQL)
            if not sql_execute(SQL):
                raise Exception('修改类型信息失败！')
            # -------------------修改current_model的内存和本地信息-------------------
            Cache_writer('current_model', Selected_Model, None)
            filepath = GetFilePath("SoftWare.ini")
            conf = ConfigParser()  # 需要实例化一个ConfigParser对象
            conf.read(filepath)  # 需要添加上config.ini的路径，不需要open打开，直接给文件路径就读取，也可以指定encoding='utf-8'
            print(conf['CommonUse']['CurrentModel'])
            conf.set('CommonUse', 'CurrentModel', str(Selected_Model))
            with open(filepath, 'w', encoding='utf-8') as f:
                conf.write(f)
            print(conf['CommonUse']['CurrentModel'])

            # 修改换型后设备各种变量信息
            print("----------------------修改换型后设备各种变量信息----------------------")
            old_device_class = cache.get('DeviceClass', default=None)
            GolbalGroup_Ini()
            # 修改equip_status中Order信息
            equip_status = cache.get('Equip_Status', default=None)
            equip_connect = cache.get('EquipConnect', default=None)
            device_class = cache.get('DeviceClass', default=None)
            print(equip_status)
            print(datetime.datetime.now())


            if equip_status is None or equip_status == []:
                back_meta = {
                    "msg": "Equip_Status为空",
                    "result": "NG"
                }
                backdata = {
                    "data": back_data,
                    "meta": back_meta,
                }
                return HttpResponse(List_Json(backdata))

            for it in equip_status:
                if it['EquipOrder'].upper() == 'ERROR':
                    msg = "当前设备存在错误机台，无法换型"
                    print(msg)
                    back_meta = {
                        "msg": msg,
                        "result": "NG"
                    }
                    backdata = {
                        "data": back_data,
                        "meta": back_meta,
                    }
                    return HttpResponse(List_Json(backdata))

            for it in equip_status:
                if it['EquipOrder'].upper() == 'STOP':
                    msg = "当前设备存在停机机台，无法换型"
                    print(msg)
                    back_meta = {
                        "msg": msg,
                        "result": "NG"
                    }
                    backdata = {
                        "data": back_data,
                        "meta": back_meta,
                    }
                    return HttpResponse(List_Json(backdata))

            for it in equip_status:
                it["EquipOrder"] = "Remodel"
                it["EquipResult"] = "NA"
            Cache_writer('Equip_Status', equip_status, None)

            # 对比EquipConnect  DeviceClass
            print("----------------------对比EquipConnect  DeviceClass----------------------")
            ApplyEquipConnectStatus(device_class, equip_connect)
            Cache_writer('DeviceClass', device_class, None)
            print(equip_status)
            print(equip_connect)
            print(device_class)

            Cache_writer('ModelSetFlag', 1, None)  # 1 一键下发  2  选择机台下发   #这里是选择机台下发中的yes下发，其实还是默认全部下发，和一键效果类似（只向old机器发）
            # 发换型消息到old机台
            for it in old_device_class:
                print(it)
                topic = "Msg2Station/" + str(it['EquipNumber'])
                data = {
                    "Command": "0x05",
                    "Gp_Model": Selected_Model
                }
                # 换型下发物料号信息
                partno_data = Remodel_getpartno_data(Selected_Model)
                data['Q_PART_NO'] = partno_data['Q_PART_NO']
                data['H_PART_NO'] = partno_data['H_PART_NO']
                data['P_PART_NO'] = partno_data['P_PART_NO']
                data['J_PART_NO'] = partno_data['J_PART_NO']
                data['ZC_PART_NO'] = ""

                publish(topic, json.dumps(data, ensure_ascii=False))
                log.info(topic + ": " + str(data))
                print(topic + ":" + json.dumps(data))


            # sleep 等待机台mqtt返回消息（收到的是作为新型号下 和旧型号重复的机台的回信 0x05）
            wait_tag = 10
            send_tag = True
            while wait_tag > 0:
                # 查看当前设备的换型状态
                equip_status = cache.get('Equip_Status')
                send_tag = True
                for item in equip_status:
                    if item['EquipOrder'].upper() != "REMODEL" or item['EquipResult'] != "OK":
                        send_tag = False
                        break
                if send_tag is True:
                    break
                wait_tag -= 1
                print("sleep")
                time.sleep(1)

            # 记录时间     换型为先换后确认是否成功，由于换型方式多，只有换型设计成在此处记录时间，其余应该在收到信息解析时记录时间
            print(">>>>>>>>>>>>>>>>>>>记录时间")
            print(send_tag)

            if send_tag is True:
                equipnumgroup = cache.get('EquipNumGroup')
                for it in equipnumgroup:
                    Time_Record(it, 4, False)

            # back_data_list 状态同步，返回换型结果给前端
            print("#----------------------返回换型结果给前端----------------------")
            if send_tag is True:
                back_meta = {
                    "msg": "换型成功",
                    "result": "OK"
                }
            else:
                back_meta = {
                    "msg": "部分机台换型失败，请检查",
                    "result": "NG"
                }
            for it in device_class:
                status_num = 0
                if it["EquipStatus"]:
                    status_num = 1
                data = {
                    "equipment_name": it["EquipName"], "equipment_num": it["EquipNumber"], "equipment_ip": it['EquipIP'], "equipment_serial": it['EquipSerial'],
                    "equipOrder": "", "equipResult": "", "checkDevice": "/", "checkResult": "",
                    "equipStatus": status_num, "equipError": it['EquipError']
                }
                #获取最新的设备状态
                checkdevice = cache.get('CheckDevice', default=None)
                equip_status = cache.get('Equip_Status')
                print(equip_status)
                for it1 in equip_status:
                    if it1['EquipNumber'] == data['equipment_num']:
                        data['equipOrder'] = it1['EquipOrder']
                        data['equipResult'] = it1['EquipResult']
                        data['checkDevice'] = it1['CheckDevice']
                        data['checkResult'] = it1['CheckResult']

                for it2 in checkdevice:
                    if it2 == data['equipment_num']:
                        data['checkDevice'] = 'YES'

                back_data_list.append(data)
                print(">>>>>back_data_list")
                print(back_data_list)

            back_data = {
                "localmodel": Selected_Model,
                "data": back_data_list,
                # "table": [{"ProductSum": "", "ProductQuantity": "", "Accept": "", "Yield": ""}]
            }
        elif Condition == "NO":
            equiplist = request.GET.get('EquipList', '')   #已经打勾选中的设备
            equiplist = json.loads(equiplist)

            SQL = "SELECT * FROM station_tab WHERE gp_model = '" + Selected_Model + "'"
            print(SQL)
            data = easy_sql_reader(SQL)
            print(data)
            # Device_Connect_Class  新的型号下的设备，保留现在已经连接的部分设备
            Device_Connect_Class = Device_Connect_Select(Selected_Model, data)
            Device_Connect_Class_re = []
            #   新的型号下的设备，现已经连接的部分设备，再由手动选中的部分的设备
            for it1 in Device_Connect_Class:
                print(it1)
                ret = False
                for it2 in equiplist:
                    print(it2)
                    if it1["EquipNumber"] == it2.get("equipment_num"):
                        print(it1["EquipNumber"] + " : " + str(it2.get("equipment_num")))
                        ret = True
                        break
                if ret is True:
                    Device_Connect_Class_re.append(it1)

            # Device_Connect_Class_re 更新数据库中 st_current_model 的当前类型  顺便向对应设备发送MQTT换型信息
            Cache_writer('ModelSetFlag', 2, None)  # 1 一键下发  2   选择机台下发
            equip_status = cache.get('Equip_Status')
            log.info("Remodel>>>>>>>>>>>  " + Selected_Model + " : " + Condition + "\n equiplist: " + str(equiplist) + "\n Device_Connect_Class: " + str(Device_Connect_Class) + "\n Device_Connect_Class_re: " + str(Device_Connect_Class_re) + "\n equip_status: " + str(equip_status))
            for it in Device_Connect_Class_re:
                print(it)
                SQL = "UPDATE station_tab SET st_current_model = '" + Selected_Model + "' WHERE gp_model = '" + current_model + "' AND equipment_num = '" + it['EquipNumber'] + "'"
                print(SQL)
                equip_status = cache.get('Equip_Status')

                # for item in equip_status:
                #     if item['EquipOrder'].upper() == "ERROR":
                #         raise Exception('设备中存在Error设备,无法换型！')
                # for item in equip_status:
                #     if item['EquipOrder'].upper() == "STOP":
                #         raise Exception('设备中存在STOP设备,无法换型！')

                for item in equip_status:
                    if item['EquipNumber'] == it['EquipNumber']:
                        item['EquipResult'] = "NA"
                        item['EquipOrder'] = "Remodel"
                        Cache_writer("Equip_Status", equip_status, None)

                if not sql_execute(SQL):
                    raise Exception('修改设备型号信息失败！')

                topic = "Msg2Station/" + str(it['EquipNumber'])
                data = {
                    "Command": "0x05",
                    "Gp_Model": Selected_Model
                }
                # 换型下发物料号信息
                partno_data = Remodel_getpartno_data(Selected_Model)
                data['Q_PART_NO'] = partno_data['Q_PART_NO']
                data['H_PART_NO'] = partno_data['H_PART_NO']
                data['P_PART_NO'] = partno_data['P_PART_NO']
                data['J_PART_NO'] = partno_data['J_PART_NO']
                data['ZC_PART_NO'] = ""
                # 发送换型指令
                publish(topic, json.dumps(data, ensure_ascii=False))

            print(Device_Connect_Class_re)
            # 最多等待3秒获得机台反馈换型消息
            print("最多等待3秒获得机台反馈换型消息")
            wait_tag = 10
            send_tag = True
            print(wait_tag)
            print(send_tag)
            while wait_tag > 0:
                # 查看当前设备的换型状态
                equip_status = cache.get('Equip_Status')
                send_tag = True
                for item1 in equip_status:
                    for item2 in Device_Connect_Class_re:
                        if item1['EquipNumber'] == item2['EquipNumber']:
                            if item1['EquipOrder'].upper() != "REMODEL" or item1['EquipResult'] != "OK":
                                send_tag = False
                                break
                    if send_tag is False:
                        break
                if send_tag is True:
                    break
                wait_tag -= 1
                print("sleep")
                time.sleep(1)
            if send_tag is True:
                back_meta = {
                    "msg": "换型成功",
                    "result": "OK"
                }
            else:
                back_meta = {
                    "msg": "部分机台换型失败，请检查",
                    "result": "NG"
                }
            # 记录时间
            if send_tag is True:
                for it in Device_Connect_Class_re:
                    Time_Record(it['EquipNumber'], 4, True)

            device_class = cache.get('DeviceClass', default=None)
            back_data_list = []
            for it in device_class:
                status_num = 0
                if it["EquipStatus"]:
                    status_num = 1
                data = {
                    "equipment_name": it["EquipName"], "equipment_num": it["EquipNumber"], "equipment_ip": it['EquipIP'], "equipment_serial": it['EquipSerial'],
                    "equipOrder": "", "equipResult": "", "checkDevice": "/", "checkResult": "NA",
                    "equipStatus": status_num, "equipError": it['EquipError']
                }
                #获取最新的设备状态
                equip_status = cache.get('Equip_Status')
                print(equip_status)
                for it1 in equip_status:
                    if it1['EquipNumber'] == data['equipment_num']:
                        data['equipOrder'] = it1['EquipOrder']
                        data['equipResult'] = it1['EquipResult']
                        data['checkDevice'] = it1['CheckDevice']
                        data['checkResult'] = it1['CheckResult']
                back_data_list.append(data)
                print(">>>>>>back_data_list")
                print(back_data_list)

            back_data = {
                "localmodel": current_model,
                "st_current_model": Selected_Model,
                "data": back_data_list,
            }

            backdata = {
                "data": back_data,
                "meta": back_meta,
            }
            print(backdata)
            return HttpResponse(List_Json(backdata))

    except Exception as err:
        log.info("Remodel ERROR :" + str(err))

        device_class = cache.get('DeviceClass', default=None)
        back_data_list = []
        for it in device_class:
            status_num = 0
            if it["EquipStatus"]:
                status_num = 1
            data = {
                "equipment_name": it["EquipName"], "equipment_num": it["EquipNumber"], "equipment_ip": it['EquipIP'],
                "equipment_serial": it['EquipSerial'],
                "equipOrder": "", "equipResult": "", "checkDevice": "/", "checkResult": "NA",
                "equipStatus": status_num, "equipError": it['EquipError']
            }
            # 获取最新的设备状态
            equip_status = cache.get('Equip_Status')
            print(equip_status)
            for it1 in equip_status:
                if it1['EquipNumber'] == data['equipment_num']:
                    data['equipOrder'] = it1['EquipOrder']
                    data['equipResult'] = it1['EquipResult']
                    data['checkDevice'] = it1['CheckDevice']
                    data['checkResult'] = it1['CheckResult']
            back_data_list.append(data)

        back_data = {
            "localmodel": current_model,
            "st_current_model": Selected_Model,
            "data": back_data_list,
        }

        back_meta = {
            "msg": str(err).replace("\"", ""),
            "result": "NG"
        }

    backdata = {
        "data": back_data,
        "meta": back_meta,
    }
    print(backdata)
    return HttpResponse(List_Json(backdata))


# --------------一键换型-------------------
def QuickRemodel(request):
    print("QuickRemodel>>>>>>>>>>>")
    print(request.GET.get('selectvalue'))
    try:
        back_data = {}
        back_data_list = []
        back_meta = {}
        Selected_Model = request.GET.get('selectvalue', '')
        device_class = cache.get('DeviceClass', default=None)
        current_model = cache.get('current_model')
        # if current_model == Selected_Model:
        #     raise Exception("换型型号与当前运行型号相同")
        if Selected_Model == '':
            raise Exception("Selected_Model为空")
        device_class = cache.get('DeviceClass', default=None)
        if device_class is None or device_class == []:
            raise Exception("DeviceClass为空")
        # 全自动状态功能判断
        for it in device_class:
            if not it["EquipStatus"]:
                raise Exception("全部机台连接后才可使用一键换型")
        Cache_writer('ModelSetFlag', 1, None)      # 1 一键下发  2   选择机台下发

        # ----------------还原因为选择机台换型导致的st_current_model临时型号---------
        SQL = "UPDATE station_tab SET st_current_model = '" + current_model + "' WHERE gp_model = '" + current_model + "'"
        print(SQL)
        if not sql_execute(SQL):
            raise Exception('修改类型信息失败！')
        # 修改current_model的内存和本地信息
        print("----------------------修改current_model的内存和本地信息----------------------")
        Cache_writer('current_model', Selected_Model, None)
        filepath = GetFilePath("SoftWare.ini")
        conf = ConfigParser()  # 需要实例化一个ConfigParser对象
        conf.read(filepath)  # 需要添加上config.ini的路径，不需要open打开，直接给文件路径就读取，也可以指定encoding='utf-8'
        print(conf['CommonUse']['CurrentModel'])
        conf.set('CommonUse', 'CurrentModel', str(Selected_Model))
        with open(filepath, 'w', encoding='utf-8') as f:
            conf.write(f)
        print(conf['CommonUse']['CurrentModel'])
        print(cache.get('current_model'))

        # 修改换型后设备各种变量信息
        print("----------------------修改换型后设备各种变量信息----------------------")
        GolbalGroup_Ini()
        # 修改equip_status中Order信息
        equip_status = cache.get('Equip_Status', default=None)
        equip_connect = cache.get('EquipConnect', default=None)
        device_class = cache.get('DeviceClass', default=None)

        # 向第一台机器下发换型信息  # 订阅区分大小写
        print("----------------------向第一台机器下发换型信息----------------------")
        device_class = cache.get('DeviceClass', default=None)
        remodel_send = {
            "Command": "0x05",
            "Gp_Model": Selected_Model
        }
        # 换型下发物料号信息
        partno_data = Remodel_getpartno_data(Selected_Model)
        remodel_send['Q_PART_NO'] = partno_data['Q_PART_NO']
        remodel_send['H_PART_NO'] = partno_data['H_PART_NO']
        remodel_send['P_PART_NO'] = partno_data['P_PART_NO']
        remodel_send['J_PART_NO'] = partno_data['J_PART_NO']
        remodel_send['ZC_PART_NO'] = ""

        publish("Msg2Station/" + str(device_class[0]["EquipNumber"]), json.dumps(remodel_send))
        print("Msg2Station/" + str(device_class[0]["EquipNumber"]) + ":" + json.dumps(remodel_send))
        # # 修改换型后设备各种变量信息
        # print("----------------------修改换型后设备各种变量信息----------------------")
        # GolbalGroup_Ini()
        # # 修改equip_status中Order信息
        # equip_status = cache.get('Equip_Status', default=None)
        # equip_connect = cache.get('EquipConnect', default=None)
        # device_class = cache.get('DeviceClass', default=None)

        if equip_status is None or equip_status == []:
            back_meta = {
                "msg": "Equip_Status为空",
                "result": "NG"
            }
            backdata = {
                "data": back_data,
                "meta": back_meta,
            }
            return HttpResponse(List_Json(backdata))
        for it in equip_status:
            it["EquipOrder"] = "Remodel"
            it["EquipResult"] = "NA"
        Cache_writer('Equip_Status', equip_status, None)

        # 对比EquipConnect  DeviceClass
        ApplyEquipConnectStatus(device_class, equip_connect)
        Cache_writer('DeviceClass', device_class, None)

        #----------------------------------------------------------------------------------------------------
        # sleep 等待机台mqtt返回消息（收到的是作为新型号下 和旧型号重复的机台的回信 0x05）
        wait_tag = 20
        send_tag = True
        while wait_tag > 0:
            # 查看当前设备的换型状态
            equip_status = cache.get('Equip_Status')
            send_tag = True
            for item in equip_status:
                if item['EquipOrder'].upper() != "REMODEL" or item['EquipResult'] != "OK":
                    send_tag = False
                    break
            if send_tag is True:
                break
            wait_tag -= 1
            print("sleep")
            time.sleep(1)

        # 记录时间     换型为先换后确认是否成功，由于换型方式多，只有换型设计成在此处记录时间，其余应该在收到信息解析时记录时间
        print(">>>>>>>>>>>>>>>>>>>记录时间")
        print(send_tag)
        if send_tag is True:
            equipnumgroup = cache.get('EquipNumGroup')
            for it in equipnumgroup:
                Time_Record(it, 4, False)

        # back_data_list 状态同步，返回换型结果给前端
        print("#----------------------返回换型结果给前端----------------------")
        if send_tag is True:
            back_meta = {
                "msg": "换型成功",
                "result": "OK"
            }
        else:
            back_meta = {
                "msg": "部分机台换型失败，请检查",
                "result": "NG"
            }
        for it in device_class:
            status_num = 0
            if it["EquipStatus"]:
                status_num = 1
            data = {
                "equipment_name": it["EquipName"], "equipment_num": it["EquipNumber"], "equipment_ip": it['EquipIP'],
                "equipment_serial": it['EquipSerial'],
                "equipOrder": "", "equipResult": "",
                "equipStatus": status_num, "equipError": it['EquipError']
            }
            # 获取最新的设备状态
            equip_status = cache.get('Equip_Status')
            print(equip_status)
            for it1 in equip_status:
                if it1['EquipNumber'] == data['equipment_num']:
                    data['equipOrder'] = it1['EquipOrder']
                    data['equipResult'] = it1['EquipResult']
            back_data_list.append(data)
            print(">>>>>back_data_list")
            print(back_data_list)
        #-----------------------------------------------------------------------------------------------------



        # # back_data_list 状态同步，返回换型结果给前端
        # print("#----------------------返回换型结果给前端----------------------")
        # for it in device_class:
        #     status_num = 0
        #     if it["EquipStatus"]:
        #         status_num = 1
        #     data = {
        #         "equipment_name": it["EquipName"], "equipment_num": it["EquipNumber"],
        #         "equipOrder": "", "equipResult": "",
        #         "equipStatus": status_num
        #     }
        #     back_data_list.append(data)

        back_data = {
            "localmodel": Selected_Model,
            "data": back_data_list,
        }
    except Exception as err:
        print(str(err))
        back_meta = {
            "msg": str(err).replace("\"", ""),
            "result": "NG"
        }
        for it in device_class:
            status_num = 0
            if it["EquipStatus"]:
                status_num = 1
            data = {
                "equipment_name": it["EquipName"], "equipment_num": it["EquipNumber"], "equipment_ip": it['EquipIP'],
                "equipment_serial": it['EquipSerial'],
                "equipOrder": "", "equipResult": "",
                "equipStatus": status_num, "equipError": it['EquipError']
            }
            # 获取最新的设备状态
            equip_status = cache.get('Equip_Status')
            print(equip_status)
            for it1 in equip_status:
                if it1['EquipNumber'] == data['equipment_num']:
                    data['equipOrder'] = it1['EquipOrder']
                    data['equipResult'] = it1['EquipResult']
            back_data_list.append(data)
            print(">>>>>back_data_list")
            print(back_data_list)

        back_data = {
            "localmodel": Selected_Model,
            "data": back_data_list,
        }

    # 发送看板换型信息
    viewboard_topic = "Msg2Station/ViewBoard"
    viewboard_data_send = {
        "Command": "S003",
        "Gp_Model": Selected_Model,
        "Status": "1"
    }
    SendMessage2Station(viewboard_topic, viewboard_data_send)
    # 更新数据库看板setting表
    SQL = "UPDATE viewboard_setting SET model = '" + Selected_Model + "'"
    print(SQL)
    if not sql_execute(SQL):
        raise Exception('修改viewboard_setting失败！')

    backdata = {
        "data": back_data,
        "meta": back_meta,
    }
    print(backdata)
    # publish("commands/msg", json.loads(backdata))
    # print(rc)
    # print(mid)
    return HttpResponse(List_Json(backdata))
def Remodel_SP(request):
    try:
        print("Remodel_SP>>>>>>>>>>>")
        back_data = {}
        # back_data_list = []
        back_meta = {}
        Selected_Model = request.GET.get('selectvalue', '')
        Condition = request.GET.get('Condition').upper()
        current_model_sp = cache.get('current_model_sp')
        print(Selected_Model)
        # if current_model_sp == Selected_Model:
        #     raise Exception("换型型号与当前型号相同")
        if Condition == "YES":
            print("YES>>>>>>>>>>>")
            back_data = {}
            back_data_list = []
            back_meta = {}
            # if current_model == Selected_Model:
            #     msg = "换型型号与当前运行型号相同"
            #     print(msg)
            #     raise Exception(msg)
            if Selected_Model == '':
                msg = "Selected_Model为空"
                print(msg)
                raise Exception(msg)

            device_class_sp = cache.get('DeviceClass_SP', default=None)
            if device_class_sp is None or device_class_sp == []:
                print("DeviceClass_SP为空")
                back_meta = {
                    "msg": "DeviceClass_SP为空",
                    "result": "NG"
                }
                backdata = {
                    "data": back_data,
                    "meta": back_meta,
                }
                return HttpResponse(List_Json(backdata))

            # # ----------------还原因为选择机台换型导致的st_current_model临时型号---------
            # SQL = "UPDATE station_tab SET st_current_model = '" + current_model + "' WHERE gp_model = '" + current_model + "'"
            # print(SQL)
            # if not sql_execute(SQL):
            #     raise Exception('修改类型信息失败！')
            # -------------------修改current_model的内存和本地信息-------------------
            Cache_writer('current_model_sp', Selected_Model, None)
            filepath = GetFilePath("SoftWare.ini")
            conf = ConfigParser()  # 需要实例化一个ConfigParser对象
            conf.read(filepath)  # 需要添加上config.ini的路径，不需要open打开，直接给文件路径就读取，也可以指定encoding='utf-8'
            print(conf['CommonUse']['CurrentModel_SP'])
            conf.set('CommonUse', 'CurrentModel_SP', str(Selected_Model))
            with open(filepath, 'w', encoding='utf-8') as f:
                conf.write(f)
            print(conf['CommonUse']['CurrentModel_SP'])

            # 修改换型后设备各种变量信息
            print("----------------------修改换型后设备各种变量信息----------------------")
            old_device_class_sp = cache.get('DeviceClass_SP', default=None)
            GolbalGroup_Ini()
            # 修改equip_status中Order信息

            equip_status_sp = cache.get('Equip_Status_SP', default=None)
            equip_connect = cache.get('EquipConnect', default=None)
            device_class_sp = cache.get('DeviceClass_SP', default=None)
            print(equip_status_sp)
            print(datetime.datetime.now())


            if equip_status_sp is None or equip_status_sp == []:
                back_meta = {
                    "msg": "Equip_Status_SP为空",
                    "result": "NG"
                }
                backdata = {
                    "data": back_data,
                    "meta": back_meta,
                }
                return HttpResponse(List_Json(backdata))

            for it in equip_status_sp:
                if it['EquipOrder'].upper() == 'ERROR':
                    msg = "当前设备存在错误机台，无法换型"
                    print(msg)
                    back_meta = {
                        "msg": msg,
                        "result": "NG"
                    }
                    backdata = {
                        "data": back_data,
                        "meta": back_meta,
                    }
                    return HttpResponse(List_Json(backdata))

            for it in equip_status_sp:
                if it['EquipOrder'].upper() == 'STOP':
                    msg = "当前设备存在停机机台，无法换型"
                    print(msg)
                    back_meta = {
                        "msg": msg,
                        "result": "NG"
                    }
                    backdata = {
                        "data": back_data,
                        "meta": back_meta,
                    }
                    return HttpResponse(List_Json(backdata))

            for it in equip_status_sp:
                it["EquipOrder"] = "Remodel"
                it["EquipResult"] = "NA"
            Cache_writer('Equip_Status_SP', equip_status_sp, None)

            # 对比EquipConnect  DeviceClass
            print("----------------------对比EquipConnect  DeviceClass----------------------")
            ApplyEquipConnectStatus(device_class_sp, equip_connect)
            Cache_writer('DeviceClass_SP', device_class_sp, None)
            print(equip_status_sp)
            print(equip_connect)
            print(device_class_sp)

            Cache_writer('ModelSetFlag', 1, None)  # 1 一键下发  2  选择机台下发   #这里是选择机台下发中的yes下发，其实还是默认全部下发，和一键效果类似（只向old机器发）
            # 发换型消息到old机台
            for it in old_device_class_sp:
                print(it)
                topic = "Msg2Station/" + str(it['EquipNumber'])
                data = {
                    "Command": "0x05",
                    "Gp_Model": Selected_Model
                }
                # 换型下发物料号信息
                partno_data = Remodel_getpartno_data(Selected_Model)
                data['Q_PART_NO'] = partno_data['BT_PART_NO']
                data['H_PART_NO'] = ""
                data['P_PART_NO'] = ""
                data['J_PART_NO'] = ""
                data['ZC_PART_NO'] = ""

                publish(topic, json.dumps(data, ensure_ascii=False))
                log.info(topic + ": " + str(data))
                print(topic + ":" + json.dumps(data))


            # sleep 等待机台mqtt返回消息（收到的是作为新型号下 和旧型号重复的机台的回信 0x05）
            wait_tag = 10
            send_tag = True
            while wait_tag > 0:
                # 查看当前设备的换型状态
                equip_status_sp = cache.get('Equip_Status_SP')
                send_tag = True
                for item in equip_status_sp:
                    if item['EquipOrder'].upper() != "REMODEL" or item['EquipResult'] != "OK":
                        send_tag = False
                        break
                if send_tag is True:
                    break
                wait_tag -= 1
                print("sleep")
                time.sleep(1)

            # back_data_list 状态同步，返回换型结果给前端
            print("#----------------------返回换型结果给前端----------------------")
            if send_tag is True:
                back_meta = {
                    "msg": "换型成功",
                    "result": "OK"
                }
            else:
                back_meta = {
                    "msg": "部分机台换型失败，请检查",
                    "result": "NG"
                }
            for it in device_class_sp:
                status_num = 0
                if it["EquipStatus"]:
                    status_num = 1
                data = {
                    "equipment_name": it["EquipName"], "equipment_num": it["EquipNumber"], "equipment_ip": it['EquipIP'], "equipment_serial": it['EquipSerial'],
                    "equipOrder": "", "equipResult": "", "checkDevice": "/", "checkResult": "",
                    "equipStatus": status_num, "equipError": it['EquipError']
                }
                #获取最新的设备状态
                checkdevice = cache.get('CheckDevice', default=None)
                equip_status_sp = cache.get('Equip_Status_SP')
                print(equip_status_sp)
                for it1 in equip_status_sp:
                    if it1['EquipNumber'] == data['equipment_num']:
                        data['equipOrder'] = it1['EquipOrder']
                        data['equipResult'] = it1['EquipResult']
                        data['checkDevice'] = it1['CheckDevice']
                        data['checkResult'] = it1['CheckResult']

                # for it2 in checkdevice:
                #     if it2 == data['equipment_num']:
                #         data['checkDevice'] = 'YES'

                back_data_list.append(data)
                print(">>>>>back_data_list")
                print(back_data_list)

            back_data = {
                "localmodel": Selected_Model,
                "data": back_data_list,
                # "table": [{"ProductSum": "", "ProductQuantity": "", "Accept": "", "Yield": ""}]
            }
        # elif Condition == "NO":
        #     equiplist = request.GET.get('EquipList', '')   #已经打勾选中的设备
        #     print("NO:")
        #     print(type(equiplist))
        #     equiplist = json.loads(equiplist)
        #     print(type(equiplist))
        #     print(equiplist)
        #     SQL = "SELECT * FROM station_tab WHERE gp_model = '" + Selected_Model + "'"
        #     print(SQL)
        #     data = easy_sql_reader(SQL)
        #     print(data)
        #     # Device_Connect_Class  新的型号下的设备，保留现在已经连接的部分设备
        #     Device_Connect_Class = Device_Connect_Select(Selected_Model, data)
        #     Device_Connect_Class_re = []
        #     #   新的型号下的设备，现已经连接的部分设备，再由手动选中的部分的设备
        #     print("---------------------------")
        #     print(">>>>>>Device_Connect_Class :" + str(Device_Connect_Class))
        #     print(">>>>>>equiplist :" + str(equiplist))
        #     for it1 in Device_Connect_Class:
        #         print(it1)
        #         ret = False
        #         for it2 in equiplist:
        #             print(it2)
        #             if it1["EquipIP"] == it2["equipment_ip"]:
        #                 print(it1["EquipIP"] + " : " + it2["equipment_ip"])
        #                 ret = True
        #                 break
        #         if ret is True:
        #             Device_Connect_Class_re.append(it1)
        #
        #     # Device_Connect_Class_re 更新数据库中 st_current_model 的当前类型  顺便向对应设备发送MQTT换型信息
        #     Cache_writer('ModelSetFlag', 2, None)  # 1 一键下发  2   选择机台下发
        #     print(">>>>>>Device_Connect_Class_re :" + str(Device_Connect_Class_re))
        #     for it in Device_Connect_Class_re:
        #         print(it)
        #         SQL = "UPDATE station_tab SET st_current_model = '" + Selected_Model + "' WHERE gp_model = '" + current_model + "' AND equipment_num = '" + it['EquipNumber'] + "'"
        #         print(SQL)
        #         equip_status = cache.get('Equip_Status')
        #
        #         for item in equip_status:
        #             if item['EquipOrder'].upper() == "ERROR":
        #                 raise Exception('设备中存在Error设备,无法换型！')
        #         for item in equip_status:
        #             if item['EquipOrder'].upper() == "STOP":
        #                 raise Exception('设备中存在STOP设备,无法换型！')
        #
        #         for item in equip_status:
        #             if item['EquipNumber'] == it['EquipNumber']:
        #                 item['EquipResult'] = "NA"
        #                 item['EquipOrder'] = "Remodel"
        #                 Cache_writer("Equip_Status", equip_status, None)
        #
        #         if not sql_execute(SQL):
        #             raise Exception('修改设备型号信息失败！')
        #
        #         topic = "Msg2Station/" + str(it['EquipNumber'])
        #         data = {
        #             "Command": "0x05",
        #             "Gp_Model": Selected_Model
        #         }
        #         publish(topic, json.dumps(data, ensure_ascii=False))
        #         log.info(topic + ": " + str(data))
        #
        #         print(topic+":"+str(data))
        #         print(datetime.datetime.now())
        #
        #     print(Device_Connect_Class_re)
        #     # 最多等待3秒获得机台反馈换型消息
        #     print("最多等待3秒获得机台反馈换型消息")
        #     wait_tag = 10
        #     send_tag = True
        #     print(wait_tag)
        #     print(send_tag)
        #     while wait_tag > 0:
        #         # 查看当前设备的换型状态
        #         equip_status = cache.get('Equip_Status')
        #         send_tag = True
        #         for item1 in equip_status:
        #             for item2 in Device_Connect_Class_re:
        #                 if item1['EquipNumber'] == item2['EquipNumber']:
        #                     if item1['EquipOrder'].upper() != "REMODEL" or item1['EquipResult'] != "OK":
        #                         send_tag = False
        #                         break
        #             if send_tag is False:
        #                 break
        #         if send_tag is True:
        #             break
        #         wait_tag -= 1
        #         print("sleep")
        #         time.sleep(1)
        #     if send_tag is True:
        #         back_meta = {
        #             "msg": "换型成功",
        #             "result": "OK"
        #         }
        #     else:
        #         back_meta = {
        #             "msg": "部分机台换型失败，请检查",
        #             "result": "NG"
        #         }
        #     # 记录时间
        #     if send_tag is True:
        #         for it in Device_Connect_Class_re:
        #             Time_Record(it['EquipNumber'], 4, True)
        #
        #     device_class = cache.get('DeviceClass', default=None)
        #     back_data_list = []
        #     for it in device_class:
        #         status_num = 0
        #         if it["EquipStatus"]:
        #             status_num = 1
        #         data = {
        #             "equipment_name": it["EquipName"], "equipment_num": it["EquipNumber"], "equipment_ip": it['EquipIP'], "equipment_serial": it['EquipSerial'],
        #             "equipOrder": "", "equipResult": "", "checkDevice": "/", "checkResult": "NA",
        #             "equipStatus": status_num, "equipError": it['EquipError']
        #         }
        #         #获取最新的设备状态
        #         equip_status = cache.get('Equip_Status')
        #         print(equip_status)
        #         for it1 in equip_status:
        #             if it1['EquipNumber'] == data['equipment_num']:
        #                 data['equipOrder'] = it1['EquipOrder']
        #                 data['equipResult'] = it1['EquipResult']
        #                 data['checkDevice'] = it1['CheckDevice']
        #                 data['checkResult'] = it1['CheckResult']
        #         back_data_list.append(data)
        #         print(">>>>>>back_data_list")
        #         print(back_data_list)
        #
        #     back_data = {
        #         "localmodel": current_model,
        #         "st_current_model": Selected_Model,
        #         "data": back_data_list,
        #     }
        #
        #     backdata = {
        #         "data": back_data,
        #         "meta": back_meta,
        #     }
        #     print(backdata)
        #     return HttpResponse(List_Json(backdata))

    except Exception as err:
        print(str(err))

        device_class_sp = cache.get('DeviceClass_SP', default=None)
        back_data_list = []
        for it in device_class_sp:
            status_num = 0
            if it["EquipStatus"]:
                status_num = 1
            data = {
                "equipment_name": it["EquipName"], "equipment_num": it["EquipNumber"], "equipment_ip": it['EquipIP'],
                "equipment_serial": it['EquipSerial'],
                "equipOrder": "", "equipResult": "", "checkDevice": "/", "checkResult": "NA",
                "equipStatus": status_num, "equipError": it['EquipError']
            }
            # 获取最新的设备状态
            equip_status_sp = cache.get('Equip_Status_SP')
            print(equip_status_sp)
            for it1 in equip_status_sp:
                if it1['EquipNumber'] == data['equipment_num']:
                    data['equipOrder'] = it1['EquipOrder']
                    data['equipResult'] = it1['EquipResult']
                    data['checkDevice'] = it1['CheckDevice']
                    data['checkResult'] = it1['CheckResult']
            back_data_list.append(data)

        back_data = {
            "localmodel": current_model_sp,
            "st_current_model": Selected_Model,
            "data": back_data_list,
        }

        back_meta = {
            "msg": str(err).replace("\"", ""),
            "result": "NG"
        }

    backdata = {
        "data": back_data,
        "meta": back_meta,
    }
    print(backdata)
    return HttpResponse(List_Json(backdata))
def GetLocalModel_Equipment_SP(request):
    try:
        back_data = {}
        back_data_list = []
        back_meta = {}

        current_model = cache.get('current_model_sp')
        current_order = cache.get('current_order_stand')
        device_class_sp = cache.get('DeviceClass_SP')
        equipstatus_sp = cache.get('Equip_Status_SP')

        device_class = cache.get('DeviceClass')
        equipstatus = cache.get('Equip_Status')
        equip_connect = cache.get("EquipConnect")
        if not len(device_class_sp) == 0:
            for it in device_class_sp:
                back_data_list.append(
                    {"equipment_name": it['EquipName'], "equipment_num": it['EquipNumber'],
                     "equipment_ip": it['EquipIP'], "equipment_serial": it['EquipSerial'],
                     "equipStatus": 0, "equipOrder": "NA", "equipResult": "NA", "checkDevice": "/", "checkResult": ""})
            # 冒泡
            n = len(back_data_list)
            for i in range(n):
                # Last i elements are already in place
                for j in range(0, n - i - 1):
                    if int(back_data_list[j]['equipment_serial']) > int(back_data_list[j + 1]['equipment_serial']):
                        back_data_list[j], back_data_list[j + 1] = back_data_list[j + 1], back_data_list[j]
            print(equip_connect)
            print(back_data_list)
            adapted = [{"EquipNumber": it['equipment_num'], "EquipIP": it['equipment_ip'], "EquipStatus": False, "_row": it} for it in back_data_list]
            ApplyEquipConnectStatus(adapted, equip_connect)
            for it in adapted:
                if it.get('EquipStatus'):
                    it['_row']['equipStatus'] = 1

            for it1 in equipstatus_sp:
                for it2 in back_data_list:
                    if it1['EquipNumber'] == it2['equipment_num']:
                        it2['equipOrder'] = it1['EquipOrder']
                        it2['equipResult'] = it1['EquipResult']

        back_data = {
            "localmodel": current_model,
            "localorder": current_order,
            "data": back_data_list
        }
        back_meta = {
            "msg": "获取成功",
            "result": "OK"
        }
    except Exception as err:
        print(str(err))
        back_meta = {
            "msg": str(err).replace("\"", ""),
            "result": "NG"
        }

    backdata = {
        "data": back_data,
        "meta": back_meta,
    }
    print(backdata)
    return HttpResponse(List_Json(backdata))
# ---------------------------------型号管理------------------------------

@csrf_exempt
def models(request):
    try:
        SQL = "select id,gp_model,sn_way from model_tab"
        # data1 = sql_list_first(SQL)
        data = easy_sql_reader(SQL)
        log.info("型号列表获取成功 count=%s", len(data) if data else 0)
        meta = {
            "msg": "获取型号列表成功!",
            "result": "OK"
        }
        backdata = {
            "data": data,
            "meta": meta,
        }

        return HttpResponse(json.dumps(backdata, ensure_ascii=False))

    except Exception as err:
        Data = {

        }
        meta = {
            "msg": "获取菜单列表失败",
            "result": "NG"
        }

        backdata = {
            "data": Data,
            "meta": meta,
        }
        # print(err)
        return HttpResponse(json.dumps(backdata, ensure_ascii=False))

# 获取设备名列表
@csrf_exempt
def equips_list(request):
    try:
        SQL = "select id,equipment_name,equipment_num from equipment_tab"
        # print(SQL)
        data = easy_sql_reader(SQL)
        meta = {
            "msg": "获取设备列表成功!",
            "result": "OK"
        }
        backdata = {
            "data": data,
            "meta": meta,
        }
        # print(backdata)
        # print(SQL)
        return HttpResponse(List_Json(backdata))

    except Exception as err:
        Data = {

        }
        meta = {
            "msg": "获取设备列表失败",
            "result": "NG"
        }

        backdata = {
            "data": Data,
            "meta": meta,
        }
        return HttpResponse(List_Json(backdata))

# @transaction.atomic
# @csrf_exempt
def AddModels(request):
    try:
        data = request.POST.get('data', '')
        data = json.loads(data)
        xinghao = request.POST.get('xinghao', '')
        sn_way = request.POST.get('sn_way', '')

        current_model = cache.get('current_model')

        # cs = connection.cursor()
        # save_id = transaction.savepoint()
        # 判断数据库中是否已经有此型号，没有则添加 有不添加 也不会报错;
        SQL = "select id from  model_tab where gp_model='" + xinghao + "'"
        data1 = SQL_function3(SQL)
        if len(data1) == 0:

            SQL = "INSERT INTO model_tab(gp_model,Pass,Fail,sn_way)VALUES ('" + xinghao + "',0,0,'" + sn_way + "')"
            if not SQL_function4(SQL):
                raise Exception('SQL执行失败！')
            SQL = "INSERT INTO planorder_partno_tab (gp_model)VALUES ('" + xinghao + "')"
            if not SQL_function4(SQL):
                raise Exception('SQL执行失败！')

        else:
            SQL = "UPDATE model_tab SET sn_way = '" + sn_way + "' WHERE gp_model = '" + xinghao + "'"
            if not SQL_function4(SQL):
                raise Exception('修改sn_way信息失败！')
        #
        # elif data==[]:
        #     raise Exception("该型号已添加！")
        # 前端勾选了设备，则添加
        print(data)
        if data != [] or len(data) != 0:
            for i in data:
                SQL = "select * from station_tab where equipment_name='" + i["equipment_name"] + "' and equipment_num='" + i["equipment_num"] + "' and equipment_ip='" + i[
                    "equipment_ip"] + "' and equipment_serial='" + i["equipment_serial"] + "' and gp_model='" + xinghao + "'"
                print(SQL)
                data2 = SQL_function3(SQL)
                if not len(data2) == 0:
                    raise Exception("该型号已经包含设备" + i["equipment_name"] + "请检查！！！")

                else:
                    SQL = "INSERT INTO station_tab(equipment_name,equipment_num,equipment_ip,equipment_serial,gp_model,st_current_model)VALUES ('" + i["equipment_name"] + "','" + i["equipment_num"] + "','" + i[
                        "equipment_ip"] + "','" + i["equipment_serial"] + "','" + xinghao + "','" + xinghao + "')"
                    if not SQL_function4(SQL):
                        raise Exception('SQL执行失败！')

                    # 如果是往当前型号下插入新的机台信息，就得同时更新内存中的机台列表
                    if xinghao == current_model:
                        # Equip_Status
                        equip_status = cache.get('Equip_Status')
                        equipStatus = {"EquipName": i['equipment_name'], "EquipNumber": i['equipment_num'],
                                       "EquipOrder": "NA",
                                       "EquipResult": "NA"}
                        equip_status.append(equipStatus)
                        Cache_writer('Equip_Status', equip_status, None)
                        # EquipNumGroup
                        SQL = "SELECT * FROM station_tab WHERE gp_model = '" + xinghao + "'"
                        print(SQL)
                        data = SQL_function3(SQL)
                        EquipNumGroup_Ini(data)

                        # EquipConnect
                        equip_connect = cache.get('EquipConnect', default=None)
                        # DeviceClass
                        device_class = cache.get('DeviceClass')
                        deviceclass = {"EquipName": i['equipment_name'], "EquipNumber": i['equipment_num'],
                                       "EquipIP": i['equipment_ip'], "EquipSerial": i['equipment_serial'],
                                       "EquipStatus": False, "EquipError": False}

                        device_class.append(deviceclass)
                        ApplyEquipConnectStatus(device_class, equip_connect)
                        Cache_writer('DeviceClass', device_class, None)

            # transaction.savepoint_commit(save_id)
            # cs.close()

        meta = {
            "msg": "添加型号管理成功!",
            "result": "OK"
        }

        backdata = {
            "data": xinghao,
            "meta": meta,
        }

        return HttpResponse(List_Json(backdata))

    except Exception as err:
        # transaction.savepoint_rollback(save_id)

        meta = {
            "msg": str(err),
            "result": "NG"
        }

        backdata = {
            "data": xinghao,
            "meta": meta,
        }
        print(err)
        return HttpResponse(List_Json(backdata))

# def AddModels(request):
#     try:
#         meta = {}
#         print(request.POST)
#         data = request.POST.get('data', '')
#         print(data)
#         data = json.loads(data)
#         print(type(data))
#         print(data[0])
#
#         xinghao = request.POST.get('xinghao', '')
#         SQL = "SELECT gp_model FROM model_tab WHERE gp_model = '" + xinghao + "'"
#         print(SQL)
#         cs = connection.cursor()
#         cs.execute(SQL)
#         result = cs.fetchall()
#         cs.close()
#         print(result)
#         if len(result) > 0:
#             print("已经存在" + str(xinghao) + "无法添加")
#             meta = {
#                 "msg": "型号已经存在 无法添加",
#                 "result": "NG"
#             }
#         elif len(result) == 0:
#             SQL = "INSERT INTO model_tab(gp_model,Pass,Fail)VALUES ('" + xinghao + "',0,0)"
#             print(SQL)
#             cs = connection.cursor()
#             result = cs.execute(SQL)
#             if result == 1:
#                 for i in data:
#                     SQL = "INSERT INTO station_tab(equipment_name,equipment_num,equipment_ip,equipment_serial,gp_model)VALUES ('" + \
#                           i["equipment_name"] + "','" + i["equipment_num"] + "','" + i["equipment_ip"] + "','" + i[
#                               "equipment_serial"] + "','" + xinghao + "')"
#                     print(SQL)
#                     result = cs.execute(SQL)
#                     if result == 1:
#                         meta = {
#                             "msg": "添加型号管理成功!",
#                             "result": "OK"
#                         }
#                     else:
#                         meta = {
#                             "msg": "SQL执行失败",
#                             "result": "NG"
#                         }
#                         raise Exception('SQL执行失败！')
#             else:
#                 meta = {
#                     "msg": "SQL执行失败",
#                     "result": "NG"
#                 }
#                 raise Exception('SQL执行失败！')
#
#         backdata = {
#             "data": xinghao,
#             "meta": meta,
#         }
#
#         return HttpResponse(List_Json(backdata))
#
#     except Exception as err:
#
#         meta = {
#             "msg": "添加型号管理失败",
#             "result": "NG"
#         }
#
#         backdata = {
#             "data": xinghao,
#             "meta": meta,
#         }
#         print(err)
#         return HttpResponse(List_Json(backdata))


# --------------------------------删除设备列表----------------------------

@csrf_exempt
def DeleteModel_Device(request):
    try:
        meta = {}
        msg = ""
        tag = False
        print(request)
        id = request.POST.get('id', '')
        # gpmodel = request.POST.get('gpmodel', '')
        # name = request.POST.get('equipname', '')
        print(int(id))
        SQL = "SELECT gp_model,equipment_name FROM station_tab WHERE id = " + id + ""
        cs = connection.cursor()
        cs.execute(SQL)
        result = cs.fetchall()
        cs.close()
        print(result[0][0])
        print(cache.get('current_model'))
        print(result[0][1])

        device_class = cache.get('DeviceClass')
        for it in device_class:
            if result[0][1] == it['EquipName'] and it['EquipStatus']:
                msg = "当前设备已连接,无法删除"
                raise Exception(msg)
        # 当前型号 station_tab 相关的全局变量的同步更新
        if result[0][0] == cache.get('current_model'):
            tag = True

        SQL = "delete from station_tab where id= " + id + ""
        # SQL = " delete from station_tab where equipment_name= '" + name + "' and gp_model='"+gpmodel+"'"
        print(SQL)
        if not sql_execute(SQL):
            meta = {
                "msg": "SQL执行失败!",
                "result": "NG"
            }
            raise Exception('SQL执行失败！')
        else:
            meta = {
                "msg": "删除成功!",
                "result": "OK"
            }

        backdata = {
            "data": {},
            "meta": meta,
        }
        if tag:
            SQL = "SELECT * FROM station_tab WHERE gp_model = '" + cache.get('current_model') + "'"
            print(SQL)
            data = easy_sql_reader(SQL)
            print(data)
            # EquipNumGrop
            data = EquipNumGroup_Ini(data)

            # Equip_Status
            equip_status = cache.get('Equip_Status')
            print(">>>>>>")
            print(equip_status)
            for i in range(len(equip_status)):
                if equip_status[i]['EquipName'] == result[0][1]:
                    equip_status.pop(i)
                    break
            print(equip_status)
            Cache_writer('Equip_Status', equip_status, None)

            # DeviceClass
            device_class = cache.get('DeviceClass')
            print(">>>>>>")
            print(device_class)
            for i in range(len(device_class)):
                if device_class[i]['EquipName'] == result[0][1]:
                    device_class.pop(i)
                    break
            print(device_class)
            Cache_writer('DeviceClass', device_class, None)

        return HttpResponse(List_Json(backdata))

    except Exception as err:
        Data = {

        }
        meta = {
            "msg": msg,
            "result": "NG"
        }

        backdata = {
            "data": Data,
            "meta": meta,
        }
        print(err)
        return HttpResponse(List_Json(backdata))


# --------------------------------获取设备列表----------------------------
@csrf_exempt
def Modeldevices(request):
    try:
        query = request.GET.get('query', '')
        pagenum = request.GET.get('pagenum', '')
        pagesize = request.GET.get('pagesize', '')
        print(query)
        SQL = "select id,equipment_name,equipment_num,equipment_ip,equipment_serial from station_tab WHERE gp_model='" + query + "'"
        print(SQL)

        data = aview_easy_sql_reader_page1(SQL, pagenum, pagesize)
        print(data)

        # 冒泡
        n = len(data['data'])
        for i in range(n):
            # Last i elements are already in place
            for j in range(0, n - i - 1):
                if int(data['data'][j]['equipment_serial']) > int(data['data'][j + 1]['equipment_serial']):
                    data['data'][j], data['data'][j + 1] = data['data'][j + 1], data['data'][j]

        meta = {
            "msg": "获取设备列表成功!",
            "result": "OK"
        }
        backdata = {
            "data": data,
            "meta": meta,
        }

        print(backdata)
        # print(SQL)
        return HttpResponse(List_Json(backdata))

    except Exception as err:
        Data = {

        }
        meta = {
            "msg": "获取设备列表失败",
            "result": "NG"
        }

        backdata = {
            "data": Data,
            "meta": meta,
        }
        # print(err)
        return HttpResponse(List_Json(backdata))


# --------------------------------删除型号----------------------------

@csrf_exempt
def DeleteModel(request):
    try:
        Data = {}
        meta = {}
        print(request)
        gpmodel = request.POST.get('gpmodel', '')
        current_model = cache.get('current_model', default=None)
        if current_model == gpmodel:
            meta = {
                "msg": "删除失败:正在使用的型号禁止删除",
                "result": "NG"
            }
            backdata = {
                "data": Data,
                "meta": meta,
            }
            return HttpResponse(List_Json(backdata))

        SQL = " delete from station_tab where gp_model= '" + gpmodel + "'"
        if not sql_execute(SQL):
            raise Exception('SQL执行失败！')

        SQL = " delete from model_tab where gp_model= '" + gpmodel + "'"
        if not sql_execute(SQL):
            raise Exception('SQL执行失败！')

        SQL = " delete from planorder_partno_tab where gp_model= '" + gpmodel + "'"
        if not SQL_function4(SQL):
            raise Exception('SQL执行失败！')

        # print(SQL)
        meta = {
            "msg": "删除成功!",
            "result": "OK"
        }
        backdata = {
            "data": {},
            "meta": meta,
        }

        return HttpResponse(List_Json(backdata))

    except Exception as err:
        Data = {

        }
        meta = {
            "msg": "删除失败",
            "result": "NG"
        }

        backdata = {
            "data": Data,
            "meta": meta,
        }
        print(err)
        return HttpResponse(List_Json(backdata))

def EditModel_Snway(request):
    try:
        gp_model = request.POST.get('gp_model', '')
        sn_way = request.POST.get('sn_way', '')

        SQL = "UPDATE  model_tab SET sn_way = '" + sn_way + "'WHERE gp_model = '" + gp_model + "'"
        print(SQL)
        # data = easy_sql_reader(SQL)
        if not sql_execute(SQL):
            raise Exception('SQL执行失败！')

        meta = {
            "msg": "修改成功!",
            "result": "OK"
        }
        backdata = {
            "data": {},
            "meta": meta,
        }

        return HttpResponse(List_Json(backdata))

    except Exception as err:
        print(err)
        Data = {

        }
        meta = {
            "msg": "修改失败",
            "result": "NG"
        }

        backdata = {
            "data": Data,
            "meta": meta,
        }
        print(err)
        return HttpResponse(List_Json(backdata))
def Modeldevices_bind(request):
    try:
        bindcolumn_name = GetBindcolumn_name()

        query = request.GET.get('query', '')
        print(query)
        SQL = "select id,equipment_name,equipment_num,equipment_ip,equipment_serial from station_tab WHERE gp_model= '" + query + "'"
        equip_data = SQL_function3(SQL)

        # 冒泡
        n = len(equip_data)
        for i in range(n):
            # Last i elements are already in place
            for j in range(0, n - i - 1):
                if int(equip_data[j]['equipment_serial']) > int(equip_data[j + 1]['equipment_serial']):
                    equip_data[j], equip_data[j + 1] = equip_data[j + 1], equip_data[j]

        # 获取该型号对应的站点绑定对应关系
        SQL = "SELECT * FROM station_bind_tab WHERE gp_model = '" + query + "'"
        bind_data = SQL_function3(SQL)
        sta_bind = eval(bind_data[0]['station_bind'])
        # 补充sta_bind中缺少的站点
        sta_bind_key = list(sta_bind.keys())
        for it in equip_data:
            if not it['equipment_num'] in sta_bind_key:
                sta_bind[it['equipment_num']] = ""

        # 同步设备列表中的绑定信息
        if len(sta_bind) == 0:
            for it in equip_data:
                it['bind_num'] = 0
        else:
            for it in equip_data:
                stno = it['equipment_num']
                for key in sta_bind:
                    if key == stno:
                        bind_name = sta_bind[key]
                        for i in range(len(bindcolumn_name)):
                            if bind_name == bindcolumn_name[i]:
                                it['bind_num'] = i+1
                                break
                        else:
                            it['bind_num'] = 0


        meta = {
            "msg": "获取设备列表成功!",
            "result": "OK"
        }
        backdata = {
            "data": equip_data,
            "meta": meta,
        }

        print(backdata)
        # print(SQL)
        return HttpResponse(List_Json(backdata))

    except Exception as err:
        print(err)
        Data = {

        }
        meta = {
            "msg": str(err),
            "result": "NG"
        }

        backdata = {
            "data": Data,
            "meta": meta,
        }
        # print(err)
        return HttpResponse(List_Json(backdata))
# --------------------------------------------------料盘管理------------------------------------------

@csrf_exempt
def ST_Tarys(request):
    try:
        SQL = "select id,tray_str,gp_model,equipment_num from tray_tab"
        pagenum = request.GET.get('pagenum', '')
        pagesize = request.GET.get('pagesize', '')

        # data = easy_sql_reader(SQL)
        data = aview_easy_sql_reader_page1(SQL, pagenum, pagesize)

        meta = {
            "msg": "获取治具列表成功!",
            "result": "OK"
        }
        backdata = {
            "data": data,
            "meta": meta,
        }

        print(backdata)


        return HttpResponse(json.dumps(backdata, ensure_ascii=False))

    except Exception as err:
        Data = {

        }
        meta = {
            "msg": "获取料号失败",
            "result": "NG"
        }

        backdata = {
            "data": Data,
            "meta": meta,
        }
        # print(err)
        return HttpResponse(json.dumps(backdata, ensure_ascii=False))

@csrf_exempt
def ST_TarysDetail(request):
    try:

        # SQL = "select tray_str,gp_model,equipment_num from tray_tab"
        # WHERE gp_model = 'GP-001' and equipment_num = 'ST02'
        pagenum = request.GET.get('pagenum', '')
        pagesize = request.GET.get('pagesize', '')
        selected_equip = request.GET.get('selected_equip', '')
        # data = sql_list_first(SQL)
        SQL = "SELECT tray_str,equipment_num,gp_model FROM tray_tab WHERE gp_model ='" + cache.get(
            'current_model') + "' and equipment_num = '" + selected_equip + "'"
        SQL_Scan = "SELECT tray_no, tray_status FROM trayscan_tab WHERE gp_model = '" + cache.get('current_model') + "'"
        data = Tray_reader_page(SQL, SQL_Scan ,pagenum, pagesize)

        meta = {
            "msg": "获取治具列表成功!",
            "result": "OK"
        }
        backdata = {
            "data": data,
            "meta": meta,
        }

        print(backdata)

        return HttpResponse(json.dumps(backdata, ensure_ascii=False))

    except Exception as err:
        Data = {

        }
        meta = {
            "msg": "获取料号失败",
            "result": "NG"
        }

        backdata = {
            "data": Data,
            "meta": meta,
        }
        # print(err)
        return HttpResponse(json.dumps(backdata, ensure_ascii=False))

@csrf_exempt
def CheckTraysn(request):
    try:
        Traysn = request.GET.get('Traysn', '')
        SQL = "select tray_str,gp_model,equipment_num from tray_tab WHERE gp_model = '" + cache.get('current_model') + "'and tray_str LIKE '%" + Traysn + "%'"
        print(SQL)
        data = sql_list(SQL)
        print(data)

        if (data == None or data == "" or len(data) == 0):

            backdata = {
                "data": {
                    "tray_str": Traysn,
                    "Status": 0,
                    "gp_model": "",
                    "equipment_num": ""
                },
                "meta": {
                    "msg": "校验治具列表失败!",
                    "result": "NG"
                },
            }

            print(backdata)
        else:
            print("111")
            SQL_Scan = "SELECT tray_no FROM trayscan_tab WHERE tray_no = '" + Traysn + "' and gp_model = '" + cache.get('current_model') + "'"
            print(SQL_Scan)
            data_scan = sql_list(SQL_Scan)
            print(data_scan)
            if len(data_scan) != 0:
                SQL_Scan = "UPDATE trayscan_tab set tray_status = 'OK' where tray_no ='" + Traysn + "' and gp_model = '" + cache.get('current_model') + "'"
                print(SQL_Scan)
                if not sql_execute(SQL_Scan):
                    raise Exception('SQL_Scan UPDATA执行失败！')
            else:
                raise Exception('不存在' + Traysn)
                # SQL_Scan = "INSERT INTO trayscan_tab(tray_no,tray_status,gp_model)VALUES ('" + Traysn + "', 'OK' ," + cache.get('current_model') + ")"
                # print(SQL_Scan)
                # if not sql_execute(SQL_Scan):
                #     raise Exception('SQL_Scan INSERT执行失败！')
            backdata = {
                "data": {
                    "tray_str": Traysn,
                    "Status": 1,
                    "gp_model": data[0][1],
                    "equipment_num": data[0][2]

                },
                "meta": {
                    "msg": "获取治具列表成功!",
                    "result": "OK"
                },
            }
            print(backdata)
        return HttpResponse(json.dumps(backdata, ensure_ascii=False))

    except Exception as err:
        Data = {

        }
        meta = {
            "msg": str(err),
            "result": "NG"
        }

        backdata = {
            "data": Data,
            "meta": meta,
        }
        # print(err)
        return HttpResponse(json.dumps(backdata, ensure_ascii=False))
# ------------------------------获取料盘列表 -----------------------------------------
def tray(request):
    if request.method == "GET":
        try:
            # print(request.GET)
            # print(len(request.GET))
            back_data = []
            back_meta = {}
            SQL = " select id,trayno from tray_tab"
            # cs = connections['aview'].cursor()
            print(SQL)
            cs = connection.cursor()
            cs.execute(SQL)
            data = cs.fetchall()
            cs.close()
            # print(data)
            back_data = []
            for it in data:
                temp_dic = {"id": it[0], "trayno": it[1]}
                back_data.append(temp_dic)
            # print(back_data)
            back_meta = {"msg": "获取料号列表成功", "result": "OK"}
            backdata = {
                "data": back_data,
                "meta": back_meta,
            }
            print(backdata)
            return HttpResponse(List_Json(backdata))

        except Exception as err:
            print(err)
            back_meta = {"msg": str(err), "result": "NG"}
            backdata = {
                "data": back_data,
                "meta": back_meta,
            }
            return HttpResponse(List_Json(backdata))


# ------------------------------获取料盘码 -----------------------------------------
def TarySeries(request):
    print(request.GET)
    try:
        back_data = []
        back_meta = {}
        SQL = "select id,trayno,sn from trayseries_tab WHERE trayno = '" + request.GET.get('selected_tray', '') + "'"
        print(SQL)
        cs = connection.cursor()
        cs.execute(SQL)
        data = cs.fetchall()
        cs.close()
        print(data)
        if len(data) == 0:
            back_meta = {"msg": "获取料号列表为空", "result": "OK"}
        else:
            back_meta = {"msg": "获取料号列表成功", "result": "OK"}
            for it in data:
                back_data.append({"id": it[0], "trayno": it[1], "sn": it[2]})
        backdata = {
            "data": back_data,
            "meta": back_meta,
        }
        return HttpResponse(List_Json(backdata))
    except Exception as err:
        print(err)
        back_meta = {"msg": str(err), "result": "NG"}
        backdata = {
            "data": back_data,
            "meta": back_meta,
        }
        return HttpResponse(List_Json(backdata))


# ------------------------------添加料盘-----------------------------------------
def AddTray(request):
    try:
        back_data = ""
        back_meta = {}
        SQL = " INSERT INTO tray_tab (trayno) VALUES ('" + request.POST.get('trayno', '') + "') "
        print(SQL)
        cs = connection.cursor()
        cs.execute(SQL)
        cs.close()
        back_data = request.POST.get('trayno', '')
        back_meta = {"msg": "添加料盘号成功", "result": "OK"}
        backdata = {
            "data": back_data,
            "meta": back_meta,
        }
        return HttpResponse(List_Json(backdata))
    except Exception as err:
        print(err)
        back_data = request.POST.get('trayno', '')
        back_meta = {"msg": str(err), "result": "NG"}
        backdata = {
            "data": back_data,
            "meta": back_meta,
        }
        return HttpResponse(List_Json(backdata))

@csrf_exempt
def AddTrays(request):
    try:
        # print(request)
        msg1 = ""
        msg2 = ""
        Tag1 = False
        Tag2 = False
        tray = request.POST.get('tray', '')
        model = request.POST.get('model', '')
        station = request.POST.get('station', '')
        print("tray:" + tray + "，model:" + model + "，station:" + station)
        if tray == '' or model == '' or station == '':
            print("AddTrays: tray or model or station is empty")
            raise Exception('参数为空')
        SQL = "select id,tray_str from tray_tab WHERE gp_model='" + model + "' and equipment_num='" + station + "'"
        print(SQL)
        # data = sql_list(SQL)
        data = sql_list_first(SQL)
        print(data)
        # print(data[0])
        if data:
            print(data[1].split(';'))
            print(tray)
            for it in data[1].split(';'):
                if str(it) == str(tray):
                    msg1 = "型号--工位下已经存在该料号"
                    print(msg1)
                    Tag1 = True
            if Tag1 is False:
                tray_new = str(data[1]) + ';' + str(tray)
                print(tray_new)
                SQL = "UPDATE tray_tab set tray_str='" + tray_new + "' where gp_model='" + model + "' and equipment_num='" + station + "'"
                print(SQL)
                if not sql_execute(SQL):
                    raise Exception('SQL执行失败！')
        else:
            print(111)
            SQL = "INSERT INTO tray_tab(tray_str,gp_model,equipment_num)VALUES ('" + tray + "','" + model + "','" + station + "')"
            if not sql_execute(SQL):
                raise Exception('SQL执行失败！')

        SQL_Scan = "select * from trayscan_tab WHERE tray_no= '" + tray + "' and gp_model = '" + model + "'"
        print(SQL_Scan)
        data_scan = sql_list_first(SQL_Scan)
        print(data_scan)
        if data_scan:
            msg2 = "trayscan_tab中" + model + "已经存在" + tray
            print(msg2)
            Tag2 = True
        else:
            print(222)
            SQL_Scan = "INSERT INTO trayscan_tab(tray_no,tray_status,gp_model)VALUES ('" + tray + "','NG','" + model + "')"
            print(SQL_Scan)
            if not sql_execute(SQL_Scan):
                raise Exception('SQL_Scan执行失败！')
        if Tag1 or Tag2:
            raise Exception(Tag1 + Tag2)
        meta = {
            "msg": "添加治具成功!",
            "result": "OK"
        }

        backdata = {
            "data": tray,
            "meta": meta,
        }

        return HttpResponse(List_Json(backdata))

    except Exception as err:

        meta = {
            "msg": str(err),
            "result": "NG"
        }

        backdata = {
            "data": tray,
            "meta": meta,
        }
        print(err)
        return HttpResponse(List_Json(backdata))

# ------------------------------删除料盘-----------------------------------------
@csrf_exempt
def DeleteTray(request):
    try:
        # print(request)

        tray = request.POST.get('trayno', '')

        SQL = " delete from tray_tab where trayno= '" + tray + "'"

        # print(SQL)
        if not sql_execute(SQL):
            raise Exception('SQL执行失败！')

        SQL = " delete from trayseries_tab where trayno= '" + tray + "'"

        # SQL = " delete from station_tab where equipment_name= '" + name + "' and gp_model='"+gpmodel+"'"
        # print(SQL)
        if not sql_execute(SQL):
            raise Exception('SQL执行失败！')

        # print(SQL)
        meta = {
            "msg": "删除成功!",
            "result": "OK"
        }
        backdata = {
            "data": {},
            "meta": meta,
        }

        return HttpResponse(List_Json(backdata))

    except Exception as err:
        Data = {

        }
        meta = {
            "msg": "删除失败",
            "result": "NG"
        }

        backdata = {
            "data": Data,
            "meta": meta,
        }
        print(err)
        return HttpResponse(List_Json(backdata))

# ---------------------------------------------6-27新增--------------------------------------------------
# ----------------------料盘管理----------------------
@csrf_exempt
def pan_list(request):
    try:
        SQL = "select id,panno from pan_tab"

        data = easy_sql_reader(SQL)
        meta = {
            "msg": "获取料号列表成功!",
            "result": "OK"
        }
        backdata = {
            "data": data,
            "meta": meta,
        }

        print(backdata)

        return HttpResponse(json.dumps(backdata, ensure_ascii=False))

    except Exception as err:
        Data = {

        }
        meta = {
            "msg": "获取料号失败",
            "result": "NG"
        }

        backdata = {
            "data": Data,
            "meta": meta,
        }
        # print(err)
        return HttpResponse(json.dumps(backdata, ensure_ascii=False))
# 增加料盘
@csrf_exempt
def AddPan(request):
    try:
        pan = request.POST.get('panno', '')
        SQL = "select id,panno from pan_tab WHERE panno='" + pan + "'"
        data = sql_list(SQL)
        print(data)
        if data:
            raise Exception('料盘'+str(pan)+'已经存在！')

        # data = sql_list_first(SQL)
        SQL = "INSERT INTO pan_tab(panno)VALUES ('" + pan + "')"
        print(SQL)
        if not sql_execute(SQL):
            raise Exception('SQL执行失败！')
        meta = {
            "msg": "添加料盘号成功!",
            "result": "OK"
        }

        backdata = {
            "data": pan,
            "meta": meta,
        }

        return HttpResponse(List_Json(backdata))

    except Exception as err:

        meta = {
            "msg": str(err),
            "result": "NG"
        }

        backdata = {
            "data": pan,
            "meta": meta,
        }
        print(err)
        return HttpResponse(List_Json(backdata))

# --------------------------------获取料盘绑定的对应码----------------------------
@csrf_exempt
def PanSeries(request):
    try:
        seleced_pan = request.GET.get('selected_pan', '')
        SQL = "select id,panno,sn from panseries_tab WHERE panno='" + seleced_pan + "'"

        # print(SQL)

        data = easy_sql_reader(SQL)
        # print(data)
        meta = {
            "msg": "获取料号条码成功!",
            "result": "OK"
        }
        backdata = {
            "data": data,
            "meta": meta,
        }

        print(backdata)
        return HttpResponse(List_Json(backdata))

    except Exception as err:

        meta = {
            "msg": "获取料号条码失败",
            "result": "NG"
        }

        backdata = {
            "data": {},
            "meta": meta,
        }
        return HttpResponse(List_Json(backdata))


# --------------------------------删除料盘哈----------------------------

@csrf_exempt
def DeletePan(request):
    try:
        # print(request)

        pan = request.POST.get('panno', '')
        SQL = " delete from pan_tab where panno= '" + pan + "'"
        # print(SQL)
        if not sql_execute(SQL):
            raise Exception('SQL执行失败！删除料盘失败')

        SQL = " delete from panseries_tab where panno= '" + pan + "'"
        # print(SQL)
        if not sql_execute(SQL):
            raise Exception('SQL执行失败！删除料盘绑定的条码失败')

        # print(SQL)
        meta = {
            "msg": "删除成功!",
            "result": "OK"
        }
        backdata = {
            "data": "",
            "meta": meta,
        }

        return HttpResponse(List_Json(backdata))

    except Exception as err:
        Data = {
        }
        meta = {
            "msg":str(err),
            "result": "NG"
        }

        backdata = {
            "data": "",
            "meta": meta,
        }
        print(err)
        return HttpResponse(List_Json(backdata))

#----------------------------------------治具Fix管理(数据库对应tray)--------------------------------------------------
    # 删除治具 DeleteTrays
@csrf_exempt
def DeleteFixs(request):
    try:
        tray = request.POST.get('tray', '')
        model = request.POST.get('model', '')
        station = request.POST.get('station', '')
        # 检查型号站位下是否存在治具，存在 拿治具列表进行循环 对比成功 则删除治具
        SQL = "select id,tray_str from tray_tab WHERE gp_model='" + model + "' and equipment_num='" + station + "'"
        print(SQL)
        data = sql_list_first(SQL)
        print(data)
        # 是否成功删除的标识
        flag = False
        if data:
            tray_list = str(data[1]).split(';')
            for i in tray_list:
                # 治具在同一型号工位下是唯一的 所以对比到相等信息 则跳出循环
                if i == tray:
                    tray_list.remove(i)
                    if (len(tray_list) == 0):
                        flag = True
                        SQL = "delete from tray_tab  where gp_model='" + model + "' and equipment_num='" + station + "'"
                        if not sql_execute(SQL):
                            raise Exception('SQL执行失败！')
                    else:
                        my_string = ';'.join(tray_list)
                        print(my_string)
                        flag = True
                        SQL = "update tray_tab set tray_str='" + my_string + "' where gp_model='" + model + "' and equipment_num='" + station + "'"
                        if not sql_execute(SQL):
                            raise Exception('SQL执行失败！')
                        break

            if flag == False:
                raise Exception('该治具在该站位下不存在，请检查！！')
        else:
            raise Exception('该型号工位下不存在治具，请检查！！')

        SQL_Scan = "DELETE FROM trayscan_tab WHERE gp_model = '" + model + "' and tray_no = '" + tray + "'"
        print(SQL_Scan)
        if not sql_execute(SQL_Scan):
            raise Exception('SQL_Scan执行失败！')


        meta = {
            "msg": "删除治具成功!",
            "result": "OK"
        }
        backdata = {
            "data": tray,
            "meta": meta,
        }

        return HttpResponse(List_Json(backdata))

    except Exception as err:
        Data = {

        }
        meta = {
            "msg": str(err),
            "result": "NG"
        }

        backdata = {
            "data": Data,
            "meta": meta,
        }
        print(err)
        return HttpResponse(List_Json(backdata))

    # -----------------------------------------生产追溯----------------------------------


# ----------------------查询产品号信息----------------------
# 临时优化 把test_data中数据为空的测试项去除不显示
def ProInfo_emptdata_erase(backdata):
    for it in backdata['data']:
        if it["test_data"] == "":
            continue
        test_data_temp = list(it["test_data"].keys())
        for k in test_data_temp:
            if it["test_data"][k] == "":
                it["test_data"].pop(k)
def ProInfo_emptdata_erase_dl(ret_data):
    try:
        ret_data_temp = copy.deepcopy(ret_data)
        print(">>>>>>ProInfo_emptdata_erase_dl")
        for num1 in range(0, len(ret_data_temp['data'])):
            ret_data['data'][num1]['test_data'] = []
            for num2 in range(0, len(ret_data_temp['data'][num1]['test_data'])):
                try:
                    ret_data_temp['data'][num1]['test_data'][num2]['testvalue']
                except:
                    raise Exception(ret_data_temp['data'][num1]['test_data'][num2])

                if ret_data_temp['data'][num1]['test_data'][num2]['testvalue'] == "" and \
                        ret_data_temp['data'][num1]['test_data'][num2]['result'] == "":
                    continue
                ret_data['data'][num1]['test_data'].append(ret_data_temp['data'][num1]['test_data'][num2])
    except Exception as err:
        log.info(">>>>>>ProInfo_emptdata_erase_dl ERROR:" + str(err))




@csrf_exempt
def ProInfo(request):
    try:
        flag = request.POST.get('flag', '') # 前壳码1 qr_code1、后壳码2 qr_code2、3 pcba_1、4  pcba_2、5 镜头lens、6 stand
        code = request.POST.get('code', '')
        dl_tag = request.POST.get('dl_tag', '')  # 本地下载的请求tag。如果为True，为本地下载，对空数据保留。如果为空 为WEB端进行请求，去除空数据
        log.info("--------ProInfo" + str(code))
        sn = ""
        sn_name = ""
        StandMultiBindTag = False
        multi_snlist = []
        multi_snnamelist = []
        # 前壳码1
        if int(flag) == 1:
            sn_name = "qr_code1"
            sn = code
            # print(flag)
            # 查找产品在工位的测试结果
        elif int(flag) == 2:
            sn_name = "qr_code2"
            sn = code
            # print(flag)
            # 查找产品在工位的测试结果
        # pcba_1
        elif int(flag) == 3:
            SQL = "select qr_code1,qr_code2,pcba_code1,pcba_code2 from qr_bind_tab where  pcba_code1 = '" + code + "'"
            print(SQL)
            data = sql_list_first(SQL)
            print(data)
            # print(len(data))
            if data == None or data == "" or len(data) == 0:
                SQL = "select qr_code1,qr_code2,pcba_code1,pcba_code2 from ordersn_tab where  pcba_code1 = '" + code + "'"
                print(SQL)
                data = sql_list_first(SQL)
                print(data)
                if data == None or data == "" or len(data) == 0:
                    raise Exception("没有找到绑定前端外壳代码")
            sn1 = data[0]
            sn2 = data[1]
            pcb1 = data[2]
            pcb2 = data[3]
            sn = sn1
            sn_name = "qr_code1"
            if sn == None or sn == "":
                sn_name = "qr_code2"
                sn = sn2
            if sn == None or sn == "":
                sn_name = "pcba_code1"
                sn = pcb1
            if sn == None or sn == "":
                sn_name = "pcba_code2"
                sn = pcb2
        # pcba_2
        elif int(flag) == 4:
            SQL = "select qr_code1,qr_code2,pcba_code1,pcba_code2 from qr_bind_tab where pcba_code2= '" + code + "'"
            print(SQL)
            data = sql_list_first(SQL)
            print(data)
            if data == None or data == "" or len(data) == 0:
                SQL = "select qr_code1,qr_code2,pcba_code1,pcba_code2 from ordersn_tab where pcba_code2 = '" + code + "'"
                print(SQL)
                data = sql_list_first(SQL)
                print(data)
                if data == None or data == "" or len(data) == 0:
                    raise Exception("没有找到绑定前端外壳代码")
            # print(data[0])
            sn1 = data[0]
            sn2 = data[1]
            pcb1 = data[2]
            pcb2 = data[3]
            sn = sn1
            sn_name = "qr_code1"
            if sn == None or sn == "":
                sn_name = "qr_code2"
                sn = sn2
            if sn == None or sn == "":
                sn_name = "pcba_code1"
                sn = pcb1
            if sn == None or sn == "":
                sn_name = "pcba_code2"
                sn = pcb2
        # lens
        elif int(flag) == 5:
            SQL = "select qr_code1,qr_code2,pcba_code1,pcba_code2,lens from qr_bind_tab where  lens = '" + code + "'"
            data = sql_list_first(SQL)
            print(data)
            # print(len(data))
            if data == None or data == "" or len(data) == 0:
                if data == None or data == "" or len(data) == 0:
                    SQL = "select qr_code1,qr_code2,pcba_code1,pcba_code2,lens from ordersn_tab where lens = '" + code + "'"
                    print(SQL)
                    data = sql_list_first(SQL)
                    print(data)
                    if data == None or data == "" or len(data) == 0:
                        raise Exception("没有找到绑定前端外壳代码")
            sn1 = data[0]
            sn2 = data[1]
            pcb1 = data[2]
            pcb2 = data[3]
            lens = data[4]
            sn = sn1
            sn_name = "qr_code1"
            if sn == None or sn == "":
                sn_name = "qr_code2"
                sn = sn2
            if sn == None or sn == "":
                sn_name = "pcba_code1"
                sn = pcb1
            if sn == None or sn == "":
                sn_name = "pcba_code2"
                sn = pcb2
            if sn == None or sn == "":
                sn_name = "lens"
                sn = lens
        # stand
        else:
            SQL = "select qr_code1,qr_code2,pcba_code1,pcba_code2 from qr_bind_tab where stand_code = '" + code + "'"
            data = SQL_function3(SQL)
            if data == None or data == "" or len(data) == 0:
                if data == None or data == "" or len(data) == 0:
                    SQL = "select qr_code1,qr_code2,pcba_code1,pcba_code2 from ordersn_tab where  stand_code = '" + code + "'"
                    data = SQL_function3(SQL)
                    if data == None or data == "" or len(data) == 0:
                        raise Exception("没有找到绑定前端外壳代码")
            # 多目情况下，支架码搜索会有多个结果
            if len(data) > 1:
                StandMultiBindTag = True
                for i in range(1,len(data)):
                    for key in data[i]:
                        if data[i][key] == "" or data[i][key] == None:
                            continue
                        else:
                            multi_snlist.append(data[i][key])
                            multi_snnamelist.append(key)

            sn1 = data[0]['qr_code1']
            sn2 = data[0]['qr_code2']
            pcb1 = data[0]['pcba_code1']
            pcb2 = data[0]['pcba_code2']
            sn = sn1
            sn_name = "qr_code1"
            if sn == None or sn == "":
                sn_name = "qr_code2"
                sn = sn2
            if sn == None or sn == "":
                sn_name = "pcba_code1"
                sn = pcb1
            if sn == None or sn == "":
                sn_name = "pcba_code2"
                sn = pcb2
        # 找到pcba副码，辅助搜索
        sn_name2 = ""
        sn2 = ""
        SQL = "select * from qr_bind_tab where " + sn_name + " = '" + sn + "'"
        print(SQL)
        data2 = SQL_function3(SQL)
        print(data2)
        if not len(data2) == 1 and not len(data2) == 0:
            msg = "qr_bind_tab 中存在重复数据"
            raise Exception(msg)
        for it in data2:
            sn_name2 = "pcba_code1"
            sn2 = it['pcba_code1']
            if it['pcba_code1'] == "":
                sn_name2 = "pcba_code2"
                sn2 = it['pcba_code2']
        print(sn_name2)
        print(sn2)
        if sn_name == sn_name2:
            sn_name2 = "lens"
            sn2 = it['lens']
        # 获取生产数据
        SQL = "select distinct B.equipment_name,B.equipment_num,A.id,A.qr_code1,A.qr_code2,A.pcba_code1,A.pcba_code2,A.lens,A.stand_code,A.check_time,A.test_time,A.test_result, A.gp_model, A.part_no, A.part_batch, A.site_name from qr_confrimation_tab A,station_tab B where A.station_no=B.equipment_num and A." + sn_name + "='" + \
              sn + "' ORDER BY equipment_num"
        data1 = SQL_function3(SQL)
        if len(data1) == 0:
            raise Exception("查询数据为空")
        # SP机台
        SQL = "select distinct B.equipment_name,B.equipment_num,A.id,A.qr_code1,A.qr_code2,A.pcba_code1,A.pcba_code2,A.lens,A.stand_code,A.check_time,A.test_time,A.test_result, A.gp_model, A.part_no, A.part_batch from qr_confrimation_tab_sp A,equipment_tab B where A.station_no=B.equipment_num and A." + sn_name + "='" + \
              sn + "' "
        data2 = SQL_function3(SQL)
        if len(data2) > 0:
            for it in data2:
                data1.append(it)

        # 多目产品下，支架锁附站数据补充
        if StandMultiBindTag:
            for i in range(0,len(multi_snlist)):
                SQL = "select distinct B.equipment_name,B.equipment_num,A.id,A.qr_code1,A.qr_code2,A.pcba_code1,A.pcba_code2,A.lens,A.stand_code,A.check_time,A.test_time,A.test_result, A.gp_model, A.part_no, A.part_batch from qr_confrimation_tab_sp A,equipment_tab B where A.station_no=B.equipment_num and A." + multi_snnamelist[i] + "='" + \
                      multi_snlist[i] + "' "
                data2 = SQL_function3(SQL)
                if len(data2) > 0:
                    for it in data2:
                        data1.append(it)


        base_name = ['id', 'start_time', 'end_time', 'qr_code1', 'qr_code2', 'pcba_code1', 'pcba_code2', 'lens', 'stand_code',
                     'station_no', 'test_result', 'gp_model','judge_code']
        for it1 in data1:
            if it1['test_time'] is None or it1['test_time'] == "":
                it1['run_time'] = "0"
            else:
                it1['run_time'] = (datetime.datetime.strptime(it1['test_time'],'%Y-%m-%d %H:%M:%S') - datetime.datetime.strptime(it1['check_time'], '%Y-%m-%d %H:%M:%S')).seconds
            test_data = {}
            it1['test_data'] = ""
            it1['ng_name'] = ""
            tab_name = it1['equipment_num'] + "_test_tab"
            tab_name = tab_name.lower()
            print(tab_name)
            SQL = "SELECT * FROM " + tab_name + " WHERE " + sn_name + " = '" + sn + "'"
            print(SQL)
            data = SQL_function3(SQL)
            print(data)
            if len(data) == 0 and not sn2 == "":
                SQL = "SELECT * FROM " + tab_name + " WHERE " + sn_name2 + " = '" + sn2 + "'"
                print(SQL)
                data = SQL_function3(SQL)
                print(data)
                if len(data) == 0:
                    continue

            data_len = len(data)
            print("len" + str(data_len))
            json_tag = False
            for i in range(0,data_len):
                # print("for" + str(i))
                # print(data[i])
                for key in data[i]:

                    tag = False
                    for it2 in base_name:
                        if it2 == key:
                            tag = True
                            break

                    if tag is False:

                        if i == 0 :
                            test_data[key] = data[i][key]
                        else:
                            if data[i][key] == "" or data[i][key] == None:
                                continue
                            else:
                                test_data[key] = data[i][key]
            print(test_data)


            # 把NG项名称提取出来
            ng_name = ""
            test_data_temp = list(test_data.keys())
            for j in test_data_temp:
                if test_data[j] == "NG":
                    ng_name += str(j)
                    break
            it1['ng_name'] = ng_name

            it1['test_data'] = test_data
        print(data1)

        meta = {
            "msg": "查询条码信息成功!",
            "result": "OK"
        }
        backdata = {
            "data": data1,
            "meta": meta,
        }

        # 临时优化 把test_data中数据为空的测试项去除不显示
        if dl_tag == "":
            ProInfo_emptdata_erase(backdata)

        print(backdata)
        return HttpResponse(json.dumps(backdata, ensure_ascii=False))

    except Exception as err:
        Data = {

        }
        meta = {
            "msg": str(err).replace("\"", ""),
            "result": "NG"
        }

        backdata = {
            "data": Data,
            "meta": meta,
        }
        # print(backdata)
        return HttpResponse(json.dumps(backdata, ensure_ascii=False))
def ProInfo_dl(request):
    flag = request.POST.get('flag', '')
    code = request.POST.get('code', '')
    log.info("--------ProInfo_dl" + str(code))
    myip = Getmyip()
    url = 'http://' + str(myip) + ':9000/api/Product/ProInfo'
    print(url)
    params = {"flag":flag,"code":code,"dl_tag":"True"}
    response = requests.post(url=url, data=params)
    ret_data = json.loads(response.text)
    num = 0
    for it in ret_data['data']:
        num = 0
        data_list = []
        data_dict = {}
        for key in it['test_data']:
            if num == 2:
                num = 0
            if num == 0:
                data_dict['testname'] = key
                data_dict['testvalue'] = it['test_data'][key].replace("\n", "").replace("\r", "")
                num = num + 1
            elif num == 1:
                data_dict['result'] = it['test_data'][key]
                num = num + 1
                data_list.append(data_dict)
                data_dict = {}

        it['test_data'] = data_list

    # 临时优化 把test_data中数据为空的测试项去除不显示
    ProInfo_emptdata_erase_dl(ret_data)
    return HttpResponse(json.dumps(ret_data, ensure_ascii=False))

# def ProInfo_sta(request):
#     print(">>>>>>>>>>>>>>>>>>>ProInfo_sta")
#     try:
#         starttime = request.GET.get('starttime', '')
#         endtime = request.GET.get('endtime', '')
#         stno = request.GET.get('stno', '')
#         stno = stno.lower()
#         st_name = ""
#
#         SQL = "SELECT * FROM equipment_tab"
#         print(SQL)
#         eq_data = easy_sql_reader(SQL)
#         print(eq_data)
#         for eq in eq_data:
#             if eq['equipment_num'] == stno.upper():
#                 st_name = eq['equipment_name']
#         print(st_name)
#
#         SQL = "SELECT * FROM qr_confrimation_tab WHERE check_time BETWEEN '" + starttime + "' AND '" + endtime + "' AND station_no = '" + stno + "'"
#         if "SP" in stno.upper():
#             SQL = "SELECT * FROM qr_confrimation_tab_sp WHERE check_time BETWEEN '" + starttime + "' AND '" + endtime + "' AND station_no = '" + stno + "'"
#
#         print(SQL)
#         data1 = easy_sql_reader(SQL)
#         print(data1)
#         base_name = ['id', 'qr_code1', 'qr_code2', 'pcba_code1', 'pcba_code2', 'lens',
#                      'station_no', 'test_result', 'gp_model', 'judge_code','start_time','end_time']
#         ret_data = []
#         data_len = len(data1)
#         print("len" + str(data_len))
#         json_tag = False
#         for i in range(0, data_len):
#             test_data = {}
#             # print("for" + str(i))
#             # print(data1[i])
#             # 补全绑定的条码
#             bind_name = ['qr_code1', 'qr_code2' , 'pcba_code1', 'pcba_code2']
#             select_name = ""
#             select_code = ""
#             qr_code1 = ""
#             qr_code2 = ""
#             pcba_code1 = ""
#             pcba_code2 = ""
#             lens = ""
#             stand = ""
#             check_time = ""
#             test_time = ""
#             for bind_it in bind_name:
#                 if data1[i][bind_it] == "":
#                     continue
#                 else:
#                     select_name = bind_it
#                     select_code = data1[i][bind_it]
#
#             # print("select_name" + select_name)
#             # print("select_code" + select_code)
#             SQL = "SELECT * FROM ordersn_tab WHERE " + select_name + " = '" + select_code + "'"
#             print(SQL)
#             code_data = easy_sql_reader(SQL)
#             # print("code_data")
#             qr_code1 = code_data[0]['qr_code1']
#             qr_code2 = code_data[0]['qr_code2']
#             pcba_code1 = code_data[0]['pcba_code1']
#             pcba_code2 = code_data[0]['pcba_code2']
#             lens = code_data[0]['lens']
#             stand_code = code_data[0]['stand_code']
#             SQL = "SELECT * FROM qr_confrimation_tab WHERE " + select_name + " = '" + select_code + "' AND station_no = '" + stno + "'"
#             if "SP" in stno.upper():
#                 SQL = "SELECT * FROM qr_confrimation_tab_sp WHERE " + select_name + " = '" + select_code + "' AND station_no = '" + stno + "'"
#             print(SQL)
#             code_data = easy_sql_reader(SQL)
#             check_time = code_data[0]['check_time']
#             test_time = code_data[0]['test_time']
#             run_time = "0"
#             if check_time is None or check_time == "" or test_time is None or test_time == "":
#                 run_time = "0"
#             else:
#                 run_time = (datetime.datetime.strptime(test_time,'%Y-%m-%d %H:%M:%S') - datetime.datetime.strptime(check_time, '%Y-%m-%d %H:%M:%S')).seconds
#
#             name_list = ['qr_code1', 'qr_code2', 'pcba_code1', 'pcba_code2']
#             value_list = [qr_code1, qr_code2, pcba_code1, pcba_code2]
#             SQL = "SELECT * FROM " + stno + "_test_tab WHERE "
#
#             temp_tag = False
#             for num in range(0,len(name_list)):
#                 if not value_list[num] == "":
#                     if temp_tag:
#                         SQL += " or "
#                     SQL += name_list[num] + " = '" + value_list[num] + "'"
#                     temp_tag = True
#
#
#             data_sta = SQL_function3(SQL)
#
#             if not len(data_sta) == 0:
#                 for num in range(0,len(name_list)):
#                     a = data_sta[0][name_list[num]]
#                     b = value_list[num]
#                     c = value_list[num]
#                     if a == b and (not c == ""):
#                         break
#                 else:
#                     data_sta = []
#                 for j in range(0,len(data_sta)):
#                     for key in data_sta[j]:
#                         # print("key" + key)
#                         tag = False
#                         for it2 in base_name:
#                             if it2 == key:
#                                 tag = True
#                                 break
#                         # print(tag)
#                         if tag is False:
#                             # print(key)
#                             # print(data_sta[j][key])
#                             if not key in test_data.keys():
#                                 test_data[key] = data_sta[j][key]
#                             elif test_data[key] == "":
#                                 test_data[key] = data_sta[j][key]
#
#             temp_data = {
#                 "equipment_name": st_name,
#                 "equipment_num": stno.upper(),
#                 "id": data1[i]['id'],
#                 "qr_code1": qr_code1,
#                 "qr_code2": qr_code2,
#                 "pcba_code1": pcba_code1,
#                 "pcba_code2": pcba_code2,
#                 "lens": lens,
#                 "stand_code": stand_code,
#                 "check_time": check_time,
#                 "test_time": test_time,
#                 "run_time": run_time,
#                 "test_result": data1[i]['test_result'],
#                 "gp_model": data1[i]['gp_model'],
#                 "test_data": test_data
#             }
#             # 遍历返回总表 去重,合并数据项(终检机台会单独2次上传测试数据，web显示前要合并)
#             same_tag = False
#             for it in ret_data:
#                 if it['qr_code1'] == temp_data['qr_code1'] and it['qr_code2'] == temp_data['qr_code2'] and it['pcba_code1'] == temp_data['pcba_code1'] and it['pcba_code2'] == temp_data['pcba_code2'] and it['lens'] == temp_data['lens']:
#                     same_tag = True
#                     for key in it['test_data']:
#                         if it['test_data'][key] == "":
#                             it['test_data'][key] = temp_data['test_data'][key]
#
#             # 该数据添加到返回总表中
#             if same_tag is False:
#                 ret_data.append(temp_data)
#
#         meta = {
#             "msg": "查询站位信息成功!",
#             "result": "OK"
#         }
#         backdata = {
#             "data": ret_data,
#             "meta": meta,
#         }
#
#     except Exception as err:
#         meta = {
#             "msg": str(err).replace("\"", ""),
#             "result": "NG"
#         }
#
#         backdata = {
#             "data": {},
#             "meta": meta,
#         }
#     print("backdata----------------------")
#     print(backdata)
#     return HttpResponse(json.dumps(backdata, ensure_ascii=False))
def ProInfo_sta(request):
    ret_data = {}
    try:
        print(">>>>>>>>ProInfo_sta")
        print("---------1  "+str(datetime.datetime.now()))
        a_time = str(datetime.datetime.now())

        starttime = request.GET.get('starttime', '')
        endtime = request.GET.get('endtime', '')
        stno = request.GET.get('stno', '').lower()
        dl_tag = request.GET.get('dl_tag', '')
        log.info("--------ProInfo_sta" + str(stno))

        ret_data = {}
        data = []
        test_tab_name = []
        test_tab_name.append(stno)
        all_tab_data_bucket = {'st01':{},'st02':{},'st03':{},'st04':{},'st05':{},'st06':{},'st07':{},'st08':{},'st09':{},'st10':{},'st11':{},'st12':{},'st13':{},'st14':{},'sp20':{},'sp21':{}}        #分别存储各个表的数据
        code_name = ['qr_code1','pcba_code1','qr_code2','pcba_code2','lens']
        for it in test_tab_name:
            data_tag = False
            for it2 in code_name:
                SQL = "select * from " + it + "_test_tab as a inner JOIN (select * from qr_confrimation_tab where check_time BETWEEN '" + starttime + "' and '" + endtime + "') as b ON a." + it2 + " = b." + it2 + " and b." + it2 + " != '' and a.station_no = b.station_no"
                if "SP" in stno.upper():
                    SQL = "select * from " + it + "_test_tab as a inner JOIN (select * from qr_confrimation_tab_sp where check_time BETWEEN '" + starttime + "' and '" + endtime + "') as b ON a." + it2 + " = b." + it2 + " and b." + it2 + " != '' and a.station_no = b.station_no"
                sql_data = SQL_function3(SQL)
                if len(sql_data) > 0:
                    all_tab_data_bucket[it][it2] = sql_data
                    data_tag = True
                    break     # 若线体生产多种型号，导致单站的主码会切换，应遍去除break 历所有码的数据对应情况。目前线体切换的型号对应各站使用的主码不变，break用于加快速度

            # if data_tag:
            #     data.extend(sql_data)

        print("---------2  " + str(datetime.datetime.now()))
        code_cloumn_name = ['id','datetime','serial_no','qr_code1', 'qr_code2', 'pcba_code1','pcba_code2', 'lens', 'station_no','check_result','test_result','gp_model','station_no','pcba_code2', 'lens', 'station_no','check_result','test_result','gp_model','station_no','site_name','stand_code','check_time','test_time','part_no','part_batch']
        data_cloumn_name = ['start_time','end_time','judge_code','id']

        # 单站点信息排序 为后期合并信息/查找信息做基础
        for stno_key in all_tab_data_bucket.keys():
            for name in code_name:
                if name in all_tab_data_bucket[stno_key].keys():
                    sta_data = all_tab_data_bucket[stno_key][name]
                    sta_data.sort(key=lambda x: x[name])
        # 合并同站同码信息
        for stno_key in all_tab_data_bucket.keys():
            for name in code_name:
                if name in all_tab_data_bucket[stno_key].keys():
                    all_tab_data_bucket[stno_key][name] = Merge_data(all_tab_data_bucket[stno_key][name])

        all_tab_data_bucket_temp = copy.deepcopy(all_tab_data_bucket)

        # 筛选 合并test_data
        for stno_key in all_tab_data_bucket_temp.keys():
            for cloumn_name in code_name:
                if cloumn_name in all_tab_data_bucket[stno_key].keys():
                    data = copy.deepcopy(all_tab_data_bucket[stno_key][cloumn_name])
                else:
                    continue

                data_temp = copy.deepcopy(data)
                data = []
                for num in range(0, len(data_temp)):
                    test_data_temp = data_temp[num]
                    data_item = {}
                    data_item_testdata = {}
                    for key in test_data_temp:
                        data_flag = False
                        for name in code_cloumn_name:
                            if key == name:
                                data_flag = True
                                break

                        if data_flag:
                            data_item[key] = test_data_temp[key]
                            continue
                        if key in data_cloumn_name:
                            continue
                        data_item_testdata[key] = test_data_temp[key]

                    data_item['test_data'] = data_item_testdata
                    data.append(data_item)

                all_tab_data_bucket[stno_key][cloumn_name] = copy.deepcopy(data)
        print("---------3  " + str(datetime.datetime.now()))
        # 汇总单站数据用于返回
        ret_data['data'] = []
        for key in all_tab_data_bucket[stno]:
            for it in all_tab_data_bucket[stno][key]:
                ret_data['data'].append(it)
        # ret_data['data'] = all_tab_data_bucket[stno]
        print(a_time)
        print("---------4  " + str(datetime.datetime.now()))

        meta = {
                    "msg": "查询站位信息成功!",
                    "result": "OK"
                }

        ret_data['meta'] = meta

        # 临时优化 把test_data中数据为空的测试项去除不显示
        if dl_tag == "":
            ProInfo_emptdata_erase(ret_data)

    except Exception as err:
        print(err)
        meta = {
            "msg": str(err),
            "result": "NG"
        }
        ret_data['data'] = []
        ret_data['meta'] = meta

    return HttpResponse(json.dumps(ret_data, ensure_ascii=False))
def ProInfo_sta_dl(request):
    stno = request.GET.get('stno', '')
    starttime = request.GET.get('starttime', '')
    endtime = request.GET.get('endtime', '')
    log.info("--------ProInfo_sta_dl" + str(stno))

    myip = Getmyip()
    url = 'http://' + str(myip) + ':9000/api/Product/ProInfo_sta'
    print(url)
    params = {"stno": stno, "starttime": starttime,"endtime": endtime, "dl_tag": "True"}
    response = requests.get(url=url, params=params)
    ret_data = json.loads(response.text)
    num = 0
    for it in ret_data['data']:
        num = 0
        data_list = []
        data_dict = {}
        for key in it['test_data']:
            if num == 2:
                num = 0
            if num == 0:
                data_dict['testname'] = key
                data_dict['testvalue'] = it['test_data'][key].replace("\n", "").replace("\r", "")
                num = num + 1
            elif num == 1:
                data_dict['result'] = it['test_data'][key]
                num = num + 1
                data_list.append(data_dict)
                data_dict = {}

        it['test_data'] = data_list
    # print(ret_data)

    # 临时优化 把test_data中数据为空的测试项去除不显示
    ProInfo_emptdata_erase_dl(ret_data)

    return HttpResponse(json.dumps(ret_data, ensure_ascii=False))
# def ProInfo_time(request):
#     try:
#         starttime = request.GET.get('starttime', '')
#         endtime = request.GET.get('endtime', '')
#         gp_model = request.GET.get('gp_model', '')
#         ret_data = {}
#         data = []
#         SQL = "SELECT * FROM qr_confrimation_tab WHERE check_time BETWEEN '" + starttime + "' AND '" + endtime + "'"
#         if not gp_model == "":
#             SQL += "AND gp_model = '" + gp_model + "'"
#         data1 = SQL_function3(SQL)
#         for it in data1:
#             temp_data = {}
#             temp_data["test_data"] = {}
#             temp_data["qr_code1"] = it['qr_code1']
#             temp_data["qr_code2"] = it['qr_code2']
#             temp_data["pcba_code1"] = it['pcba_code1']
#             temp_data["pcba_code2"] = it['pcba_code2']
#             temp_data["lens"] = it['lens']
#             temp_data["stand_code"] = it['stand_code']
#             temp_data["gp_model"] = it['gp_model']
#
#             temp_data["equipment_num"] = it['station_no']
#             temp_data["equipment_name"] = ""
#             temp_data["site_name"] = it['site_name']
#             temp_data["part_no"] = it['part_no']
#             temp_data["part_batch"] = it['part_batch']
#
#             data.append(temp_data)
#
#         cloumn_name = ['qr_code1','qr_code2','pcba_code1','pcba_code2','lens','station_no','test_result','gp_model',
#                        'judge_code','id','start_time','end_time']
#         for it in data:
#             SQL = "SELECT * FROM " + it['equipment_num'] + "_test_tab WHERE qr_code1 = '" + temp_data["qr_code1"] \
#                   + "' or qr_code2 = '" + temp_data["qr_code2"] + "' or pcba_code1 = '" + temp_data["pcba_code1"] \
#                   + "' or pcba_code2 = '" + temp_data["pcba_code2"] + "'"
#             data2 = SQL_function3(SQL)
#             if len(data2) == 0:
#                 msg = it['equipment_num'] + "数据表中未找到对应的数据"
#                 print(msg)
#                 continue
#             for key in data2[0]:
#                 data_flag = False
#                 for name in cloumn_name:
#                     if key == name:
#                         data_flag = True
#                         break
#                 if data_flag:
#                     continue
#                 it['test_data'][key] = data2[0][key]
#             print("----------")
#             print(it['test_data'])
#         if len(data) == 0:
#             ret_data['data'] = data
#         else:
#             ret_data['data'] = data
#
#         meta = {
#             "msg": "查询站位信息成功!",
#             "result": "OK"
#         }
#         ret_data['meta'] = meta
#     except Exception as err:
#         print(err)
#         meta = {
#             "msg": str(err),
#             "result": "NG"
#         }
#         ret_data['meta'] = meta
#     print(ret_data)
#
#     num = 0
#     for it in ret_data['data']:
#         data_list = []
#         data_dict = {}
#         for key in it['test_data']:
#             if num == 2:
#                 num = 0
#             if num == 0:
#                 data_dict['testname'] = key
#                 data_dict['testvalue'] = it['test_data'][key]
#                 num = num + 1
#             elif num == 1:
#                 data_dict['result'] = it['test_data'][key]
#                 num = num + 1
#                 data_list.append(data_dict)
#                 data_dict = {}
#
#         it['test_data'] = data_list
#     print(ret_data)
#
#     return HttpResponse(json.dumps(ret_data, ensure_ascii=False))
def Merge_msg(item1,item2):
    for key in item1:
        if item1[key] == "" and not item2[key] == "":
            item1[key] = item2[key]
def Merge_data(data):
    data_len = len(data)
    data_temp = []
    item_temp = data[0]

    for num in range(1,len(data)):
        this_item = data[num]
        if this_item['qr_code1'] == item_temp['qr_code1'] and this_item['qr_code2'] == item_temp['qr_code2'] and this_item['pcba_code1'] == item_temp['pcba_code1'] and this_item['pcba_code2'] == item_temp['pcba_code2']:
            Merge_msg(item_temp,data[num])
        else:
            data_temp.append(item_temp)
            item_temp = data[num]
            if num < len(data) -1:
                num += 1
            else:
                break
    return data_temp
# 折半查找
def binarySearch(arr, l, r, x, code_name):
    if r >= l:
        mid = int(l + (r - l) / 2)
        if arr[mid][code_name] == x[code_name]:
            return mid
        elif arr[mid][code_name] > x[code_name]:
            return binarySearch(arr, l, mid - 1, x, code_name)
        else:
            return binarySearch(arr, mid + 1, r, x, code_name)
    else:
        # 不存在
        return -1
async def ProInfo_time(request):
    log.info("------sql_t :ProInfo_time:" + "\n " + "t_num:" + str(threading.active_count()) + "\n " + "t_msg:" + str(
        threading.enumerate()) + "\n " + "this_t_msg:" + str(threading.current_thread()))

    ret_data = {}
    try:
        print("---------1  "+str(datetime.datetime.now()))
        a_time = str(datetime.datetime.now())

        starttime = request.GET.get('starttime', '')
        endtime = request.GET.get('endtime', '')
        gp_model = request.GET.get('gp_model', '')

        way = request.GET.get('way','')

        log.info("--------ProInfo_time" + str(gp_model))

        ret_data = {}
        data = []
        test_tab_name = ['st01','st02','st03','st04','st05','st06','st07','st08','st09','st10','st11','st12','st13','st14']
        all_tab_data_bucket = {'st01':{},'st02':{},'st03':{},'st04':{},'st05':{},'st06':{},'st07':{},'st08':{},'st09':{},'st10':{},'st11':{},'st12':{},'st13':{},'st14':{}}        #分别存储各个表的数据



        #顺序很重要，遵守当前线体主码可能出现的顺序
        code_name = ['qr_code1','pcba_code1','pcba_code2','qr_code2','lens']
        if way == "":
            for it in test_tab_name:
                data_tag = False
                for it2 in code_name:
                    SQL = "select * from " + it + "_test_tab as a inner JOIN (select * from qr_confrimation_tab where check_time BETWEEN '" + starttime + "' and '" + endtime + "' and gp_model = '" + gp_model + "') as b ON a." + it2 + " = b." + it2 + " and b." + it2 + " != '' and a.station_no = b.station_no"
                    sql_data = SQL_function3(SQL)
                    if len(sql_data) > 0:
                        all_tab_data_bucket[it][it2] = sql_data
                        data_tag = True
                        break  # 若线体生产多种型号，导致单站的主码会切换，应遍去除break 历所有码的数据对应情况。目前线体切换的型号对应各站使用的主码不变，break用于加快速度
        else:
            # 优化异步版本的数据库查询逻辑
            from concurrent.futures import ThreadPoolExecutor, as_completed
            future_set = set()

            code_name = ['qr_code1', 'pcba_code1', 'pcba_code2', 'qr_code2', 'lens']
            with ThreadPoolExecutor(len(test_tab_name)) as executor:
                for it in test_tab_name:
                    data_tag = False
                    for it2 in code_name:
                        all_tab_data_bucket[it][it2] = []
                        SQL = "select * from " + it + "_test_tab as a inner JOIN (select * from qr_confrimation_tab where check_time BETWEEN '" + starttime + "' and '" + endtime + "' and gp_model = '" + gp_model + "') as b ON a." + it2 + " = b." + it2 + " and b." + it2 + " != '' and a.station_no = b.station_no"
                        future = executor.submit(asy_SQL_function3, SQL, it + ":" + it2)
                        future_set.add(future)
            for future in as_completed(future_set):
                error = future.exception()
                if error is not None:
                    raise error

            for future in future_set:
                sql_dict = future.result()
                keys = sql_dict.keys()
                for key in keys:
                    stno = key.split(":")[0]
                    retcode_name = key.split(":")[1]
                    if sql_dict[key] == []:
                        all_tab_data_bucket[stno].pop(retcode_name)
                        continue
                    all_tab_data_bucket[stno][retcode_name] = sql_dict[key]
            # for it in test_tab_name:
            #     for it2 in code_name:
            #         if all_tab_data_bucket[it][it2] == []:
            #             all_tab_data_bucket[it].pop(it2)
        # return HttpResponse(json.dumps(all_tab_data_bucket, ensure_ascii=False))


        print("---------2  " + str(datetime.datetime.now()))
        code_cloumn_name = ['id','datetime','serial_no','qr_code1', 'qr_code2', 'pcba_code1','pcba_code2', 'lens', 'station_no','check_result','test_result','gp_model','station_no','pcba_code2', 'lens', 'station_no','check_result','test_result','gp_model','station_no','site_name','stand_code','check_time','test_time','part_no','part_batch']
        data_cloumn_name = ['start_time','end_time','judge_code','id']

        # 单站点信息排序 为后期合并信息/查找信息做基础
        for stno_key in all_tab_data_bucket.keys():
            for name in code_name:
                if name in all_tab_data_bucket[stno_key].keys():
                    sta_data = all_tab_data_bucket[stno_key][name]
                    sta_data.sort(key=lambda x: x[name])
        # 合并同站同码信息
        for stno_key in all_tab_data_bucket.keys():
            for name in code_name:
                if name in all_tab_data_bucket[stno_key].keys():
                    all_tab_data_bucket[stno_key][name] = Merge_data(all_tab_data_bucket[stno_key][name])

        all_tab_data_bucket_temp = copy.deepcopy(all_tab_data_bucket)

        # 过滤测试数据信息 且打包成组
        for stno_key in all_tab_data_bucket_temp.keys():
            for cloumn_name in code_name:
                if cloumn_name in all_tab_data_bucket[stno_key].keys():
                    data = copy.deepcopy(all_tab_data_bucket[stno_key][cloumn_name])
                else:
                    continue
                data_temp = copy.deepcopy(data)
                data = []
                for num in range(0, len(data_temp)):
                    test_data_temp = data_temp[num]
                    data_item = {}
                    data_item_testdata = {}
                    for key in test_data_temp:
                        data_flag = False
                        for name in code_cloumn_name:
                            if key == name:
                                data_flag = True
                                break

                        if data_flag:
                            data_item[key] = test_data_temp[key]
                            continue
                        if key in data_cloumn_name:
                            continue
                        data_item_testdata[key] = test_data_temp[key]

                    data_item['test_data'] = data_item_testdata
                    data.append(data_item)
                # 转化测试数据格式
                num = 0
                for it in data:
                    data_list = []
                    data_dict = {}
                    for key in it['test_data']:
                        if num == 2:
                            num = 0
                        if num == 0:
                            data_dict['testname'] = key
                            data_dict['testvalue'] = str(it['test_data'][key]).replace("\n", "").replace("\r", "")

                            num = num + 1
                        elif num == 1:
                            data_dict['result'] = it['test_data'][key]
                            data_dict['stno'] = it['station_no']
                            num = num + 1
                            data_list.append(data_dict)
                            data_dict = {}

                    it['test_data'] = data_list

                all_tab_data_bucket[stno_key][cloumn_name] = copy.deepcopy(data)
        print("---------3  " + str(datetime.datetime.now()))

        # 合并异站同码信息
        bucket_code_num = 0
        for stno_key in all_tab_data_bucket_temp.keys():
            for cloumn_name in code_name:
                if cloumn_name in all_tab_data_bucket[stno_key].keys():
                    bucket_code_num += len(all_tab_data_bucket[stno_key][cloumn_name])

        ret_data_bucket = []
        all_tab_data_bucket_temp = copy.deepcopy(all_tab_data_bucket)

        while not bucket_code_num == 0:
            # for cloumn_name in code_name:
            for name_num in range(0,len(code_name)):
                cloumn_name = code_name[name_num]
                for num in range(len(test_tab_name)):
                    if cloumn_name in all_tab_data_bucket[test_tab_name[num]].keys():
                        while not len(all_tab_data_bucket[test_tab_name[num]][cloumn_name]) == 0:
                            this_item = all_tab_data_bucket[test_tab_name[num]][cloumn_name][0]
                            # all_tab_data_bucket_temp[test_tab_name[num]][cloumn_name].remove(this_item)
                            all_tab_data_bucket[test_tab_name[num]][cloumn_name].remove(this_item)
                            bucket_code_num -= 1
                            num2 = num + 1

                            for num2 in range(num2, len(test_tab_name)):
                                # 对线体组装过程中主码改变的兼容，当前cloumn_name主码类型搜索不到时切换到下一个主码类型搜索，将主码有变的特殊情况考虑进去
                                cloumn_name_find = cloumn_name
                                name_num_find = name_num
                                for name_num_find in range(name_num,len(code_name)):
                                    cloumn_name_find = code_name[name_num_find]
                                    arr = []
                                    if cloumn_name_find in all_tab_data_bucket[test_tab_name[num2]].keys():
                                        arr = all_tab_data_bucket[test_tab_name[num2]][cloumn_name_find]
                                        break
                                    else:
                                        continue
                                # 在该站该主码bucket中搜索
                                result = binarySearch(arr, 0, len(arr) - 1, this_item, cloumn_name_find)
                                if result == -1:
                                    continue
                                else:
                                    new_item = all_tab_data_bucket[test_tab_name[num2]][cloumn_name_find][result]
                                    # 同步该站测试结果
                                    this_item['test_result'] = new_item['test_result']
                                    # 合并该站测试数据
                                    for it in new_item['test_data']:
                                        this_item['test_data'].append(it)

                                    # all_tab_data_bucket_temp[test_tab_name[num2]][cloumn_name].remove(
                                    #     new_item)
                                    all_tab_data_bucket[test_tab_name[num2]][cloumn_name_find].remove(
                                        new_item)
                                    bucket_code_num -= 1
                            ret_data_bucket.append(this_item)
                            # all_tab_data_bucket = copy.deepcopy(all_tab_data_bucket_temp)
        print(a_time)
        print("---------4  " + str(datetime.datetime.now()))
        meta = {
                    "msg": "查询站位信息成功!",
                    "result": "OK"
                }
        ret_data['data'] = ret_data_bucket
        ret_data['meta'] = meta

        ProInfo_emptdata_erase_dl(ret_data)
    except Exception as err:
        print(err)
        meta = {
            "msg": str(err),
            "result": "NG"
        }
        ret_data['data'] = []
        ret_data['meta'] = meta

    return HttpResponse(json.dumps(ret_data, ensure_ascii=False))
async def ProInfo_time_dl(request):
    starttime = request.GET.get('starttime', '')
    endtime = request.GET.get('endtime', '')
    gp_model = request.GET.get('gp_model', '')
    log.info("--------ProInfo_time_dl" + str(gp_model))

    myip = Getmyip()
    url = 'http://' + str(myip) + ':9000/api/Product/ProInfo_time'
    print(url)
    params = {"gp_model": gp_model, "starttime": starttime, "endtime": endtime, "dl_tag": "True"}
    response = requests.get(url=url, params=params)
    ret_data = json.loads(response.text)

    # print(ret_data)

    temp_list = []
    data_back = {
        "data":[],
        "meta": {
            "msg": "查询站位信息成功!",
            "result": "OK"
        }
    }

    return HttpResponse(json.dumps(ret_data, ensure_ascii=False))

def ProInfo_history(request):
    try:
        flag = request.POST.get('flag', '') # 前壳码1 qr_code1、后壳码2 qr_code2、3 pcba_1、4  pcba_2、5 镜头lens、6 stand
        code = request.POST.get('code', '')
        dl_tag = request.POST.get('dl_tag', '')  # 本地下载的请求tag。如果为True，为本地下载，对空数据保留。如果为空 为WEB端进行请求，去除空数据
        log.info("--------ProInfo_history" + str(code))
        print(flag)
        print(code)
        sn = ""
        sn_name = ""
        # 前壳码1
        if int(flag) == 1:
            sn_name = "qr_code1"
            sn = code
            # print(flag)
            # 查找产品在工位的测试结果
        elif int(flag) == 2:
            sn_name = "qr_code2"
            sn = code
            # print(flag)
            # 查找产品在工位的测试结果
        # pcba_1
        elif int(flag) == 3:
            sn_name = "pcba_code1"
            sn = code
        elif int(flag) == 4:
            sn_name = "pcba_code2"
            sn = code
        # lens
        elif int(flag) == 5:
            sn_name = "lens"
            sn = code
        # stand
        else:
            sn_name = "stand_code"
            sn = code

        # 获取生产数据
        ret_data = []
        SQL = "select * from st_history_test_tab where " + sn_name + "='" + \
              sn + "' ORDER BY station_no"
        data = SQL_function3(SQL)
        if len(data) == 0:
            raise Exception("查询数据为空")
        else:
            for it in data:
                it['test_data'] = it['test_data'].replace("\n", "").replace("\r", "")
                print("test_data0" + str(it['test_data']))
                test_data = json.loads(json.dumps(eval(it['test_data'])))
                it['test_data'] = test_data
                print("test_data1" + str(test_data))
                # 把NG项名称提取出来
                ng_name = ""
                test_data_temp = list(test_data.keys())
                for j in test_data_temp:
                    if test_data[j] == "NG":
                        ng_name += str(j)
                        break
                it['ng_name'] = ng_name
                ret_data.append(it)

        for it in ret_data:
            it['check_time'] = it['start_time']
            it['test_time'] = it['end_time']

        meta = {
            "msg": "查询条码信息成功!",
            "result": "OK"
        }
        backdata = {
            "data": ret_data,
            "meta": meta,
        }
        print(backdata)
        # 临时优化 把test_data中数据为空的测试项去除不显示
        # if dl_tag == "":
        #     ProInfo_emptdata_erase(backdata)

        return HttpResponse(json.dumps(backdata, ensure_ascii=False))

    except Exception as err:
        Data = {

        }
        meta = {
            "msg": str(err).replace("\"", ""),
            "result": "NG"
        }

        backdata = {
            "data": Data,
            "meta": meta,
        }
        log.info(">>>>>>ProInfo_history ERROR " + str(err))
        return HttpResponse(json.dumps(backdata, ensure_ascii=False))

def ProInfo_history_dl(request):
    flag = request.POST.get('flag', '')
    code = request.POST.get('code', '')
    log.info("--------ProInfo_history_dl" + str(code))
    myip = Getmyip()
    url = 'http://' + str(myip) + ':9000/api/Product/ProInfo_history'
    print(url)
    params = {"flag":flag,"code":code,"dl_tag":"True"}
    response = requests.post(url=url, data=params)
    ret_data = json.loads(response.text)
    num = 0
    for it in ret_data['data']:
        data_list = []
        data_dict = {}
        for key in it['test_data']:
            if num == 2:
                num = 0
            if num == 0:
                data_dict['testname'] = key
                data_dict['testvalue'] = it['test_data'][key].replace("\n", "").replace("\r", "")
                num = num + 1
            elif num == 1:
                data_dict['result'] = it['test_data'][key]
                num = num + 1
                data_list.append(data_dict)
                data_dict = {}

        it['test_data'] = data_list

    # 临时优化 把test_data中数据为空的测试项去除不显示
    ProInfo_emptdata_erase_dl(ret_data)
    return HttpResponse(json.dumps(ret_data, ensure_ascii=False))

# ---------------------根据型号查询产品生产信息-----------------------
def ModelInfo(request):
    try:
        model = request.GET.get('model', '')
        pagenum = request.GET.get('pagenum', '')
        pagesize = request.GET.get('pagesize', '')

        SQL = "select  gp_model as model, SUM(Pass)+SUM(Fail) as total,SUM(Pass) as good,SUM(Fail) as ng ,ROUND(SUM(Pass)/(SUM(Pass)+SUM(Fail)),2) as rate from model_tab"
        if len(model) != 0:
            SQL += " where gp_model='" + str(model) + "' "
        SQL += " GROUP BY gp_model"
        # print(SQL)

        data = aview_easy_sql_reader_page1(SQL, pagenum, pagesize)
        meta = {
            "msg": "获取成功!",
            "result": "OK"
        }
        backdata = {
            "data": data,
            "meta": meta,
        }

        # print(backdata)
        # print(SQL)
        return HttpResponse(List_Json(backdata))

    except Exception as err:
        print(err)
        return HttpResponse('{"status": "NG", "msg":"' + str(err).replace("\"", "") + '"}')

# -----------------------根据工位型号查询产品生产信息--------- 生产良率统计 -----------
def StaInfo(request):
    try:
        model = request.GET.get('model', '')
        sta = request.GET.get('sta', '')
        all_sta = request.GET.get('all_sta', '')
        starttime = request.GET.get('starttime', '')
        endtime = request.GET.get('endtime', '')
        if model == "" or starttime == "" or endtime == "":
            msg = "型号或时间参数不能为空"
            raise Exception(msg)
        if sta == "" and all_sta == "False":
            msg = "站点参数不能为空"
            raise Exception(msg)

        if not all_sta == "":
            all_sta = eval(all_sta)
        sta = sta.split("-")

        if all_sta:
            device_class = cache.get('DeviceClass')
            sta_tem = []
            for it in device_class:
                sta_tem.append(it['EquipNumber'])
            sta = sta_tem

        ret_list = []
        for it in sta:
            SQL = "SELECT station_no,SUM(tiaojian = 1) + SUM(tiaojian = 0) as total,SUM(tiaojian = 1) As good,SUM(tiaojian = 0) As ng " \
                  "FROM (select station_no, CASE when test_result='OK' then 1  when test_result='NG' then 0 END AS tiaojian from qr_confrimation_tab " \
                  "where station_no = '" + it + "' and gp_model = '" + model + "' and check_time BETWEEN '" + starttime + "' and  '" + endtime + "')B  "
            print(SQL)
            data = SQL_function3(SQL)
            if data[0]['total'] == "":
                data[0]['station_no'] = it
                data[0]['total'] = "0"
                data[0]['good'] = "0"
                data[0]['ng'] = "0"
            ret_list.append(data[0])

        print(ret_list)

        all_OK = 0
        all_NG = 0
        all_total = 0
        for it in ret_list:
            OK_num = int(it['good'])
            NG_num = int(it['ng'])
            total = int(it['total'])
            if not total == 0:
                rate = '{:.2%}'.format(OK_num/total)
            else:
                rate = "0%"
            it['rate'] = rate
            if all_sta:
                all_OK += OK_num
                all_NG += NG_num
                all_total += total

        # if all_sta and not all_total == 0:
        #     rate = '{:.2%}'.format(all_OK/all_total)
        #     line_list = {'station_no': '全线', 'total': all_total, 'good': all_OK, 'ng': all_NG, 'rate': rate}
        #     ret_list.insert(0,line_list)

        meta = {
            "msg": "获取成功!",
            "result": "OK"
        }
        backdata = {
            "data": ret_list,
            "meta": meta,
        }

        print(backdata)
        # print(SQL)
        return HttpResponse(List_Json(backdata))

    except Exception as err:
        print(err)
        meta = {
            "msg": str(err),
            "result": "NG"
        }
        backdata = {
            "data": [],
            "meta": meta,
        }
        print(backdata)
        return HttpResponse(List_Json(backdata))

def SaveProinfo(stnum,codename,codevalue):
    try:
        log.info(">>>>>>SaveProinfo")
        if codevalue == "" or codevalue is None:
            log.info("codevalue为空，跳过保存")
            return
        main_code_name = ['qr_code1', 'qr_code2', 'pcba_code1', 'pcba_code2','lens','stand_code']
        column_name = ['qr_code1', 'qr_code2', 'pcba_code1', 'pcba_code2','stand_code', 'station_no', 'test_result', 'gp_model',
                       'judge_code', 'start_time', 'end_time']
        column_name_useless = ['id']
        json_data = {}
        json_testdata = {}
        SQL = "SELECT * FROM ST" + stnum + "_test_tab WHERE " + codename + " = '" + codevalue + "'"
        data = SQL_function3(SQL)

        if not len(data) == 0:
            for it in data:
                for key in it:
                    if key in column_name:
                        json_data[key] = it[key]
                    else:
                        if key in column_name_useless:
                            continue
                        json_testdata[key] = it[key]
        json_data['test_data'] = json_testdata

        # 补充该码的绑定码
        SQL = "SELECT * FROM ordersn_tab WHERE " + codename + " = '" + codevalue + "'"
        data = SQL_function3(SQL)
        if not len(data) == 0:
            for key in data[0]:
                if key in main_code_name:
                    json_data[key] = data[0][key]
        # 补充其他信息
        SQL = "SELECT * FROM qr_confrimation_tab WHERE " + codename + " = '" + codevalue + "' and station_no = 'ST" + stnum + "'"
        data1 = SQL_function3(SQL)
        json_data['site_name'] = data1[0]['site_name']
        json_data['equipment_num'] = data1[0]['station_no']
        json_data['equipment_name'] = ""
        json_data['part_no'] = data1[0]['part_no']
        json_data['part_batch'] = data1[0]['part_batch']
        if json_data['start_time'] == "" or json_data['end_time'] == "":
            json_data['run_time'] = "0"
        else:
            json_data['run_time'] = (datetime.datetime.strptime(json_data['start_time'],'%Y-%m-%d %H:%M:%S') - datetime.datetime.strptime(json_data['end_time'], '%Y-%m-%d %H:%M:%S')).seconds

        insert_key = ""
        insert_values = ""
        for key in json_data:
            insert_key += key + ","
            insert_values += "\"" + str(json_data[key]) + "\","
        insert_key = insert_key[:-1]
        insert_values = insert_values[:-1]
        SQL = "INSERT INTO st_history_test_tab (" + insert_key + ") Values (" + insert_values + ")"
        if not SQL_function4(SQL):
            raise Exception("插入历史数据失败")

    except Exception as err:
        log.info("--------SaveProinfo ERROR " + str(err))
        raise Exception(str(err))


@csrf_exempt
def DeleteProInfo(request):
    log.info("--------------手动重投")
    # [修复] 防重复点击机制：使用产品ID生成唯一锁key，避免多点导致并发问题
    qr_code1 = request.GET.get('qr_code1', '')
    qr_code2 = request.GET.get('qr_code2', '')
    pcba_code1 = request.GET.get('pcba_code1', '')
    pcba_code2 = request.GET.get('pcba_code2', '')
    station_no = request.GET.get('station_no', '')
    lock_key = f"retest_lock:{pcba_code1}:{pcba_code2}"
    lock_value = cache.get(lock_key)
    if lock_value:
        meta = {"msg": "产品正在处理中，请勿重复点击重投", "result": "NG"}
        backdata = {"data": {}, "meta": meta}
        return HttpResponse(List_Json(backdata))
    cache.set(lock_key, "1", timeout=300)
    try:
        # 原有业务逻辑
        log.info("--------------qr_code1:" + qr_code1)
        log.info("--------------qr_code2:" + qr_code2)
        log.info("--------------pcba_code1:" + pcba_code1)
        log.info("--------------pcba_code2:" + pcba_code2)
        print(station_no)
        print(qr_code1)
        print(qr_code2)
        print(pcba_code1)
        print(pcba_code2)
        log.info("--------------qr_code1:" + qr_code1)
        log.info("--------------qr_code2:" + qr_code2)
        log.info("--------------pcba_code1:" + pcba_code1)
        log.info("--------------pcba_code2:" + pcba_code2)


        # current_model = cache.get("current_model")
        # SQL = "SELECT * FROM station_bind_tab WHERE gp_model = '" + current_model + "'"
        # print(SQL)
        # data = easy_sql_reader(SQL)
        # print(data)
        # if len(data) == 0:
        #     msg = "解绑失败，没有找到当前型号"+ current_model +"的站点绑定表"
        #     print(msg)
        #     raise Exception(msg)
        # station_bind = json.loads(data[0]['station_bind'].replace("'", "\""))

        # SQL = "SELECT * FROM ordersn_tab WHERE qr_code1 = '" + qr_code1 + "'AND qr_code2 = '" + qr_code2 + "'AND pcba_code1 = '" + pcba_code1 + "'AND pcba_code2 = '" + pcba_code2 + "'"
        #重投不检查qr_code2
        SQL = "SELECT * FROM ordersn_tab WHERE qr_code1 = '" + qr_code1 + "'AND pcba_code1 = '" + pcba_code1 + "'AND pcba_code2 = '" + pcba_code2 + "'"

        print(SQL)
        data = SQL_function3(SQL)
        print(data)
        if len(data) == 0:
            msg = "未找到绑定信息"
            raise Exception(msg)
        elif len(data) > 1:
            msg = "找到多个绑定信息"
            raise Exception(msg)

        # 手动重投次数限制检查
        # retest_num字段保存在ordersn_tab表中
        # AA及AA前的站点(ST01-ST04)：最多2次
        # 气密(ST09)、EOL(ST10/ST11)、标定(ST12)：最多3次
        # 其他工站默认最多2次
        num = int(data[0]['retest_num'])
        current_station = data[0]['current_station']
        stand_code = data[0].get('stand_code') or ""
        limit_dict = {
            'ST01': 2, 'ST02': 2, 'ST03': 2, 'ST04': 2,  # AA及前工站
            'ST09': 3,  # 气密
            'ST10': 3, 'ST11': 3,  # EOL
            'ST12': 3,  # 标定
        }
        retest_limit = limit_dict.get(current_station, 2)
        if num >= retest_limit:
            msg = f"该产品已重投{num}次，不允许再次重投(当前工站{current_station}最多重投{retest_limit}次)"
            raise Exception(msg)

        SQL_Model = "SELECT gp_model from qr_confrimation_tab WHERE qr_code1 = '" + qr_code1 + "'AND pcba_code1 = '" + pcba_code1 + "'AND pcba_code2 = '" + pcba_code2 + "'"
        data_model = SQL_function3(SQL_Model)
        if len(data_model) == 0:
            msg = "未在qr_confrimation_tab中找到对应数据"
            raise Exception(msg)
        code_model = data_model[0]['gp_model']

        SQL_Bind = "SELECT * FROM station_bind_tab WHERE gp_model = '" + code_model + "'"
        data_bind = SQL_function3(SQL_Bind)
        if len(data_bind) == 0:
            msg = "解绑失败，没有找到当前型号" + code_model + "的站点绑定表"
            print(msg)
            raise Exception(msg)
        station_bind = json.loads(data_bind[0]['station_bind'].replace("'", "\""))

        # 对SP机台特殊处理（目前只考虑线外单台的支架锁附）
        # SQL_function3/4 会自行关闭连接并抛异常，不适合包在 transaction.atomic() 中。
        if True:
            if "SP" in station_no:
                SQL = "SELECT * FROM qr_confrimation_tab_sp WHERE qr_code1 = '" + qr_code1 + "'AND pcba_code1 = '" + pcba_code1 + "'AND pcba_code2 = '" + pcba_code2 + "'"
                data = SQL_function3(SQL)
                if len(data) == 0:
                    msg = "未在qr_confrimation_tab_sp中找到对应数据"
                    raise Exception(msg)
                stand_code = data[0]['stand_code']
                # 删除qr_confrimation_tab_sp中的数据 # 删除SP_test_tab中的数据
                bind_tab_name_sp = ['qr_confrimation_tab_sp', station_no.lower() + "_test_tab"]
                for it in bind_tab_name_sp:
                    # SQL = "DELETE FROM " + it + " WHERE qr_code1 = '" + qr_code1 + "'AND qr_code2 = '" + qr_code2 + "'AND pcba_code1 = '" + pcba_code1 + "'AND pcba_code2 = '" + pcba_code2 + "'"
                    #重投不查qr_code2
                    SQL = "DELETE FROM " + it + " WHERE qr_code1 = '" + qr_code1 + "'AND pcba_code1 = '" + pcba_code1 + "'AND pcba_code2 = '" + pcba_code2 + "'"
                    if not SQL_function4(SQL):
                        msg = "删除" + it + "中的信息失败"
                        raise Exception(msg)


            # 解绑线体上保存的支架绑定信息
            bind_tab_name = ['qr_bind_tab', 'qr_confrimation_tab', 'ordersn_tab']
            if not stand_code == "":
                for it in bind_tab_name:
                    SQL = "UPDATE " + it + " SET stand_code = '' WHERE stand_code = '" + stand_code + "'"
                    if not SQL_function4(SQL):
                        msg = "删除" + it + "中的信息失败"
                        raise Exception(msg)
            else:
                SQL = "SELECT * FROM qr_confrimation_tab_sp WHERE qr_code1 = '" + qr_code1 + "'AND pcba_code1 = '" + pcba_code1 + "'AND pcba_code2 = '" + pcba_code2 + "'"

                sp_data = SQL_function3(SQL)
                if not len(sp_data) == 0:
                    msg = "找到对应支架绑定数据，请先解绑支架"
                    raise Exception(msg)

                from_stno = data[0]['current_station']
                to_station = station_no
                s_no = int(from_stno.replace('ST', '')) + 1
                d_no = int(to_station.replace('ST', ''))
                if s_no < d_no:
                    msg = "起始站点错误，只能向前站解绑跳站"

                # 跳站
                myip = Getmyip()
                url = 'http://' + str(myip) + ':9000/api/Jump/ToStation'
                print(url)
                d_no_temp = d_no - 1
                stno = ""
                if d_no_temp < 10:
                    stno = "ST0" + str(d_no_temp)
                else:
                    stno = "ST" + str(d_no_temp)
                params = {'from_stno': from_stno, 'to_stno': stno, 'qr_code1': qr_code1,
                        'qr_code2': qr_code2, 'pcba_code1': pcba_code1, 'pcba_code2': pcba_code2, 'lens': '',
                        'Starttime': "", 'Endtime': ""}
                print(params)
                response = requests.get(url=url, params=params)
                ret_data = json.loads(response.text)
                print(ret_data)
                # 解绑
                bind_name = ""
                for i in range(d_no, s_no):
                    print(i)
                    if i < 10:
                        stno = "ST0" + str(i)
                    else:
                        stno = "ST" + str(i)
                    for key in station_bind:
                        if key == stno:
                            if not bind_name == "":
                                bind_name = bind_name + ","
                            bind_name = bind_name + station_bind[key] + "= ''"

                print(bind_name)

                bind_tab_name = ['qr_bind_tab', 'qr_confrimation_tab', 'ordersn_tab']
                temp_sql = " WHERE qr_code1 = '" + qr_code1 + "'AND qr_code2 = '" + qr_code2 + "'AND pcba_code1 = '" + pcba_code1 + "'AND pcba_code2 = '" + pcba_code2 + "'"
                if not bind_name == "":
                    for it1 in bind_tab_name:
                        SQL = "UPDATE " + it1 + " SET " + bind_name + temp_sql
                        print(SQL)
                        if not SQL_function4(SQL):
                            raise Exception('SQL执行失败！')

        # 重投成功后更新重投次数
        SQL = "UPDATE ordersn_tab SET retest_num = '" + str(num + 1) + "' WHERE qr_code1 = '" + qr_code1 + "' AND pcba_code1 = '" + pcba_code1 + "' AND pcba_code2 = '" + pcba_code2 + "'"
        print(SQL)
        if not SQL_function4(SQL):
            raise Exception('更新重投次数失败！')

        meta = {
            "msg": "删除成功!",
            "result": "OK"
        }
        backdata = {
            "data": {},
            "meta": meta,
        }

        return HttpResponse(List_Json(backdata))

    except Exception as err:
        cache.delete(lock_key)
        print(err)
        Data = {}
        meta = {"msg": str(err), "result": "NG"}
        backdata = {"data": Data, "meta": meta}
        print(backdata)
        return HttpResponse(List_Json(backdata))
# 手动绑定按钮  当前功能为只能对当前工单的产品进行绑定信息的修改，在绑定开始会对码进行工单的物料号对比
def Bind_manual_btn(request):
    # flag 前壳码1 qr_code1、后壳码2 qr_code2、3 pcba_1、4  pcba_2、5 镜头lens、6 stand
    try:
        log.info(">>>>>>Bind_manual_btn")
        main_code = request.GET.get('main_code', '')
        main_code_flag = request.GET.get('main_code_flag', '')
        bind_code = request.GET.get('bind_code', '')
        bind_code_flag = request.GET.get('bind_code_flag', '')
        current_model = cache.get("current_model")
        st_current_model = ""
        current_model_sp = cache.get("current_model_sp")
        device_class_sp = cache.get('DeviceClass_SP')
        current_order = cache.get('current_order')
        current_order_stand = cache.get('current_order_stand')
        retdata = {}
        t = datetime.datetime.now()

        # SQL =
        # 根据station_bind_tab 转化为对应站点STNO的绑定
        STNO = device_class_sp[0]['EquipNumber']

        # flag 1 前壳码1 qr_code1、2 后壳码2 qr_code2、3 pcba_1、4  pcba_2、5 镜头lens、6 stand支架
        # type 0前壳qrcode1     1  pcba1        2后壳qrcode2    3 pcba2   4 料盘码

        # 临时优化 对当前主副码进行型号匹配
        main_code_model = ""
        bind_code_model = ""
        flag_tag_dict = {"1":"qr_code1", "2":"qr_code2", "3":"pcba_code1", "4":"pcba_code2", "5":"lens", "6":"stand_code"}
        part_no_dict = {"pcba_code1":"P_PART_NO", "lens":"J_PART_NO", "stand_code":"ZC_PART_NO"}

        SQL = "SELECT * FROM qr_confrimation_tab WHERE " + flag_tag_dict[main_code_flag] + " = '" + main_code + "'"
        data = SQL_function3(SQL)
        if len(data) == 0:
            msg = "不存在该主码生产信息"
            raise Exception(msg)
        main_code_model = data[0]['gp_model']

        SQL = "SELECT * FROM planorder_partno_tab WHERE gp_model = '" + main_code_model + "'"
        data = SQL_function3(SQL)
        partno_code = data[0][part_no_dict[flag_tag_dict[bind_code_flag]]]
        if partno_code == "":
            msg = main_code_model + " 对应绑定物料号为空,请维护"
            raise Exception(msg)
        index = bind_code.find(partno_code)
        if index == -1:
            raise Exception("绑定码与主码物料型号不一致")

        # 前端传来的flag码转为机台协议中的type码
        Type = ""
        match main_code_flag:
            case "1":
                Type = "0"
            case "2":
                Type = "2"
            case "3":
                Type = "1"
            case "4":
                Type = "3"

        msg2mes_0x02 = {
            "Command": "0x02",
            "Check":
                {
                    "Serial_No": main_code,
                    "Type": Type,
                    "Station_No": STNO,
                    "Gp_Model": current_model_sp
                }
        }
        msg2mes_0x03 = {
            "Command": "0x03",
            "Bind":
                {
                    "Pcba1": "",
                    "Pcba2": "",
                    "Lens": "",
                    "Qr_code1": "",
                    "Qr_code2": "",
                    "Stand": "",
                    "Station_No": STNO,
                    "Gp_Model": current_model_sp
                }
        }
        msg2mes_0x04 = {
            "Command": "0x04",
            "DataUp":
                {
                    "Serial_No": main_code,
                    "Station_No": STNO,
                    "Site_Name": "",
                    "Type": Type,
                    "Test_Result": "OK",
                    "Gp_Model": current_model_sp,
                    "Judge_Code": [],
                    "Start_Time":  int(time.mktime(t.timetuple()))*1000,
                    "End_Time":  int(time.mktime(t.timetuple()))*1000,
                    "Test_Value": []
                }
        }

        # SP 0x02 请求   6为绑定支架码
        if bind_code_flag == "6":
            type = msg2mes_0x02['Check']['Type']
            if type == "0":
                code_name = "qr_code1"
            elif type == "1":
                code_name = "pcba_code1"
            elif type == "2":
                code_name = "qr_code2"
            elif type == "3":
                code_name = "pcba_code2"
            # 校验线体生产结果信息
            SQL = "SELECT * FROM ordersn_tab WHERE " + code_name + " = '" + main_code + "'"
            or_data = SQL_function(SQL)
            if not or_data[0]['result'] == "OK":
                msg = "该主码NG或未生产完成"
                raise Exception(msg)
            # 校验线体生产站点信息
            SQL = "SELECT * FROM qr_confrimation_tab WHERE " + code_name + " = '" + main_code + "'"
            sta_data = SQL_function3(SQL)
            gp_model = sta_data[0]['gp_model']
            SQL = "SELECT * FROM station_tab where gp_model = '" + gp_model + "'"
            model_data = SQL_function3(SQL)

            if len(sta_data) < len(model_data):
                msg = "该主码线体未生产完成，无法绑定支架"
                raise Exception(msg)

            print("lock2.acquire")
            log.info("lock2.acquire")
            lock2.acquire()
            retdata = TRecv_SP("", str(msg2mes_0x02), "Msg2Mes/")

            lock2.release()
            print("lock2.release")
            log.info("lock2.release")

            if retdata['Check_Result']['Result'] == "NG":
                raise Exception(retdata['Check_Result']['Message'])

        flag_list = []
        code_list = []
        name_list = []
        flag_list.append(main_code_flag)
        flag_list.append(bind_code_flag)
        code_list.append(main_code)
        code_list.append(bind_code)

        print(code_list)
        print(flag_list)

        if main_code_flag == bind_code_flag:
            raise Exception("绑定失败,绑定码和主码类型一致")
        # flag 前壳码1 qr_code1、后壳码2 qr_code2、3 pcba_1、4 pcba_2、5 镜头lens、6 stand
        for it1 in code_list:
            name = ""
            print("it1:")
            print(it1)
            for it2 in flag_list:
                print("it2:")
                print(it2)
                match it2:
                    case "1":
                        if msg2mes_0x03['Bind']['Qr_code1'] == "":
                            msg2mes_0x03['Bind']['Qr_code1'] = it1
                            name = "qr_code1"
                            break
                    case "2":
                        if msg2mes_0x03['Bind']['Qr_code2'] == "":
                            msg2mes_0x03['Bind']['Qr_code2'] = it1
                            name = "qr_code2"
                            break
                    case "3":
                        if msg2mes_0x03['Bind']['Pcba1'] == "":
                            msg2mes_0x03['Bind']['Pcba1'] = it1
                            name = "pcba_code1"
                            break
                    case "4":
                        if msg2mes_0x03['Bind']['Pcba2'] == "":
                            msg2mes_0x03['Bind']['Pcba2'] = it1
                            name = "pcba_code2"
                            break
                    case "5":
                        if msg2mes_0x03['Bind']['Lens'] == "":
                            msg2mes_0x03['Bind']['Lens'] = it1
                            name = "lens"
                            break
                    case "6":
                        if msg2mes_0x03['Bind']['Stand'] == "":
                            msg2mes_0x03['Bind']['Stand'] = it1
                            name = "stand_code"
                            break
            name_list.append(name)
        print(msg2mes_0x03)

        # flag 1 前壳码1 qr_code1、2 后壳码2 qr_code2、3 pcba_1、4  pcba_2、5 镜头lens、6 stand
        if bind_code_flag == "6" and not main_code_flag == "6":
            print("lock2.acquire")
            log.info("lock2.acquire")
            lock2.acquire()
            # 如果是绑定支架
            retdata = TRecv_SP("", str(msg2mes_0x03), "Msg2Mes/")

            lock2.release()
            print("lock2.release")
            log.info("lock2.release")

        else:
            # print("lock2.acquire")
            # log.info("lock2.acquire")
            # lock2.acquire()
            #
            # retdata = TRecv_SP("", str(msg2mes_0x03), "Msg2Mes/")
            #
            # lock2.release()
            # print("lock2.release")
            # log.info("lock2.release")
            if not code_list[1] or code_list[1].strip() == "":
                raise Exception("绑定码不能为空")
            SQL = "SELECT * FROM qr_bind_tab WHERE " + name_list[1] + " = '" + code_list[1] + "'"
            data = SQL_function3(SQL)
            if not len(data) == 0:
                msg = "存在相同绑定码的绑定"
                raise Exception(msg)

            if not code_list[0] or code_list[0].strip() == "":
                raise Exception("主码不能为空")
            SQL = "SELECT * FROM qr_bind_tab WHERE " + name_list[0] + " = '" + code_list[0] + "'"
            data = SQL_function3(SQL)
            if len(data) == 0:
                msg = "未找到该主码信息"
                raise Exception(msg)
            bind_tab_name = ['qr_bind_tab','qr_confrimation_tab']
            for it in bind_tab_name:
                SQL = "UPDATE " + it + " SET " + name_list[1] + " = '" + code_list[1] + "' WHERE " + name_list[
                    0] + " = '" + code_list[0] + "'"
                if not SQL_function4(SQL):
                    msg = "绑定失败"
                    raise Exception(msg)
                retdata = {"Bind_Result":{"Result":"OK"}}

        # 返回判断
        if retdata['Bind_Result']['Result'] == "NG":
            raise Exception(retdata['Bind_Result']['Message'])
        # 更新sp真实型号
        if bind_code_flag == '6':
            SQL = "Update qr_confrimation_tab_sp set gp_model = '" + main_code_model + "' WHERE " + flag_tag_dict[
                main_code_flag] + " = '" + main_code + "'"
            if not SQL_function4(SQL):
                msg = "型号保存失败"
                raise Exception(msg)

        # 上传绑定测试数据，同步绑定至MOM
        if bind_code_flag == "6":
            print("lock2.acquire")
            log.info("lock2.acquire")
            lock2.acquire()

            retdata = TRecv_SP("", str(msg2mes_0x04), "Msg2Mes/")

            lock2.release()
            print("lock2.release")
            log.info("lock2.release")

            if retdata['DataUp_Result']['Result'] == "NG":
                raise Exception(retdata['DataUp_Result']['Message'])

        # 返回
        SQL = "SELECT * FROM qr_bind_tab WHERE " + name_list[0] + " = '" + code_list[0] + "' AND " + name_list[1] + " = '" + code_list[1] + "'"
        print(SQL)
        data = easy_sql_reader(SQL)
        print(data)
        if len(data) == 0:
            raise Exception("绑定查询失败")
        Data = {
            "qr_code1": data[0]['qr_code1'],
            "qr_code2": data[0]['qr_code2'],
            "pcba_code1": data[0]['pcba_code1'],
            "pcba_code2": data[0]['pcba_code2'],
            "lens": data[0]['lens'],
            "stand_code": data[0]['stand_code']
        },
        meta = {
            "msg": "绑定成功",
            "result": "OK"
        }
        backdata = {
            "data": Data,
            "meta": meta,
        }
        print(backdata)
        return HttpResponse(List_Json(backdata))
    except Exception as err:
        if lock2.acquire():
            lock2.release()
            print("lock2.release")
            log.info("lock2.release")

        print(str(err))
        log.info(str(err))
        Data = {}
        meta = {
            "msg": str(err),
            "result": "NG"
        }

        backdata = {
            "data": Data,
            "meta": meta,
        }
        print(backdata)
        return HttpResponse(List_Json(backdata))

    # -------------------------------------手动过站-----------------------------------------

# ---------------获取产线上当前工单所有生产的产品信息--------------
def GetOnline(request):
    try:
        Starttime = request.GET.get('Starttime', '')
        Endtime = request.GET.get('Endtime', '')

        print(Starttime)
        print(Endtime)
        if Starttime == "" or Endtime == "":
            Starttime = request.POST.get('Starttime', '')
            Endtime = request.POST.get('Endtime', '')
            if Starttime == "" or Endtime == "":
                raise Exception("查询时间为空")
        current_order = cache.get('current_order')
        SQL = "SELECT * FROM ordersn_tab WHERE order_no = '" + current_order + "' AND online_time BETWEEN '" + Starttime + "' AND '" + Endtime + "'"
        print(SQL)
        back_data = sql_list(SQL)
        print(back_data)
        meta = {
            "msg": "",
            "result": "OK"
        }
        data = []
        for it in back_data:
            print(it)
            data_temp = {
            "order_no": it[0],
            "qr_code1": it[1],
            "qr_code2": it[2],
            "pcba_code1": it[3],
            "pcba_code2": it[4],
            "lens": it[5],
            "stand_code": it[12],
            "online_time": str(it[6]),
            "offline_time": str(it[7]),
            "laststation_time": str(it[8]),
            "current_station": it[11]
            }
            data.append(data_temp)

        backdata = {
            "data": data,
            "meta": meta,
        }
    except Exception as err:
        print(err)
        meta = {
            "msg": str(err),
            "result": "NG"
        }
        data = {}
        backdata = {
            "data": data,
            "meta": meta,
        }
    return HttpResponse(List_Json(backdata))
# ---------------手动过站，将产品跳到目标站点---------------
def ToStation(request):
    log.info("-----------------------ToStation过站")
    try:
        current_model = cache.get('current_model')
        equipnumgroup = cache.get('EquipNumGroup')
        t = datetime.datetime.now()

        from_stno = request.GET.get('from_stno', '')
        to_stno = request.GET.get('to_stno', '')
        qr_code1 = request.GET.get('qr_code1', '')
        qr_code2 = request.GET.get('qr_code2', '')
        pcba_code1 = request.GET.get('pcba_code1', '')
        pcba_code2 = request.GET.get('pcba_code2', '')
        lens = request.GET.get('lens', '')
        # 查看当前生产型号
        SQL = "SELECT * FROM qr_confrimation_tab WHERE qr_code1 = '" + qr_code1 + "' and qr_code2 = '" + qr_code2 + \
              "' and pcba_code1 = '" + pcba_code1 + "' and pcba_code2 = '" + pcba_code2 + "'"
        model_data = SQL_function3(SQL)
        current_model = model_data[0]['gp_model']
        # 查看当前sn号是否为NG件，如果是，清除NG信息再跳
        SQL = "SELECT * FROM ordersn_tab WHERE qr_code1 = '" + qr_code1 + "' and qr_code2 = '" + qr_code2 + \
                  "' and pcba_code1 = '" + pcba_code1 + "' and pcba_code2 = '" + pcba_code2 + "'"
        print(SQL)
        # back_data = sql_list(SQL)
        back_data = SQL_function3(SQL)
        print(back_data)
        if back_data[0]['result'] == "NG":
            SQL = "DELETE FROM product_statistics_tab WHERE qr_code1 = '" + qr_code1 + "' and qr_code2 = '" + qr_code2 + \
                  "' and pcba_code1 = '" + pcba_code1 + "' and pcba_code2 = '" + pcba_code2 + "'"
            if not SQL_function4(SQL):
                raise Exception('product_statistics_tab NG数据删除失败！')

        s_no = int(from_stno.replace('ST', '')) + 1
        d_no = int(to_stno.replace('ST', '')) + 1
        log.info("s_no:" + str(s_no))
        log.info("d_no:" + str(d_no))

        # 产品往后(下料方向)跳
        if s_no <= d_no:
            print("产品往后跳")
            SQL = "UPDATE qr_confrimation_tab SET test_result = 'OK',check_result = 'OK',test_time = '" + str(t) + "' WHERE qr_code1 = '" + qr_code1 + "' and qr_code2 = '" + qr_code2 + \
                  "' and pcba_code1 = '" + pcba_code1 + "' and pcba_code2 = '" + pcba_code2 + "' and station_no = '" + from_stno + "'"
            print(SQL)
            if not SQL_function4(SQL):
                raise Exception('SQL执行失败！')
            # 向后跳时生成跳站的过站数据
            for i in range(s_no, d_no):
                print(i)
                if i < 10:
                    stnum = '0' + str(i)
                else:
                    stnum = str(i)
                SQL = "SELECT st_current_model FROM station_tab WHERE gp_model = '" + current_model + "' and equipment_num = 'ST" + stnum + "'"
                stmodel_data = SQL_function3(SQL)
                if len(stmodel_data) == 0:
                    st_current_model = current_model
                    continue
                elif stmodel_data[0]['st_current_model'] == "":
                    st_current_model = current_model
                else:
                    st_current_model = stmodel_data[0]['st_current_model']
                SQL = "INSERT INTO qr_confrimation_tab (pcba_code1,pcba_code2,qr_code1,qr_code2,lens,check_result,test_result,gp_model,station_no,check_time,test_time) VALUES ('" + pcba_code1 + \
                      "','" + pcba_code2 + "','" + qr_code1 + "','" + qr_code2 + "','" + lens + "','OK','OK','" + st_current_model + "','ST" + stnum + "','" + str(t) + "','" + str(t) + "')"
                print(SQL)
                if not SQL_function4(SQL):
                    raise Exception('SQL执行失败！')

        # 产品往前(上料方向)跳
        elif s_no > d_no:
            print("产品往前跳")
            # 向前跳时候删除站位信息 和 数据信息
            for i in range(d_no, s_no):
                print(i)
                if i < 10:
                    stnum = '0' + str(i)
                else:
                    stnum = str(i)
                # SQL = "DELETE FROM qr_confrimation_tab WHERE qr_code1 = '" + qr_code1 + "' and qr_code2 = '" + qr_code2 + \
                #   "' and pcba_code1 = '" + pcba_code1 + "' and pcba_code2 = '" + pcba_code2 + "' and station_no = 'ST" + stnum + "'"
                # print(SQL)
                # if not SQL_function4(SQL):
                #     raise Exception('SQL执行失败！')

                name_list = ['qr_code1','qr_code2','pcba_code1','pcba_code2']
                value_list = [qr_code1,qr_code2,pcba_code1,pcba_code2]
                for num in range(0,len(name_list)):
                    if not value_list[num] == "":
                        SQL = "SELECT * FROM ST" + stnum + "_test_tab WHERE " + name_list[num] + " = '" + value_list[
                            num] + "'"
                        data = SQL_function3(SQL)
                        if not len(data) == 0:
                            # 存储历史测试数据
                            SaveProinfo(stnum,name_list[num],value_list[num])

                            SQL = "DELETE FROM ST" + stnum + "_test_tab WHERE " + name_list[num] + " = '" + value_list[
                                num] + "'"
                            if not SQL_function4(SQL):
                                raise Exception('SQL执行失败！')

                SQL = "DELETE FROM qr_confrimation_tab WHERE qr_code1 = '" + qr_code1 + "' and qr_code2 = '" + qr_code2 + \
                      "' and pcba_code1 = '" + pcba_code1 + "' and pcba_code2 = '" + pcba_code2 + "' and station_no = 'ST" + stnum + "'"
                print(SQL)
                if not SQL_function4(SQL):
                    raise Exception('SQL执行失败！')


        print(to_stno)
        print(d_no)
        # 更新ordersn 中的对应站点信息
        if to_stno == "ST00":
            SQL = "DELETE FROM ordersn_tab WHERE qr_code1 = '" + qr_code1  + "' and qr_code2 = '" + qr_code2 + \
              "' and pcba_code1 = '" + pcba_code1 + "' and pcba_code2 = '" + pcba_code2 + "'"
            SQL_function4(SQL)
            SQL = "DELETE FROM qr_bind_tab WHERE qr_code1 = '" + qr_code1 + "' and qr_code2 = '" + qr_code2 + \
                  "' and pcba_code1 = '" + pcba_code1 + "' and pcba_code2 = '" + pcba_code2 + "'"
            SQL_function4(SQL)

        order_result = ""
        if to_stno == equipnumgroup[len(equipnumgroup) - 1]:
            order_result = "OK"

        SQL = "UPDATE ordersn_tab SET current_station = '" + to_stno + "',result = '" + order_result + "',retest_num = '0'  WHERE qr_code1 = '" + qr_code1 + "' and qr_code2 = '" + qr_code2 + \
              "' and pcba_code1 = '" + pcba_code1 + "' and pcba_code2 = '" + pcba_code2 + "' and current_station = '" + from_stno + "'"
        SQL_function4(SQL)

        # [修复] eval() 替换为 json.loads()，避免安全问题（eval可执行任意Python代码）
        back_data = json.loads(GetOnline(request).content)
        back_data['meta']['msg'] = from_stno + " ---> " + to_stno + "跳站成功"
        back_data['meta']['result'] = "OK"

    except Exception as err:
        print(err)
        # [修复] eval() 替换为 json.loads()，避免安全问题
        back_data = json.loads(GetOnline(request).content)
        back_data['meta']['result'] = "NG"
    return HttpResponse(List_Json(back_data))

# -----------------NG重测------------------------
def Get_retestmsg(request):
    print("-----------------------Get_retestmsg")
    Start_stno = ""
    End_stno = ""
    try:
        Starttime = request.GET.get('Starttime', '')
        Endtime = request.GET.get('Endtime', '')
        Ordernum = request.GET.get('Ordernum', '')

        filepath = GetFilePath("SoftWare.ini")
        conf = ConfigParser()  # 需要实例化一个ConfigParser对象
        conf.read(filepath)  # 需要添加上config.ini的路径，不需要open打开，直接给文件路径就读取，也可以指定encoding='utf-8'
        retest_station = conf['CommonUse']['retest_station']
        retest_station = retest_station.replace("'","\"")
        retest_station = json.loads(retest_station)

        Start_stno = str(retest_station['start_stno'])
        End_stno = retest_station['end_stno']
        Start_num = int(Start_stno.replace('ST', ''))
        End_num = int(End_stno.replace('ST', ''))
        current_order = cache.get('current_order')

        if Ordernum == "":
            Ordernum = current_order

        stno_list = []
        for i in range(Start_num, End_num + 1):
            st_num = "ST"
            if i < 10:
                st_num = st_num + "0"
                st_num = st_num + str(i)
            else:
                st_num = st_num + str(i)

            stno_list.append(st_num)

        SQL = "SELECT * FROM ordersn_tab WHERE result = 'NG' AND order_no = '" + Ordernum + "' AND (current_station = "
        for i in range(0, len(stno_list)):
            SQL = SQL + "'" + stno_list[i] + "'"
            print(i)
            if not i == len(stno_list) - 1:
                SQL = SQL + " OR current_station = "
        SQL = SQL + ")"
        if Starttime == "" or Endtime == "":
            print('时间为空')
        else:
            SQL = SQL + " AND online_time BETWEEN '" + Starttime + "' AND '" + Endtime + "'"
        print(SQL)
        # back_data = sql_list(SQL)
        back_data = easy_sql_reader(SQL)
        print(back_data)
        print(type(back_data))
        print(len(back_data))

        SQL = "SELECT * FROM planorder_tab"
        print(SQL)
        order_back_data = easy_sql_reader(SQL)
        print(order_back_data)
        Ordernum_list = []
        for it in order_back_data:
            Ordernum_list.append(it['order_no'])
        Data = {
            "Ordernum": Ordernum,
            "Ordernum_list": Ordernum_list,
            "NG_data": back_data
        }
        Setting = {
            "Start_stno": Start_stno,
            "End_stno": End_stno
        }
        Meta = {
            "msg": "查询成功",
            "result": "OK"
        }
        backdata = {
            "Data": Data,
            "meta": Meta,
            "Setting": Setting,
        }
        print(backdata)
    except Exception as err:
        print(err)
        Data = []
        Meta = {
            "msg": str(err),
            "result": "NG"
        }
        Setting = {
            "Start_stno": Start_stno,
            "End_stno": End_stno
        }
        backdata = {
            "Data": Data,
            "meta": Meta,
            "Setting": Setting,
        }
    return HttpResponse(List_Json(backdata))
def retest_setting(request):
    print("-----------------------retest_setting")
    try:
        start_stno = request.GET.get('start_stno', '')
        end_stno = request.GET.get('end_stno', '')
        if start_stno == "" or end_stno == "":
            raise Exception("工位号为空")
        retest_station = {"start_stno": start_stno, "end_stno": end_stno}
        # 修改本地文件中的站点信息
        filepath = GetFilePath("SoftWare.ini")
        conf = ConfigParser()  # 需要实例化一个ConfigParser对象
        conf.read(filepath)  # 需要添加上config.ini的路径，不需要open打开，直接给文件路径就读取，也可以指定encoding='utf-8'
        print(conf['CommonUse']['retest_station'])
        conf.set('CommonUse', 'retest_station', str(retest_station))
        with open(filepath, 'w', encoding='utf-8') as f:
            conf.write(f)
        print(conf['CommonUse']['retest_station'])
        meta = {
            "msg": "站位修改成功!",
            "result": "OK"
        }
        backdata = {
            "data": "",
            "meta": meta,
            "setting": {"start_stno":start_stno,"end_stno":end_stno}
        }
    except Exception as err:
        print(err)
        meta = {
            "msg": err,
            "result": "NG"
        }
        backdata = {
            "data": "",
            "meta": meta,
            "setting": {}
        }
    return HttpResponse(List_Json(backdata))
def retest(request):
    # NG重测按钮，将该产品跳到重测区间起始站，删除测试记录和测试信息，将ordersn_tab中对应该型号的retest_num 自增 1
    print("-----------------------retest")
    result = "NG"
    msg = ""
    try:
        print(request.GET)
        qr_code1 = request.GET.get('qr_code1', '')
        qr_code2 = request.GET.get('qr_code2', '')
        pcba_code1 = request.GET.get('pcba_code1', '')
        pcba_code2 = request.GET.get('pcba_code2', '')
        Starttime = request.GET.get('Starttime', '')
        Endtime = request.GET.get('Endtime', '')

        filepath = GetFilePath("SoftWare.ini")
        conf = ConfigParser()  # 需要实例化一个ConfigParser对象
        conf.read(filepath)  # 需要添加上config.ini的路径，不需要open打开，直接给文件路径就读取，也可以指定encoding='utf-8'
        retest_station = conf['CommonUse']['retest_station']
        retest_station = retest_station.replace("'", "\"")
        retest_station = json.loads(retest_station)
        myip = conf['CommonUse']['myip']

        Start_stno = str(retest_station['start_stno'])
        print("startstaion:"+Start_stno)
        SQL = "SELECT * FROM ordersn_tab WHERE qr_code1 = '" + qr_code1 + "' and qr_code2 = '" + qr_code2 + \
                  "' and pcba_code1 = '" + pcba_code1 + "' and pcba_code2 = '" + pcba_code2 + "'"
        print(SQL)
        back_data = easy_sql_reader(SQL)
        print(back_data)

        num = int(back_data[0]['retest_num'])
        if num == 2:
            msg = "已经NG三次不允许重测"
            raise Exception(msg)
        elif num < 2:
            url = 'http://' + str(myip) + ':9000/api/Jump/ToStation'
            print(url)
            params = {'from_stno': back_data[0]['current_station'], 'to_stno': Start_stno, 'qr_code1': qr_code1,
                      'qr_code2': qr_code2, 'pcba_code1': pcba_code1, 'pcba_code2': pcba_code2, 'lens': '',
                      'Starttime': Starttime, 'Endtime': Endtime}
            print(params)
            response = requests.get(url=url, params=params)
            ret_data = json.loads(response.text)
            # 更新重测次数记录
            # 删除product_statistics_tab中的 NG信息
            if ret_data['meta']['result'].upper() == "OK":
                num = num + 1
                SQL = "UPDATE ordersn_tab SET retest_num = '" + str(num) + "',result = '' WHERE qr_code1 = '" + qr_code1 + "' and qr_code2 = '" + qr_code2 + \
                  "' and pcba_code1 = '" + pcba_code1 + "' and pcba_code2 = '" + pcba_code2 + "'"
                print(SQL)
                if not sql_execute(SQL):
                    raise Exception('SQL执行失败！')

                SQL = "DELETE FROM product_statistics_tab WHERE qr_code1 = '" + qr_code1 + "' and qr_code2 = '" + qr_code2 + \
                  "' and pcba_code1 = '" + pcba_code1 + "' and pcba_code2 = '" + pcba_code2 + "'"
                print(SQL)
                if not sql_execute(SQL):
                    raise Exception('SQL执行失败！')
                response_back = Get_retestmsg(request)
                ret_data = json.loads(response_back.content)
                print(ret_data)
                print(type(ret_data))
                ret_data['meta']['msg'] = "NG重测准备成功"
                return HttpResponse(List_Json(ret_data))
            else:
                raise Exception(ret_data['meta']['msg'])
    except Exception as err:
        print(err)
        response_back = Get_retestmsg(request)
        ret_data = json.loads(response_back.content)
        ret_data['meta']['msg'] = str(err)
        return HttpResponse(List_Json(ret_data))
# -------------------------------------工单管理--------------------------------------------

# -----------------手动添加工单--------------------
def Addorder(request):
    factory_code = request.POST.get('factory_code', '')
    order_no = request.POST.get('order_no', '')
    part_no = request.POST.get('part_no', '')                                           # 产品物料编码  这个自己生成
    soft_ver = ""                                           #软件本版本号
    num = request.POST.get('num', '')
    line_no = request.POST.get('line_no', '')
    shift_no = request.POST.get('shift_no', '')            #（0：白班，1：中班，2：晚班）
    gp_model = request.POST.get('gp_model', '')
    # 手动添加工单不获取版本号
    backdata=PlanOrderRecord(factory_code, order_no, part_no, soft_ver, num, line_no, shift_no, gp_model, 1)
    return HttpResponse(List_Json(backdata))

# ----------------------获取生产工单表----------------------------
def Getorder(request):
    try:
        gp_model = request.GET.get('gp_model', '')
        order_no = request.GET.get('order_no', '')
        start_time = request.GET.get('start_time', '')
        end_time = request.GET.get('end_time', '')

        pagenum = request.GET.get('pagenum', '')
        pagesize = request.GET.get('pagesize', '')

        print(pagenum)
        print(pagesize)
        print(order_no)
        print(gp_model)
        print(start_time)
        print(end_time)
        SQL = "SELECT * FROM planorder_tab"

        search_tag = False
        # 添加搜索条件  未完成 待补充
        if gp_model != "":
            if search_tag:
                SQL += " AND gp_model = '" + gp_model + "'"
            else:
                SQL += " WHERE gp_model = '" + gp_model + "'"
                search_tag = True
        if order_no != "":
            if search_tag:
                SQL += " AND order_no = '" + order_no + "'"
            else:
                SQL += " WHERE order_no = '" + order_no + "'"
                search_tag = True
        if start_time != "" and end_time != "":
            if search_tag:
                SQL += " AND datetime BETWEEN '"+start_time+"' AND '"+end_time+"'"
            else:
                SQL += " WHERE datetime BETWEEN '"+start_time+"' AND '"+end_time+"'"
                search_tag = True
        # start_time = request.GET.get('start_time', '')
        # end_time = request.GET.get('end_time', '')
        SQL += " ORDER BY online_time DESC"

        print(SQL)
        data = aview_easy_sql_reader_page1(SQL, pagenum, pagesize)
        print(data)
        meta = {
            "msg": "获取工单列表成功!",
            "result": "OK"
        }
        backdata = {
            "data": data,
            "meta": meta,
        }

        print(backdata)
        # print(SQL)
        return HttpResponse(List_Json(backdata))
    except Exception as err:
        print(err)
        meta = {
            "msg": "获取计划列表失败!",
            "result": "NG"
        }
        data = {}
        backdata = {
            "data": data,
            "meta": meta,
        }
        return HttpResponse(List_Json(backdata))
# ---------------------获取当前生产的工单------------------------
def GetCurrentorder(request):
    try:
        current_order = cache.get('current_order')

        SQL = "SELECT * FROM planorder_tab WHERE order_no = '" + current_order + "'"
        print(SQL)
        data = SQL_function3(SQL)
        print(data)
        if len(data) != 1:
            raise Exception("查找产品在当前工单" + current_plan + "失败")

        meta = {
            "msg": "获取工单成功!",
            "result": "OK"
        }
        data = {
            "order_no": data[0]['order_no'],
            "num": data[0]['num'],
            "num_real": data[0]['num_real'],
            "gp_model": data[0]['gp_model'],
            "datetime": str(data[0]['datetime']),
            "factory_code": data[0]['factory_code'],
            "soft_ver": data[0]['soft_ver'],
            "shift_no": data[0]['shift_no'],
            "line_no": data[0]['line_no'],
            "part_no": data[0]['part_no'],
            "status": data[0]['status'],
        }

        backdata = {
            "data": data,
            "meta": meta,
        }
        print(backdata)
    except Exception as err:
        print(err)
        meta = {
            "msg": err,
            "result": "NG"
        }
        data = {}
        backdata = {
            "data": data,
            "meta": meta,
        }
    return HttpResponse(List_Json(backdata))

def Addorder_stand(request):
    factory_code = request.POST.get('factory_code', '')
    order_no = request.POST.get('order_no', '')
    part_no = request.POST.get('part_no', '')                                           # 产品物料编码  这个自己生成
    soft_ver = ""                                           #软件本版本号
    num = request.POST.get('num', '')
    line_no = request.POST.get('line_no', '')
    shift_no = request.POST.get('shift_no', '')            #（0：白班，1：中班，2：晚班）
    gp_model = request.POST.get('gp_model', '')
    # 手动添加工单不获取版本号
    backdata=PlanOrderRecord_stand(factory_code, order_no, part_no, soft_ver, num, line_no, shift_no, gp_model, 1)
    return HttpResponse(List_Json(backdata))
# ----------------------获取生产工单表----------------------------
def Getorder_stand(request):
    try:
        gp_model = request.GET.get('gp_model', '')
        order_no = request.GET.get('order_no', '')
        start_time = request.GET.get('start_time', '')
        end_time = request.GET.get('end_time', '')

        pagenum = request.GET.get('pagenum', '')
        pagesize = request.GET.get('pagesize', '')

        print(pagenum)
        print(pagesize)
        print(order_no)
        print(gp_model)
        print(start_time)
        print(end_time)
        SQL = "SELECT * FROM planorder_stand_tab"

        search_tag = False
        # 添加搜索条件  未完成 待补充
        if gp_model != "":
            if search_tag:
                SQL += " AND gp_model = '" + gp_model + "'"
            else:
                SQL += " WHERE gp_model = '" + gp_model + "'"
                search_tag = True
        if order_no != "":
            if search_tag:
                SQL += " AND order_no = '" + order_no + "'"
            else:
                SQL += " WHERE order_no = '" + order_no + "'"
                search_tag = True
        if start_time != "" and end_time != "":
            if search_tag:
                SQL += " AND datetime BETWEEN '"+start_time+"' AND '"+end_time+"'"
            else:
                SQL += " WHERE datetime BETWEEN '"+start_time+"' AND '"+end_time+"'"
                search_tag = True
        # start_time = request.GET.get('start_time', '')
        # end_time = request.GET.get('end_time', '')
        SQL += " ORDER BY online_time DESC"

        print(SQL)
        data = aview_easy_sql_reader_page1(SQL, pagenum, pagesize)
        print(data)
        meta = {
            "msg": "获取工单列表成功!",
            "result": "OK"
        }
        backdata = {
            "data": data,
            "meta": meta,
        }

        print(backdata)
        # print(SQL)
        return HttpResponse(List_Json(backdata))
    except Exception as err:
        print(err)
        meta = {
            "msg": "获取计划列表失败!",
            "result": "NG"
        }
        data = {}
        backdata = {
            "data": data,
            "meta": meta,
        }
        return HttpResponse(List_Json(backdata))
def Getorder_re(request):
    try:
        gp_model = request.GET.get('gp_model', '')
        order_no = request.GET.get('order_no', '')
        start_time = request.GET.get('start_time', '')
        end_time = request.GET.get('end_time', '')

        pagenum = request.GET.get('pagenum', '')
        pagesize = request.GET.get('pagesize', '')

        print(pagenum)
        print(pagesize)
        print(order_no)
        print(gp_model)
        print(start_time)
        print(end_time)
        # 查询所有离线支架工单
        SQL1 = "SELECT * FROM planorder_stand_tab"

        search_tag = False
        # 添加搜索条件  未完成 待补充
        if gp_model != "":
            if search_tag:
                SQL1 += " AND gp_model = '" + gp_model + "'"
            else:
                SQL1 += " WHERE gp_model = '" + gp_model + "'"
                search_tag = True
        if order_no != "":
            if search_tag:
                SQL1 += " AND order_no = '" + order_no + "'"
            else:
                SQL1 += " WHERE order_no = '" + order_no + "'"
                search_tag = True
        if start_time != "" and end_time != "":
            if search_tag:
                SQL1 += " AND datetime BETWEEN '" + start_time + "' AND '" + end_time + "'"
            else:
                SQL1 += " WHERE datetime BETWEEN '" + start_time + "' AND '" + end_time + "'"
                search_tag = True
        # start_time = request.GET.get('start_time', '')
        # end_time = request.GET.get('end_time', '')
        if search_tag:
            SQL1 += " AND type = '1'"
        else:
            SQL1 += " WHERE type = '1'"
        print(SQL1)

        # 查询所有离线镜头工单
        SQL2 = "SELECT * FROM planorder_tab"
        search_tag = False
        # 添加搜索条件  未完成 待补充
        if gp_model != "":
            if search_tag:
                SQL2 += " AND gp_model = '" + gp_model + "'"
            else:
                SQL2 += " WHERE gp_model = '" + gp_model + "'"
                search_tag = True
        if order_no != "":
            if search_tag:
                SQL2 += " AND order_no = '" + order_no + "'"
            else:
                SQL2 += " WHERE order_no = '" + order_no + "'"
                search_tag = True
        if start_time != "" and end_time != "":
            if search_tag:
                SQL2 += " AND datetime BETWEEN '" + start_time + "' AND '" + end_time + "'"
            else:
                SQL2 += " WHERE datetime BETWEEN '" + start_time + "' AND '" + end_time + "'"
                search_tag = True
        # start_time = request.GET.get('start_time', '')
        # end_time = request.GET.get('end_time', '')
        if search_tag:
            SQL2 += " AND type = '1'"
        else:
            SQL2 += " WHERE type = '1'"
        print(SQL2)
        SQL = SQL1 + " UNION " + SQL2

        print(SQL)
        data = aview_easy_sql_reader_page1(SQL, pagenum, pagesize)
        print(data)

        meta = {
            "msg": "获取工单列表成功!",
            "result": "OK"
        }
        backdata = {
            "data": data,
            "meta": meta,
        }

        print(backdata)
        # print(SQL)
        return HttpResponse(List_Json(backdata))
    except Exception as err:
        print(err)
        meta = {
            "msg": "获取计划列表失败!",
            "result": "NG"
        }
        data = {}
        backdata = {
            "data": data,
            "meta": meta,
        }
        return HttpResponse(List_Json(backdata))
# 产品重传数据获取 包括线体和线外独立站点  通过站点名称来区分
def Getpro_re(request):
    try:
        # 获取参数 准备带参搜索 默认为空
        gp_model = request.GET.get('gp_model', '')
        order_no = request.GET.get('order_no', '')
        start_time = request.GET.get('start_time', '')
        end_time = request.GET.get('end_time', '')
        pagenum = request.GET.get('pagenum', '')
        pagesize = request.GET.get('pagesize', '')

        print(gp_model)
        print(order_no)
        print(start_time)
        print(end_time)
        print(pagenum)
        print(pagesize)

        # 查询所有失败产记录信息
        SQL = "SELECT * FROM mom_message"

        search_tag = False
        # 添加搜索条件  未完成 待补充
        if gp_model != "":
            if search_tag:
                SQL += " AND gp_model = '" + gp_model + "'"
            else:
                SQL += " WHERE gp_model = '" + gp_model + "'"
                search_tag = True
        if order_no != "":
            if search_tag:
                SQL += " AND order_no = '" + order_no + "'"
            else:
                SQL += " WHERE order_no = '" + order_no + "'"
                search_tag = True
        if start_time != "" and end_time != "":
            if search_tag:
                SQL += " AND datetime BETWEEN '" + start_time + "' AND '" + end_time + "'"
            else:
                SQL += " WHERE datetime BETWEEN '" + start_time + "' AND '" + end_time + "'"
                search_tag = True
        # SQL += "order By datetime"
        # if search_tag:
        #     SQL += " AND type = '1'"
        # else:
        #     SQL += " WHERE type = '1'"
        print(SQL)
        data = aview_easy_sql_reader_page1(SQL, pagenum, pagesize)
        print(data)

        meta = {
            "msg": "获取产品列表成功!",
            "result": "OK"
        }
        backdata = {
            "data": data,
            "meta": meta,
        }

        print(backdata)
        # print(SQL)
        return HttpResponse(List_Json(backdata))
    except Exception as err:
        print(err)
        meta = {
            "msg": "获取计划列表失败!",
            "result": "NG"
        }
        data = {}
        backdata = {
            "data": data,
            "meta": meta,
        }
        return HttpResponse(List_Json(backdata))
def Order_dataup(request):
    try:
        order_no = request.GET.get('order_no', '')
        if order_no == "":
            raise Exception("订单号为空")
        else:
            SQL = "SELECT * FROM ordersn_tab WHERE order_no = '" + order_no + "'"
            print(SQL)
            data = easy_sql_reader(SQL)
            # print(data)
            # for it in data:
            #     print(it)
            #     #发送给MOM
            url = "http://10.251.84.53:8181/mes.asmx/GetPlanOrder"
            msg = {"FACTORYCODE": "B620", "LINENO": "SXTMZ01", "PRODUCTDATE": "2023-11-07", "SHIFTNO": "0"}

            ret_data = SendMessage2MOM(msg, url)
            print("------------------------------------------")
            # SQL = "SELECT * FROM qr_confrimation_tab WHERE "
            meta = {
                "msg": ret_data,
                "result": "OK"
            }
            data = {}
            backdata = {
                "data": data,
                "meta": meta,
            }
    except Exception as err:
        print(err)
        meta = {
            "msg": str(err),
            "result": "NG"
        }
        data = {}
        backdata = {
            "data": data,
            "meta": meta,
        }
    return HttpResponse(List_Json(backdata))
# 重新发送给MOM
def Re_SendMessage2MOM(sn,code_name,station_no,gp_model,order_no,test_result):
    log.info(">>>>>>>>ReSendMessage2MOM")
    station_no = station_no.upper()
    t= datetime.datetime.now()
    mom_uuid1 = t.strftime('%Y%m%d')
    mom_uuid2 = ""
    line_no = Getline_no()
    SQL = "SELECT * FROM planorder_partno_tab WHERE gp_model = '" + gp_model + "'"
    partno_data = SQL_function3(SQL)
    SQL = "SELECT * FROM ordersn_tab WHERE " + code_name + " = '" + sn + "'"
    code_data = SQL_function3(SQL)
    SQL = "SELECT * FROM planorder_tab WHERE order_no = '" + order_no + "'"
    order_data = SQL_function3(SQL)

    if "SP" in station_no:
        SQL = "SELECT * FROM qr_confrimation_tab_sp WHERE " + code_name + " = '" + sn + "'"
        sta_data = SQL_function3(SQL)
    else:
        SQL = "SELECT * FROM qr_confrimation_tab WHERE " + code_name + " = '" + sn + "'"
        sta_data = SQL_function3(SQL)

    if len(sta_data) == 0:
        msg = "未查询到该sn信息"
        raise Exception(msg)
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
            "SN": sn,
            "PART_NO": order_data[0]['part_no'],
            "STATION_STATUS": test_result.upper(),
        }
        # 发送单站状态给MOM ---- 生产过程信息接口
        # if Planorder_ismomcheck(code_name,sn):
        ret_data = ProcessInfo(Data2mom)
        log.info("----------ret_data" + str(ret_data))
        if ret_data['STATUS'] == "NG":
            log.info(ret_data['ERRORMSG'])
            raise Exception(ret_data['ERRORMSG'])
    if "SP" in station_no:
        PlanOrderReport_SP(code_name, sn, station_no)
    else:
        PlanOrderReport(code_name, sn, station_no)

    # # ---------------------- 发送NG或最终OK 给看板 ------------------------------
    # # 发送产品最终生产信息给看板统计
    # # （只需要发送最后一站/失败的dataup结果，也就是最终产品的生产成败信息）
    # model_tag = cache.get('ModelSetFlag', default=0)
    # current_model = cache.get('current_model')
    # current_order = cache.get('current_order')
    # current_order_stand = cache.get('current_order_stand')

def Pro_dataup(request):
    # data = {}
    # myurl = ""
    # params = ""
    try:
        gp_model = request.GET.get('gp_model', '')
        # 顶栏搜索的order  上传数据的order_no
        order_no = request.GET.get('order_no', '')
        order = request.GET.get('order', '')
        start_time = request.GET.get('start_time', '')
        end_time = request.GET.get('end_time', '')
        pagenum = request.GET.get('pagenum', '')
        pagesize = request.GET.get('pagesize', '')
        params = {"gp_model":gp_model,"order_no":order,"start_time":start_time,"end_time":end_time,"pagenum":pagenum,"pagesize":pagesize}
        myip = Getmyip()
        myurl = 'http://' + str(myip) + ':9000/api/Order/Getpro_re'

        t = datetime.datetime.now()
        sn = request.GET.get('sn', '')
        url = request.GET.get('url', '')
        station_no = request.GET.get('station_no', '')

        SQL = "SELECT * FROM mom_message WHERE sn = '" + sn + "' and station_no = '" + station_no + "'"
        data = SQL_function3(SQL)
        if len(data) == 0:
            msg = "mom_message中未找到对应信息"
            raise Exception(msg)

        code_name = data[0]['code_name']
        station_no = data[0]['station_no']
        gp_model = data[0]['gp_model']
        order_no = data[0]['order_no']
        test_result = data[0]['test_result']
        ret = Re_SendMessage2MOM(sn,code_name,station_no,gp_model,order_no,test_result)
        print("------------ret:" + str(ret))
        if ret['STATUS'] == "NG":
            raise Exception(ret['ERRORMSG'])
        if ret['STATUS'] == "OK":
            SQL = "DELETE FROM mom_message WHERE sn = '" + sn + "' and station_no = '" + station_no + "'"
            if SQL_function4(SQL) is False:
                msg = "发送至MOM成功，本地删除记录失败，请检查"
                raise Exception(msg)

        response = requests.get(url=myurl, params=params)
        ret_data = json.loads(response.text)
        data = ret_data['data']
        meta = {
            "msg": "上传MOM成功",
            "result": "OK"
        }
        backdata = {
            "data": data,
            "meta": meta,
        }

    except Exception as err:
        print(str(err))
        log.info(str(err))
        response = requests.get(url=myurl, params=params)
        ret_data = json.loads(response.text)
        data = ret_data['data']
        meta = {
            "msg": str(err),
            "result": "NG"
        }
        backdata = {
            "data": data,
            "meta": meta,
        }
    log.info("HttpResponse:" + str(backdata))
    return HttpResponse(List_Json(backdata))
def Pro_dataup_all(request):
    try:
        SQL = "SELECT * FROM mom_message"
        data = SQL_function3(SQL)
        if len(data) == 0:
            msg = "当前记录为空"
            raise Exception(msg)
        for it in data:
            sn = it['sn']
            code_name = it['code_name']
            station_no = it['station_no']
            gp_model = it['gp_model']
            order_no = it['order_no']
            test_result = it['test_result']
            ret = Re_SendMessage2MOM(sn, code_name, station_no, gp_model, order_no, test_result)

            if ret['STATUS'] == "NG":
                raise Exception(ret['ERRORMSG'])
            if ret['STATUS'] == "OK":
                SQL = "DELETE FROM mom_message WHERE sn = '" + sn + "' and station_no = '" + station_no + "'"
                if SQL_function4(SQL) is False:
                    msg = "发送至MOM成功，本地删除记录失败，请检查"
                    raise Exception(msg)

            sn = it['sn']
            url = it['url']
            station_no = it['station_no']
            data = it['msg']
            ret = SendMessage2MOM(data, url)
            if ret['STATUS'] == "NG":
                raise Exception(ret['ERRORMSG'])
            if ret['STATUS'] == "OK":
                SQL = "DELETE FROM mom_message WHERE sn = '" + sn + "' and url = '" + url + "' and station_no = '" + station_no + "'"
                if SQL_function4(SQL) is False:
                    msg = "发送至MOM成功，本地删除记录失败,请检查"
                    raise Exception(msg)
        data = {}
        meta = {
            "msg": "批量上传MOM成功",
            "result": "OK"
        }
        backdata = {
            "data": data,
            "meta": meta,
        }

    except Exception as err:
        print(str(err))
        log.info(str(err))
        data = {}
        meta = {
            "msg": str(err),
            "result": "NG"
        }
        backdata = {
            "data": data,
            "meta": meta,
        }
    return HttpResponse(List_Json(backdata))

def Info_upload(request):
    try:
        current_model = cache.get('current_model')
        select_model = request.GET.get('select_model', '')
        if not select_model == "":
            current_model = select_model

        # K_PART_NO = request.GET.get('K_PART_NO', '')            # 壳体物料号
        # K_PART_BATCH = request.GET.get('K_PART_BATCH', '')      # 壳体物料批次
        Q_PART_NO = request.GET.get('Q_PART_NO', '')            # *前壳料号
        Q_PART_BATCH = request.GET.get('Q_PART_BATCH', '')      # 前壳批次号
        JS_PART_NO = request.GET.get('JS_PART_NO', '')            # 胶水物料号
        JS_PART_BATCH = request.GET.get('JS_PART_BATCH', '')      # 胶水批次号
        H_PART_NO = request.GET.get('H_PART_NO', '')            # *后壳物料号
        H_PART_BATCH = request.GET.get('H_PART_BATCH', '')      # 后壳批次号
        # F_PART_NO = request.GET.get('F_PART_NO', '')            # fakra物料号
        # F_PART_BATCH = request.GET.get('F_PART_BATCH', '')      # fakra批次号
        L_PART_NO = request.GET.get('L_PART_NO', '')            # 螺丝物料号
        L_PART_BATCH = request.GET.get('L_PART_BATCH', '')      # 螺丝批次号
        Z_PART_NO = request.GET.get('Z_PART_NO', '')            # 支架物料号
        Z_PART_BATCH = request.GET.get('Z_PART_BATCH', '')      # 支架批次号
        P_PART_NO = request.GET.get('P_PART_NO', '')            # pcba物料号
        P_PART_BATCH = request.GET.get('P_PART_BATCH', '')      # pcba壳批次号
        J_PART_NO = request.GET.get('J_PART_NO', '')            # 镜头物料号
        J_PART_BATCH = request.GET.get('J_PART_BATCH', '')      # 镜头批次号

        ZC_PART_NO = request.GET.get('ZC_PART_NO', '')
        BT_PART_NO = request.GET.get('BT_PART_NO', '')

        SQL = "UPDATE planorder_partno_tab SET Q_PART_NO = '" + Q_PART_NO + "',H_PART_NO = '" + H_PART_NO + "',P_PART_NO = '" + P_PART_NO + "',J_PART_NO = '" + J_PART_NO + "',JS_PART_NO = '" + JS_PART_NO+ "',L_PART_NO = '" + L_PART_NO\
              + "',Q_PART_BATCH = '" + Q_PART_BATCH + "',H_PART_BATCH = '" + H_PART_BATCH + "',P_PART_BATCH = '" + P_PART_BATCH + "',J_PART_BATCH = '" + J_PART_BATCH + "',JS_PART_BATCH = '" + JS_PART_BATCH + "',Z_PART_NO = '" + Z_PART_NO + "',Z_PART_BATCH = '" + Z_PART_BATCH + "',L_PART_BATCH = '" + L_PART_BATCH + "',BT_PART_NO = '" + BT_PART_NO + "',ZC_PART_NO = '" + ZC_PART_NO + "' WHERE gp_model = '" + current_model + "'"
        print(SQL)
        if not sql_execute(SQL):
            raise Exception('SQL执行失败！')
        meta = {
            "msg": "更新成功",
            "result": "OK"
        }
        data = {}
        backdata = {
            "data": data,
            "meta": meta,
        }
        return HttpResponse(List_Json(backdata))
    except Exception as err:
        print(str(err))
        meta = {
            "msg": str(err),
            "result": "NG"
        }
        data = {}
        backdata = {
            "data": data,
            "meta": meta,
        }
        return HttpResponse(List_Json(backdata))
# 当前存在物料号跟随型号绑定和独立的全局物料号，后序将型号绑定的物料号同步至全局物料号使用，在换型时切换，物料号判定全部改为对全局物料号的比对
def Get_info(request):
    try:
        current_model = cache.get('current_model')
        select_model = request.GET.get('select_model', '')
        if not select_model == "":
            current_model = select_model
        SQL = "SELECT * FROM planorder_partno_tab WHERE gp_model = '" + current_model + "'"
        print(SQL)
        ret_db = easy_sql_reader(SQL)
        print(ret_db)
        data = {
            "Q_PART_NO": ret_db[0]['Q_PART_NO'],
            "H_PART_NO": ret_db[0]['H_PART_NO'],
            "P_PART_NO": ret_db[0]['P_PART_NO'],
            "J_PART_NO": ret_db[0]['J_PART_NO'],
            "L_PART_NO": ret_db[0]['L_PART_NO'],
            "Z_PART_NO": ret_db[0]['Z_PART_NO'],
            "BT_PART_NO": ret_db[0]['BT_PART_NO'],
            "ZC_PART_NO": ret_db[0]['ZC_PART_NO'],
            "Q_PART_BATCH": ret_db[0]['Q_PART_BATCH'],
            "H_PART_BATCH": ret_db[0]['H_PART_BATCH'],
            "P_PART_BATCH": ret_db[0]['P_PART_BATCH'],
            "J_PART_BATCH": ret_db[0]['J_PART_BATCH'],
            "L_PART_BATCH": ret_db[0]['L_PART_BATCH'],
        }
        meta = {
            "msg": "获取成功",
            "result": "OK"
        }
        backdata = {
            "data": data,
            "meta": meta,
        }
        print(backdata)
        return HttpResponse(List_Json(backdata))
    except Exception as err:
        print(str(err))
        meta = {
            "msg": str(err),
            "result": "NG"
        }
        data = {}
        backdata = {
            "data": data,
            "meta": meta,
        }
        return HttpResponse(List_Json(backdata))
# # 当前已经设置镭雕逻辑的型号列表
# def laser_modeltab(request):
#     SQL = "SELECT gp_model FROM planorder_laser_tab"
#     data = SQL_function3(SQL)
#
# 获取某型号镭雕配置，若有信息则展示，若无信息
def Lasercode_get(request):
    try:
        gp_model = request.GET.get('gp_model', '')
        SQL = "SELECT * FROM planorder_laser_tab WHERE gp_model = '" + gp_model + "'"
        data = SQL_function3(SQL)
        # 从模板表中获取所有模板信息，发给前端使用
        SQL = "SELECT * FROM planorder_laser_template_tab WHERE template_type = '0'"
        template = SQL_function3(SQL)
        SQL = "SELECT * FROM planorder_laser_template_tab WHERE template_type = '1'"
        stand_template = SQL_function3(SQL)


        code_msg = []
        stand_code_msg = []
        if len(data) == 0:
            data = {
                "code_msg": code_msg,
                "stand_code_msg": stand_code_msg,
                "template": template,
                "stand_template": stand_template
            }
            meta = {
                "msg": "该型号未设置",
                "result": "NG"
            }
            backdata = {
                "data": data,
                "meta": meta,
            }
        elif len(data) == 1:
            SQL = "SELECT template_rule FROM planorder_laser_template_tab WHERE template_name = '" + data[0]['code_rule'] + "'"
            rule_data = SQL_function3(SQL)
            SQL = "SELECT template_rule FROM planorder_laser_template_tab WHERE template_name = '" + data[0]['stand_code_rule'] + "'"
            stand_rule_data = SQL_function3(SQL)
            code_rule = []
            stand_code_rule = []
            if not len(rule_data) == 0:
                code_rule = rule_data[0]['template_rule'].split("@")
            if not len(stand_code_rule) == 0:
                stand_code_rule = stand_rule_data[0]['template_rule'].split("@")

            rule_id = 0
            for name in code_rule:
                code_item = {}
                code_item['rule_id'] = rule_id
                code_item['code_name'] = name
                code_item['code_value'] = data[0][name]
                code_msg.append(code_item)
                rule_id += 1

            stand_rule_id = 0
            for name in stand_code_rule:
                code_item = {}
                code_item['stand_rule_id'] = stand_rule_id
                code_item['code_name'] = name
                code_item['code_value'] = data[0][name]
                stand_code_msg.append(code_item)
                stand_rule_id += 1

            data = {
                "code_msg": code_msg,
                "stand_code_msg": stand_code_msg,
                "template": template,
                "stand_template": stand_template
            }
            meta = {
                "msg": "",
                "result": "OK"
            }
            backdata = {
                "data": data,
                "meta": meta,
            }

    except Exception as err:
        print(str(err))
        meta = {
            "msg": str(err),
            "result": "NG"
        }
        data = {}
        backdata = {
            "data": data,
            "meta": meta,
        }
    print(backdata)
    return HttpResponse(List_Json(backdata))

def Lasercode_template_init(template_name, template_type, gp_model):
    if template_type == "":
        raise Exception("template_type 为空")
    SQL = "SELECT * FROM planorder_laser_template_tab WHERE template_name = '" + template_name + "' and template_type = '" + template_type + "'"
    template_data = SQL_function3(SQL)
    template_rule = template_data[0]['template_rule'].split("@")
    SQL = "SELECT column_name FROM information_schema.COLUMNS WHERE table_name = 'planorder_laser_tab'"
    column_data = SQL_function3(SQL)
    for it1 in template_rule:
        for it2 in column_data:
            if it2['COLUMN_NAME'] == it1:
                break
        else:
            SQL = "ALTER TABLE planorder_laser_tab ADD (" + it1 + " varchar(255) default '')"
            if not SQL_function4(SQL):
                msg = "planorder_laser_tab插入" + it + "失败"
                raise Exception(msg)

    if template_data[0]['template_type'] == "0":
        # 此语句是需要把gp_model设置为表的唯一索引才能实现
        SQL = "INSERT INTO planorder_laser_tab (gp_model,code_rule) values ('" + gp_model + "','" + template_data[0][
            'template_name'] + "') ON DUPLICATE KEY UPDATE code_rule= '" + template_data[0]['template_name'] + "'"
        if not SQL_function4(SQL):
            msg = "planorder_laser_tab插入数据失败"
            raise Exception(msg)
    elif template_data[0]['template_type'] == "1":
        SQL = "INSERT INTO planorder_laser_tab (gp_model,stand_code_rule) values ('" + gp_model + "','" + \
              template_data[0]['template_name'] + "') ON DUPLICATE KEY UPDATE stand_code_rule= '" + template_data[0][
                  'template_name'] + "'"
        if not SQL_function4(SQL):
            msg = "planorder_laser_tab插入数据失败"
            raise Exception(msg)
# 新增/修改某型号的镭雕头部信息
#如果为修改，code_data中存储的是该型号的最新的修改信息
#如果为新增，code_data为空，template_name template_type 来确定该型号使用的规则模板，后端对应创建后，返回对应型号Lasercode_get信息，进入修改状态
def Lasercode_set(request):
    try:
        gp_model = request.GET.get('gp_model', '')
        js_data = request.GET.get('data', '')
        if js_data == "":
            raise Exception("请求数据为空")
        code_data = json.loads(js_data)
        template_name = request.GET.get('template_name', '')
        template_type = request.GET.get('template_type', '')

        # 如果没有镭雕参数数据，就是使用模板初始化该型号的镭雕变量
        if len(code_data['code_msg']) == 0 and len(code_data['stand_code_msg']) == 0:
            Lasercode_template_init(template_name, template_type, gp_model)
        else: # 如果有镭雕参数数据。有模板数据，就检查与当前型号的对应模板是否一致，不一致删除数据更新模板。无模板数据，就只更新镭雕参数
            if template_name == "":
                for it in code_data['code_msg']:
                    SQL = "UPDATE planorder_laser_tab SET " + it['code_name'] + " = '" + it['code_value'] + "'"
                    if not SQL_function4(SQL):
                        msg = "planorder_laser_tab更新数据失败"
                for it in code_data['stand_code_msg']:
                    SQL = "UPDATE planorder_laser_tab SET " + it['code_name'] + " = '" + it['code_value'] + "'"
                    if not SQL_function4(SQL):
                        msg = "planorder_laser_tab更新数据失败"
            else:
                SQL = "SELECT * FROM planorder_laser_tab WHERE gp_model = '" + gp_model + "'"
                data = SQL_function3(SQL)
                if template_name == data[0]['code_rule'] or template_name == data[0]['stand_code_rule']:
                    msg = "新模板与当前模板一致"
                    raise Exception(msg)
                else:
                    SQL = "DELETE FROM planorder_laser_tab WHERE gp_model = '" + gp_model + "'"
                    if not SQL_function4(SQL):
                        msg = "删除型号镭雕模板失败"
                        raise Exception(msg)
                    Lasercode_template_init(template_name, template_type, gp_model)

        myip = Getmyip()
        url = 'http://' + str(myip) + ':9000/api/Order/Lasercode_get'
        params = {'gp_model': gp_model}
        response = requests.get(url=url, params=params)
        backdata = json.loads(response.text)

    except Exception as err:
        print(str(err))
        log.info(str(err))
        myip = Getmyip()
        url = 'http://' + str(myip) + ':9000/api/Order/Lasercode_get'
        params = {'gp_model': gp_model}
        response = requests.get(url=url, params=params)
        backdata = json.loads(response.text)
        print(backdata['meta'])
        backdata['meta']['msg'] = str(err)
        backdata['meta']['result'] = "NG"
    return HttpResponse(List_Json(backdata))
# -------------------------------------------- Mes Setting Mes设置--------------------------------------------
def Get_setting(request):
    try:
        filepath = GetFilePath("SoftWare.ini")
        conf = ConfigParser()  # 需要实例化一个ConfigParser对象
        conf.read(filepath)  # 需要添加上config.ini的路径，不需要open打开，直接给文件路径就读取，也可以指定encoding='utf-8'
        # int 类型
        line_no = int(conf['CommonUse']['line_no'])
        # bool 类型 False 表关闭 True 表打开
        partno_check_flag = str(conf['CommonUse']['partno_check_flag'])
        # string 类型 镭雕sn生成时的项目号
        sn_head = str(conf['CommonUse']['sn_head'])
        # mom上传失败后的报警
        timeout_alarm = str(conf['CommonUse']['mom_alarm'])
        # 胶水校验开关
        js_check_flag = str(conf['CommonUse']['js_check_flag'])
        # 最后一站完成是否上传MOM（过程信息+报工）
        mom_upload_flag = str(conf.get('CommonUse', 'mom_upload_flag', fallback='true'))

        if partno_check_flag.upper() == "TRUE":
            partno_check_flag = True
        elif partno_check_flag.upper() == "FALSE":
            partno_check_flag = False

        if timeout_alarm.upper() == "TRUE":
            timeout_alarm = True
        elif timeout_alarm.upper() == "FALSE":
            timeout_alarm = False

        if js_check_flag.upper() == "TRUE":
            js_check_flag = True
        elif js_check_flag.upper() == "FALSE":
            js_check_flag = False

        if mom_upload_flag.upper() == "TRUE":
            mom_upload_flag = True
        elif mom_upload_flag.upper() == "FALSE":
            mom_upload_flag = False

        data = {
            "line_no": line_no,
            "partno_check_flag": partno_check_flag,
            "sn_head": sn_head,
            "timeout_alarm": timeout_alarm,
            "js_check_flag": js_check_flag,
            "mom_upload_flag": mom_upload_flag
        }
        backdata = {
            "data": data,
            "meta": {
                "msg": "",
                "result": "OK"
                }
        }
        return HttpResponse(List_Json(backdata))
    except Exception as err:
        print(str(err))
        meta = {
            "msg": str(err),
            "result": "NG"
        }
        data = {}
        backdata = {
            "data": data,
            "meta": meta,
        }
        return HttpResponse(List_Json(backdata))

def Set_setting(request):
    try:
        line_no = str(request.GET.get('line_no', ''))
        partno_check_flag = str(request.GET.get('partno_check_flag', ''))
        sn_head = str(request.GET.get('sn_head', ''))
        timeout_alarm = str(request.GET.get('timeout_alarm', ''))
        js_check_flag = str(request.GET.get('js_check_flag', ''))
        mom_upload_flag = str(request.GET.get('mom_upload_flag', ''))
        try:
            line_no_int = int(line_no)
        except:
            raise Exception("线体号必须为数字")
        if not (partno_check_flag.upper() == "TRUE" or partno_check_flag.upper() == "FALSE"):
            raise Exception("选项必须为True或False")

        # 修改本地文件中的站点信息
        filepath = GetFilePath("SoftWare.ini")
        conf = ConfigParser()  # 需要实例化一个ConfigParser对象
        conf.read(filepath)  # 需要添加上config.ini的路径，不需要open打开，直接给文件路径就读取，也可以指定encoding='utf-8'
        if mom_upload_flag == '':
            mom_upload_flag = conf.get('CommonUse', 'mom_upload_flag', fallback='true')
        elif not (mom_upload_flag.upper() == "TRUE" or mom_upload_flag.upper() == "FALSE"):
            raise Exception("选项必须为True或False")
        conf.set('CommonUse', 'line_no', line_no)
        conf.set('CommonUse', 'partno_check_flag', partno_check_flag)
        conf.set('CommonUse', 'sn_head', sn_head)
        conf.set('CommonUse', 'mom_alarm', timeout_alarm)
        conf.set('CommonUse', 'js_check_flag', js_check_flag)
        conf.set('CommonUse', 'mom_upload_flag', mom_upload_flag)
        with open(filepath, 'w', encoding='utf-8') as f:
            conf.write(f)
        backdata = {
            "data": {},
            "meta": {
                "msg": "保存成功",
                "result": "OK"
            }
        }
        return HttpResponse(List_Json(backdata))
    except Exception as err:
        print(str(err))
        meta = {
            "msg": str(err),
            "result": "NG"
        }
        data = {}
        backdata = {
            "data": data,
            "meta": meta,
        }
        return HttpResponse(List_Json(backdata))
# --------------------------------------------MOM--------------------------------------------
# MOM请求修改工单生产数量 0 为取消工单  (接口无法直接区分支架工单和摄像头工单，两个表都得查询)
def ChangePlanOrderList(request):
    try:
        tab_list = ['planorder_tab','planorder_stand_tab']
        t = datetime.datetime.now()

        FACTORYCODE = request.POST.get('FACTORYCODE', '')
        ORDERNO = request.POST.get('ORDERNO', '')
        PARTNO = request.POST.get('PARTNO', '')
        NUM = request.POST.get('NUM', '')
        LINENO = request.POST.get('LINENO', '')
        SHIFTNO = request.POST.get('SHIFTNO', '')
        print("FACTORYCODE:" + str(FACTORYCODE))
        print("ORDERNO:" + str(ORDERNO))
        print("PARTNO:" + str(PARTNO))
        print("NUM:" + str(NUM))
        print("LINENO:" + str(LINENO))
        print("SHIFTNO:" + str(SHIFTNO))
        if FACTORYCODE == "" :
            raise Exception("FACTORYCODE 为空")
        if ORDERNO == "" :
            raise Exception("ORDERNO 为空")
        if PARTNO == "" :
            raise Exception("PARTNO 为空")
        if NUM == "" :
            raise Exception("NUM 为空")
        if LINENO == "" :
            raise Exception("LINENO 为空")
        if SHIFTNO == "" :
            raise Exception("SHIFTNO 为空")
        SQL1 = "SELECT * FROM planorder_tab WHERE factory_code = '" + FACTORYCODE + "' and order_no = '" + ORDERNO + "' and part_no = '" + PARTNO + "' and line_no = '" + LINENO + "' and shift_no = '" + SHIFTNO + "'"
        SQL2 = "SELECT * FROM planorder_stand_tab WHERE factory_code = '" + FACTORYCODE + "' and order_no = '" + ORDERNO + "' and part_no = '" + PARTNO + "' and line_no = '" + LINENO + "' and shift_no = '" + SHIFTNO + "'"
        SQL = SQL1 + " UNION " + SQL2
        data = SQL_function3(SQL)
        if len(data) == 0:
            msg = "未找到对应工单信息，修改失败"
            raise Exception(msg)
        elif len(data) > 1:
            msg = "找到多个对应工单信息，修改失败"
            raise Exception(msg)
        if str(NUM) == "0":
            for it in tab_list:
                SQL = "UPDATE " + it + " SET status = 'Close',offline_time = '" + str(t) + "' WHERE factory_code = '" + FACTORYCODE + "' and order_no = '" + ORDERNO + "' and part_no = '" + PARTNO + "' and line_no = '" + LINENO + "' and shift_no = '" + SHIFTNO + "'"
                if SQL_function4(SQL) is False:
                    msg = "关闭工单失败"
                    raise Exception(msg)

        else:
            for it in tab_list:
                SQL = "UPDATE " + it + " SET num = '" + NUM + "' WHERE factory_code = '" + FACTORYCODE + "' and order_no = '" + ORDERNO + "' and part_no = '" + PARTNO + "' and line_no = '" + LINENO + "' and shift_no = '" + SHIFTNO + "'"
                if SQL_function4(SQL) is False:
                    msg = "修改工单数量失败"
                    raise Exception(msg)

        backdata = {
            "STATUS": "OK",
            "NUM": NUM,
            "ERRORMSG": "",
        }
    except Exception as err:
        log.info(err)
        backdata = {
            "STATUS": "NG",
            "NUM": "",
            "ERRORMSG": str(err),
        }
    return HttpResponse(List_Json(backdata))
# -----------------------------上线此工单-----------------------------------
# 向MOM请求获取按工单按钮， 检验旧工单是否完成，切换到新的工单
def GetPlanOrder_btn(request):
    try:
        t = datetime.datetime.now()
        productdate = request.GET.get('productdate', '' )
        print(productdate)
        if productdate == "":
            productdate = t.strftime('%Y-%m-%d')
        else:
            productdate = datetime.datetime.strptime(productdate, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
        # 调用msg_operation 中的方法
        ret_backdata = GetPlanOrder(productdate)
        ret_backdata = eval(ret_backdata)
        print("GetPlanOrder_btn")
        print(ret_backdata)
        SQL = "SELECT * FROM planorder_tab ORDER BY online_time DESC"
        print(SQL)
        ret_db = easy_sql_reader(SQL)
        print(ret_db)
        data = []
        for item in ret_db:
            print(item)
            temp_order = {
                "order_no": item['order_no'],
                "num": item['num'],
                "num_real": item['num_real'],
                "gp_model": item['gp_model'],
                "datetime": str(item['datetime']),
                "factory_code": item['factory_code'],
                "soft_ver": item['soft_ver'],
                "shift_no": item['shift_no'],
                "line_no": item['line_no'],
                "part_no": item['part_no'],
                "status": item['status'],
            }
            data.append(temp_order)

        if ret_backdata['result'] == "False":
            meta = {
                "msg": ret_backdata['msg'],
                "result": "NG"
            }
            backdata = {
                "data": data,
                "meta": meta,
            }
        else:
            meta = {
                "msg": "获取到新工单:" + cache.get('current_order'),
                "result": "OK"
            }
            backdata = {
                "data": data,
                "meta": meta,
            }
    except Exception as err:
        log.info(err)
        meta = {
            "msg": str(err),
            "result": "NG"
        }
        data = {}
        backdata = {
            "data": data,
            "meta": meta,
        }
    print(backdata)
    return HttpResponse(List_Json(backdata))
def GetPlanOrder_btn_stand(request):
    try:
        t = datetime.datetime.now()
        productdate = request.GET.get('productdate', '')
        print(productdate)
        if productdate == "":
            productdate = t.strftime('%Y-%m-%d')
        else:
            productdate = datetime.datetime.strptime(productdate, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
        # 调用msg_operation 中的方法
        ret_backdata = GetPlanOrder_stand(productdate)
        ret_backdata = eval(ret_backdata)
        print("GetPlanOrder_btn_stand")
        print(ret_backdata)
        SQL = "SELECT * FROM planorder_stand_tab ORDER BY online_time DESC"
        print(SQL)
        ret_db = easy_sql_reader(SQL)
        print(ret_db)
        data = []
        for item in ret_db:
            print(item)
            temp_order = {
                "order_no": item['order_no'],
                "num": item['num'],
                "num_real": item['num_real'],
                "gp_model": item['gp_model'],
                "datetime": str(item['datetime']),
                "factory_code": item['factory_code'],
                "soft_ver": item['soft_ver'],
                "shift_no": item['shift_no'],
                "line_no": item['line_no'],
                "part_no": item['part_no'],
                "status": item['status'],
            }
            data.append(temp_order)

        if ret_backdata['result'] == "False":
            meta = {
                "msg": ret_backdata['msg'],
                "result": "NG"
            }
            backdata = {
                "data": data,
                "meta": meta,
            }
        else:
            meta = {
                "msg": "获取到新支架工单:" + cache.get('current_order'),
                "result": "OK"
            }
            backdata = {
                "data": data,
                "meta": meta,
            }
    except Exception as err:
        log.info(err)
        meta = {
            "msg": str(err),
            "result": "NG"
        }
        data = {}
        backdata = {
            "data": data,
            "meta": meta,
        }
    print(backdata)
    return HttpResponse(List_Json(backdata))
def ClosePlanOrder_btn(request):
    try:
        myip = Getmyip()
        url = 'http://' + str(myip) + ':9000/api/Order/Getorder'
        print(url)
        start_time = request.GET.get('start_time', '')
        end_time = request.GET.get('end_time', '')
        pagenum = request.GET.get('pagenum', '')
        pagesize = request.GET.get('pagesize', '')

        order_no = cache.get('current_order')
        SQL = "SELECT * FROM planorder_tab WHERE order_no = '" + order_no + "'"
        print(SQL)
        data = easy_sql_reader(SQL)
        if len(data) == 1:
            SQL = "UPDATE planorder_tab SET status = 'Close' WHERE order_no = '" + order_no + "'"
            print(SQL)
            if not sql_execute(SQL):
                raise Exception('SQL执行失败！')
        else:
            raise Exception('查询到多个工单信息，请检查')

        params = {'order_no': '', 'pagesize': pagesize, 'pagenum': pagenum,
                  'start_time': start_time, 'end_time': end_time}
        print(params)
        response = requests.get(url=url, params=params)
        ret_data = json.loads(response.text)
        print("--------------------")
        print(ret_data)
        backdata = ret_data
        backdata['meta']['msg'] = "工单:" + order_no + "关闭成功"
    except Exception as err:
        log.info(err)
        params = {'order_no': '', 'pagesize': pagesize, 'pagenum': pagenum,
                  'start_time': start_time, 'end_time': end_time}
        print(params)
        response = requests.get(url=url, params=params)
        ret_data = json.loads(response.text)
        print("--------------------")
        print(ret_data)
        meta = {
            "msg": str(err),
            "result": "NG"
        }
        backdata = {
            "data": ret_data['data'],
            "meta": meta,
        }
    print(backdata)
    return HttpResponse(List_Json(backdata))
def ClosePlanOrder_btn_stand(request):
    try:
        myip = Getmyip()
        url = 'http://' + str(myip) + ':9000/api/Order/Getorder_stand'
        print(url)
        start_time = request.GET.get('start_time', '')
        end_time = request.GET.get('end_time', '')
        pagenum = request.GET.get('pagenum', '')
        pagesize = request.GET.get('pagesize', '')

        order_no = cache.get('current_order_stand')
        SQL = "SELECT * FROM planorder_stand_tab WHERE order_no = '" + order_no + "'"
        print(SQL)
        data = easy_sql_reader(SQL)
        if len(data) == 1:
            SQL = "UPDATE planorder_stand_tab SET status = 'Close' WHERE order_no = '" + order_no + "'"
            print(SQL)
            if not sql_execute(SQL):
                raise Exception('SQL执行失败！')
        else:
            raise Exception('查询到多个工单信息，请检查')

        params = {'order_no': '', 'pagesize': pagesize, 'pagenum': pagenum,
                  'start_time': start_time, 'end_time': end_time}
        print(params)
        response = requests.get(url=url, params=params)
        ret_data = json.loads(response.text)
        print("--------------------")
        print(ret_data)
        backdata = ret_data
        backdata['meta']['msg'] = "工单:" + order_no + "关闭成功"
    except Exception as err:
        log.info(err)
        params = {'order_no': '', 'pagesize': pagesize, 'pagenum': pagenum,
                  'start_time': start_time, 'end_time': end_time}
        print(params)
        response = requests.get(url=url, params=params)
        ret_data = json.loads(response.text)
        print("--------------------")
        print(ret_data)
        meta = {
            "msg": str(err),
            "result": "NG"
        }
        backdata = {
            "data": ret_data['data'],
            "meta": meta,
        }
    print(backdata)
    return HttpResponse(List_Json(backdata))
    #切换当前工单按钮

# def ChangePlanOrder_btn(request):
#     try:
#         myip = Getmyip()
#         url = 'http://' + str(myip) + ':9000/api/Order/Getorder'
#         order_no = request.GET.get('order_no', '')
#         start_time = request.GET.get('start_time', '')
#         end_time = request.GET.get('end_time', '')
#         pagenum = request.GET.get('pagenum', '')
#         pagesize = request.GET.get('pagesize', '')
#         t = datetime.datetime.now()
#
#         SQL = "SELECT * FROM planorder_tab WHERE order_no = '" + order_no + "'"
#         data = easy_sql_reader(SQL)
#         if len(data) == 1:
#             if data[0]['status'] == "":
#                 #将切换前工单状态
#                 current_order = cache.get('current_order')
#                 SQL = "SELECT * FROM planorder_tab WHERE order_no = '" + current_order + "'"
#                 data = SQL_function3(SQL)
#                 if data[0]['status'] == "Start" or data[0]['status'] == "Close":
#                     #更新sn_num数量
#                     t_day = t.day - datetime.datetime.strptime(data[0]['datetime'], '%Y-%m-%d %H:%M:%S').day
#                     print(t_day)
#                     if not t_day >= 1:
#                         SQL = "UPDATE mom_setting,planorder_tab set planorder_tab.sn_num = mom_setting.sn_num where planorder_tab.order_no = '" + current_order + "'"
#                         if not SQL_function4(SQL):
#                             raise Exception('SQL执行失败！')
#                     if data[0]['status'] == "Start":
#                         SQL = "UPDATE planorder_tab SET status = '',datetime = '" + str(
#                             t) + "' WHERE order_no = '" + current_order + "'"
#                         if not SQL_function4(SQL):
#                             raise Exception('SQL执行失败！')
#
#                 #更新切换后工单状态
#                 #恢复新工单sn_num数量至mom_setting中
#                 SQL = "SELECT * FROM planorder_tab WHERE order_no = '" + order_no + "'"
#                 data = SQL_function3(SQL)
#                 t_day = t.day - datetime.datetime.strptime(data[0]['datetime'], '%Y-%m-%d %H:%M:%S').day
#                 if not t_day >= 1:
#                     SQL = "UPDATE mom_setting,planorder_tab set mom_setting.sn_num = planorder_tab.sn_num where planorder_tab.order_no = '" + order_no + "'"
#                     if not SQL_function4(SQL):
#                         raise Exception('SQL执行失败！')
#
#                 SQL = "UPDATE planorder_tab SET status = 'Start',datetime = '" + str(t) + "' WHERE order_no = '" + order_no + "'"
#                 if not SQL_function4(SQL):
#                     raise Exception('SQL执行失败！')
#                 Cache_writer('current_order', order_no, None)
#                 #修改本地文件中当前订单信息
#                 filepath = GetFilePath("SoftWare.ini")
#                 conf = ConfigParser()  # 需要实例化一个ConfigParser对象
#                 conf.read(filepath)  # 需要添加上config.ini的路径，不需要open打开，直接给文件路径就读取，也可以指定encoding='utf-8'
#                 print(conf['CommonUse']['Currentorder'])
#                 conf.set('CommonUse', 'Currentorder', order_no)
#                 with open(filepath, 'w', encoding='utf-8') as f:
#                     conf.write(f)
#                 print(conf['CommonUse']['Currentorder'])
#             elif data[0]['status'] == "Close":
#                 raise Exception('已经关闭的工单不可使用')
#             elif data[0]['status'] == "Start":
#                 raise Exception('此工单已经开始')
#
#         else:
#             raise Exception('切换失败,未找到该工单,请检查')
#
#         params = {'order_no': '', 'pagesize': pagesize, 'pagenum': pagenum,
#                   'start_time': start_time, 'end_time': end_time}
#         print(params)
#         response = requests.get(url=url, params=params)
#         ret_data = json.loads(response.text)
#         print("--------------------")
#         print(ret_data)
#         meta = {
#             "msg": "切换成功",
#             "result": "OK"
#         }
#         backdata = {
#             "data": ret_data['data'],
#             "meta": meta,
#         }
#     except Exception as err:
#         log.info(err)
#         params = {'order_no': '', 'pagesize': pagesize, 'pagenum': pagenum,
#                   'start_time': start_time, 'end_time': end_time}
#         print(params)
#         response = requests.get(url=url, params=params)
#         ret_data = json.loads(response.text)
#         print("--------------------")
#         print(ret_data)
#         meta = {
#             "msg": str(err),
#             "result": "NG"
#         }
#         backdata = {
#             "data": ret_data['data'],
#             "meta": meta,
#         }
#     print(backdata)
#     return HttpResponse(List_Json(backdata))

# def ChangePlanOrder_btn_stand(request):
#     try:
#         myip = Getmyip()
#         url = 'http://' + str(myip) + ':9000/api/Order/Getorder_stand'
#         order_no = request.GET.get('order_no', '')
#         start_time = request.GET.get('start_time', '')
#         end_time = request.GET.get('end_time', '')
#         pagenum = request.GET.get('pagenum', '')
#         pagesize = request.GET.get('pagesize', '')
#
#         SQL = "SELECT * FROM planorder_stand_tab WHERE order_no = '" + order_no + "'"
#         data = easy_sql_reader(SQL)
#         if len(data) == 1:
#             if data[0]['status'] == "":
#                 #将切换前工单状态
#                 current_order_stand = cache.get('current_order_stand')
#                 SQL = "SELECT * FROM planorder_stand_tab WHERE order_no = '" + current_order_stand + "'"
#                 data = easy_sql_reader(SQL)
#                 if data[0]['status'] == "Start":
#                     SQL = "UPDATE planorder_stand_tab SET status = '' WHERE order_no = '" + current_order_stand + "'"
#                     if not sql_execute(SQL):
#                         raise Exception('SQL执行失败！')
#                 #更新切换后工单状态
#                 SQL = "UPDATE planorder_stand_tab SET status = 'Start' WHERE order_no = '" + order_no + "'"
#                 if not sql_execute(SQL):
#                     raise Exception('SQL执行失败！')
#                 Cache_writer('current_order_stand', order_no, None)
#                 #修改本地文件中当前订单信息
#                 filepath = GetFilePath("SoftWare.ini")
#                 conf = ConfigParser()  # 需要实例化一个ConfigParser对象
#                 conf.read(filepath)  # 需要添加上config.ini的路径，不需要open打开，直接给文件路径就读取，也可以指定encoding='utf-8'
#                 print(conf['CommonUse']['currentorder_stand'])
#                 conf.set('CommonUse', 'currentorder_stand', order_no)
#                 with open(filepath, 'w', encoding='utf-8') as f:
#                     conf.write(f)
#                 print(conf['CommonUse']['currentorder_stand'])
#             elif data[0]['status'] == "Close":
#                 raise Exception('已经关闭的工单不可使用')
#             elif data[0]['status'] == "Start":
#                 raise Exception('此工单已经开始')
#
#         else:
#             raise Exception('切换失败,未找到该工单,请检查')
#
#         params = {'order_no': '', 'pagesize': pagesize, 'pagenum': pagenum,
#                   'start_time': start_time, 'end_time': end_time}
#         print(params)
#         response = requests.get(url=url, params=params)
#         ret_data = json.loads(response.text)
#         print("--------------------")
#         print(ret_data)
#         meta = {
#             "msg": "切换成功",
#             "result": "OK"
#         }
#         backdata = {
#             "data": ret_data['data'],
#             "meta": meta,
#         }
#     except Exception as err:
#         log.info(err)
#         params = {'order_no': '', 'pagesize': pagesize, 'pagenum': pagenum,
#                   'start_time': start_time, 'end_time': end_time}
#         print(params)
#         response = requests.get(url=url, params=params)
#         ret_data = json.loads(response.text)
#         print("--------------------")
#         print(ret_data)
#         meta = {
#             "msg": str(err),
#             "result": "NG"
#         }
#         backdata = {
#             "data": ret_data['data'],
#             "meta": meta,
#         }
#     print(backdata)
#     return HttpResponse(List_Json(backdata))
# 每日开班检查 时间非当天为开班，返回True
def Start_check(t):
    log.info(">>>>>>>>Start_check")
    SQL = "SELECT * FROM mom_setting"
    data = SQL_function3(SQL)
    t_year = t.year - datetime.datetime.strptime(data[0]['datetime'], '%Y-%m-%d %H:%M:%S').year
    t_month = t.month - datetime.datetime.strptime(data[0]['datetime'], '%Y-%m-%d %H:%M:%S').month
    if t_year == 0 and t_month == 0:
        t_day = t.day - datetime.datetime.strptime(data[0]['datetime'], '%Y-%m-%d %H:%M:%S').day
    else:
        t_day = 1
    if not t_day >= 1:
        return False
    else:
        return True
def ChangePlanOrder_btn(request):
    try:
        log.info(">>>>>>>>ChangePlanOrder_btn")
        myip = Getmyip()
        url = 'http://' + str(myip) + ':9000/api/Order/Getorder'
        order_no = request.GET.get('order_no', '')
        start_time = request.GET.get('start_time', '')
        end_time = request.GET.get('end_time', '')
        pagenum = request.GET.get('pagenum', '')
        pagesize = request.GET.get('pagesize', '')
        t = datetime.datetime.now()
        current_order = cache.get('current_order')
        current_order_stand = cache.get('current_order_stand')

        SQL = "SELECT * FROM planorder_tab WHERE order_no = '" + order_no + "'"
        data = SQL_function3(SQL)

        part_no = data[0]['part_no']
        sn_num = data[0]['sn_num']

        if len(data) == 1:
            if data[0]['status'] == "":
                # 将切换前工单状态保存
                SQL = "SELECT * FROM planorder_tab WHERE order_no = '" + current_order + "'"
                data = SQL_function3(SQL)
                if data[0]['status'] == "Start" or data[0]['status'] == "Close":
                    # 更新sn_num数量
                    t_year = t.year - datetime.datetime.strptime(data[0]['datetime'], '%Y-%m-%d %H:%M:%S').year
                    t_month = t.month - datetime.datetime.strptime(data[0]['datetime'], '%Y-%m-%d %H:%M:%S').month
                    if t_year == 0 and t_month == 0:
                        t_day = t.day - datetime.datetime.strptime(data[0]['datetime'], '%Y-%m-%d %H:%M:%S').day
                    else:
                        t_day = 1
                    log.info("t_day:" + str(t_day))
                    # 如果是当天已经生产的工单，就同步最新sn_num数据到工单中。否则就清空当前工单的sn_num数据
                    if not t_day >= 1:
                        SQL = "UPDATE mom_setting,planorder_tab set planorder_tab.sn_num = mom_setting.sn_num where planorder_tab.order_no = '" + current_order + "'"
                        if not SQL_function4(SQL):
                            raise Exception('SQL Fail执行失败！')
                    else:
                        SQL = "UPDATE mom_setting,planorder_tab set planorder_tab.sn_num = '0' where planorder_tab.order_no = '" + current_order + "'"
                        if not SQL_function4(SQL):
                            raise Exception('SQL Fail执行失败！')
                    if data[0]['status'] == "Start":
                        SQL = "UPDATE planorder_tab SET status = '',datetime = '" + str(
                            t) + "' WHERE order_no = '" + current_order + "'"
                        if not SQL_function4(SQL):
                            raise Exception('SQL执行失败！')

                # 检查对比当天同型号的工单
                today_samemodel_tag = False
                today_samemodel_orderno = ""
                SQL = "SELECT * FROM planorder_tab "
                data_today = easy_sql_reader(SQL)
                for it in data_today:
                    day_temp = t.day - datetime.datetime.strptime(it['datetime'], '%Y-%m-%d %H:%M:%S').day
                    month_temp = t.month - datetime.datetime.strptime(it['datetime'], '%Y-%m-%d %H:%M:%S').month
                    year_temp = t.year - datetime.datetime.strptime(it['datetime'], '%Y-%m-%d %H:%M:%S').year
                    if month_temp == 0 and year_temp == 0:
                        if day_temp < 1 and it['part_no'] == part_no and not it['order_no'] == order_no:
                            today_samemodel_orderno = it['order_no']
                            if int(sn_num) < int(it['sn_num']):
                                today_samemodel_tag = True
                                break

                # 更新切换后工单状态
                # 恢复新工单sn_num数量至mom_setting中
                SQL = "SELECT * FROM planorder_tab WHERE order_no = '" + order_no + "'"
                data = SQL_function3(SQL)
                t_year = t.year - datetime.datetime.strptime(data[0]['datetime'], '%Y-%m-%d %H:%M:%S').year
                t_month = t.month - datetime.datetime.strptime(data[0]['datetime'], '%Y-%m-%d %H:%M:%S').month
                if t_year == 0 and t_month == 0:
                    t_day = t.day - datetime.datetime.strptime(data[0]['datetime'], '%Y-%m-%d %H:%M:%S').day
                else:
                    t_day = 1
                # 如果切换到当天的工单,每日开班切换工单时不用修改sn_num,镭雕机第一次申请sn时会自动归0
                if not t_day >= 1:
                    if not Start_check(t):
                        SQL = "UPDATE mom_setting,planorder_tab set mom_setting.sn_num = planorder_tab.sn_num where planorder_tab.order_no = '" + order_no + "'"
                        if not SQL_function4(SQL):
                            raise Exception('SQL执行失败！')
                else:
                    if not Start_check(t):
                        SQL = "UPDATE mom_setting,planorder_tab set mom_setting.sn_num = '0',planorder_tab.sn_num = '0' where planorder_tab.order_no = '" + order_no + "'"
                        if not SQL_function4(SQL):
                            raise Exception('SQL执行失败！')
                    else:
                        SQL = "UPDATE planorder_tab set planorder_tab.sn_num = '0' where planorder_tab.order_no = '" + order_no + "'"
                        if not SQL_function4(SQL):
                            raise Exception('SQL执行失败！')

                # 如果同型号的工单有当天的生产记录，延续上一同型号工单的sn_num计数
                if today_samemodel_tag:
                    SQL = "UPDATE mom_setting,planorder_tab set mom_setting.sn_num = planorder_tab.sn_num where planorder_tab.order_no = '" + today_samemodel_orderno + "'"
                    if not SQL_function4(SQL):
                        raise Exception('SQL执行失败！')

                # 修改本地文件中当前订单信息
                filepath = GetFilePath("SoftWare.ini")
                conf = ConfigParser()  # 需要实例化一个ConfigParser对象
                conf.read(filepath)  # 需要添加上config.ini的路径，不需要open打开，直接给文件路径就读取，也可以指定encoding='utf-8'
                print(conf['CommonUse']['Currentorder'])
                conf.set('CommonUse', 'Currentorder', order_no)
                with open(filepath, 'w', encoding='utf-8') as f:
                    conf.write(f)
                print(conf['CommonUse']['Currentorder'])

                # 更新工单信息
                SQL = "UPDATE planorder_tab SET status = 'Start',datetime = '" + str(
                    t) + "' WHERE order_no = '" + order_no + "'"
                if not SQL_function4(SQL):
                    raise Exception('SQL执行失败！')
                Cache_writer('current_order', order_no, None)

            elif data[0]['status'] == "Close":
                raise Exception('已经关闭的工单不可使用')
            elif data[0]['status'] == "Start":
                raise Exception('此工单已经开始')

        else:
            raise Exception('切换失败,未找到该工单,请检查')

        params = {'order_no': '', 'pagesize': pagesize, 'pagenum': pagenum,
                  'start_time': start_time, 'end_time': end_time}
        print(params)
        response = requests.get(url=url, params=params)
        ret_data = json.loads(response.text)
        print("--------------------")
        print(ret_data)
        meta = {
            "msg": "切换成功",
            "result": "OK"
        }
        backdata = {
            "data": ret_data['data'],
            "meta": meta,
        }
    except Exception as err:
        log.info(">>>>>>>>ChangePlanOrder_btn ERROR: " + str(err))
        params = {'order_no': '', 'pagesize': pagesize, 'pagenum': pagenum,
                  'start_time': start_time, 'end_time': end_time}
        print(params)
        response = requests.get(url=url, params=params)
        ret_data = json.loads(response.text)
        print("--------------------")
        print(ret_data)
        meta = {
            "msg": str(err),
            "result": "NG"
        }
        backdata = {
            "data": ret_data['data'],
            "meta": meta,
        }
    print(backdata)
    return HttpResponse(List_Json(backdata))
def ChangePlanOrder_btn_stand(request):
    try:
        myip = Getmyip()
        url = 'http://' + str(myip) + ':9000/api/Order/Getorder_stand'
        order_no = request.GET.get('order_no', '')
        start_time = request.GET.get('start_time', '')
        end_time = request.GET.get('end_time', '')
        pagenum = request.GET.get('pagenum', '')
        pagesize = request.GET.get('pagesize', '')
        t = datetime.datetime.now()

        SQL = "SELECT * FROM planorder_stand_tab WHERE order_no = '" + order_no + "'"
        data = easy_sql_reader(SQL)

        part_no = data[0]['part_no']
        sn_num = data[0]['sn_num_stand']

        if len(data) == 1:
            if data[0]['status'] == "":
                # 将切换前工单状态
                current_order_stand = cache.get('current_order_stand')
                SQL = "SELECT * FROM planorder_stand_tab WHERE order_no = '" + current_order_stand + "'"
                data = SQL_function3(SQL)
                if data[0]['status'] == "Start" or data[0]['status'] == "Close":
                    # 更新sn_num数量
                    t_year = t.year - datetime.datetime.strptime(data[0]['datetime'], '%Y-%m-%d %H:%M:%S').year
                    t_month = t.month - datetime.datetime.strptime(data[0]['datetime'], '%Y-%m-%d %H:%M:%S').month
                    if t_year == 0 and t_month == 0:
                        t_day = t.day - datetime.datetime.strptime(data[0]['datetime'], '%Y-%m-%d %H:%M:%S').day
                    else:
                        t_day = 1
                    print(t_day)
                    # 如果是当天已经生产的工单，就同步最新sn_num数据到工单中。否则就清空当前工单的sn_num数据
                    if not t_day >= 1:
                        SQL = "UPDATE mom_setting,planorder_stand_tab set planorder_stand_tab.sn_num_stand = mom_setting.sn_num_stand where planorder_stand_tab.order_no = '" + current_order_stand + "'"
                        if not SQL_function4(SQL):
                            raise Exception('SQL执行失败！')
                    else:
                        SQL = "UPDATE mom_setting,planorder_stand_tab set planorder_stand_tab.sn_num_stand = '0' where planorder_stand_tab.order_no = '" + current_order_stand + "'"
                        if not SQL_function4(SQL):
                            raise Exception('SQL执行失败！')
                    if data[0]['status'] == "Start":
                        SQL = "UPDATE planorder_stand_tab SET status = '',datetime = '" + str(
                            t) + "' WHERE order_no = '" + current_order_stand + "'"
                        if not SQL_function4(SQL):
                            raise Exception('SQL执行失败！')
                # 检查对比当天同型号的工单
                today_samemodel_tag = False
                today_samemodel_orderno = ""
                SQL = "SELECT * FROM planorder_stand_tab "
                data_today = easy_sql_reader(SQL)
                for it in data_today:
                    day_temp = t.day - datetime.datetime.strptime(it['datetime'], '%Y-%m-%d %H:%M:%S').day
                    month_temp = t.month - datetime.datetime.strptime(it['datetime'], '%Y-%m-%d %H:%M:%S').month
                    year_temp = t.year - datetime.datetime.strptime(it['datetime'], '%Y-%m-%d %H:%M:%S').year
                    if month_temp == 0 and year_temp == 0:
                        if day_temp < 1 and it['part_no'] == part_no and not it['order_no'] == order_no:
                            today_samemodel_orderno = it['order_no']
                            if sn_num < it['sn_num_stand']:
                                today_samemodel_tag = True
                                break

                # 更新切换后工单状态
                # 恢复新工单sn_num数量至mom_setting中
                SQL = "SELECT * FROM planorder_stand_tab WHERE order_no = '" + order_no + "'"
                data = SQL_function3(SQL)
                t_year = t.year - datetime.datetime.strptime(data[0]['datetime'], '%Y-%m-%d %H:%M:%S').year
                t_month = t.month - datetime.datetime.strptime(data[0]['datetime'], '%Y-%m-%d %H:%M:%S').month
                if t_year == 0 and t_month == 0:
                    t_day = t.day - datetime.datetime.strptime(data[0]['datetime'], '%Y-%m-%d %H:%M:%S').day
                else:
                    t_day = 1
                # 如果切换到当天的工单,每日开班切换工单时不用修改sn_num,镭雕机第一次申请sn时会自动归0
                if not t_day >= 1:
                    if not Start_check(t):
                        SQL = "UPDATE mom_setting,planorder_stand_tab set mom_setting.sn_num_stand = planorder_stand_tab.sn_num_stand where planorder_stand_tab.order_no = '" + order_no + "'"
                        if not SQL_function4(SQL):
                            raise Exception('SQL执行失败！')
                else:
                    if not Start_check(t):
                        SQL = "UPDATE mom_setting,planorder_stand_tab set mom_setting.sn_num_stand = '0',planorder_stand_tab.sn_num_stand = '0' where planorder_stand_tab.order_no = '" + order_no + "'"
                        if not SQL_function4(SQL):
                            raise Exception('SQL执行失败！')
                    else:
                        SQL = "UPDATE planorder_stand_tab set planorder_stand_tab.sn_num_stand = '0' where planorder_stand_tab.order_no = '" + order_no + "'"
                        if not SQL_function4(SQL):
                            raise Exception('SQL执行失败！')

                # 如果同型号的工单有当天的生产记录，延续该工单的sn_num计数
                if today_samemodel_tag:
                    SQL = "UPDATE mom_setting,planorder_stand_tab set mom_setting.sn_num_stand = planorder_stand_tab.sn_num_stand where planorder_stand_tab.order_no = '" + today_samemodel_orderno + "'"
                    if not SQL_function4(SQL):
                        raise Exception('SQL执行失败！')

                SQL = "UPDATE planorder_stand_tab SET status = 'Start',datetime = '" + str(
                    t) + "' WHERE order_no = '" + order_no + "'"
                if not SQL_function4(SQL):
                    raise Exception('SQL执行失败！')
                Cache_writer('current_order_stand', order_no, None)
                # 修改本地文件中当前订单信息
                filepath = GetFilePath("SoftWare.ini")
                conf = ConfigParser()  # 需要实例化一个ConfigParser对象
                conf.read(filepath)  # 需要添加上config.ini的路径，不需要open打开，直接给文件路径就读取，也可以指定encoding='utf-8'
                print(conf['CommonUse']['Currentorder_stand'])
                conf.set('CommonUse', 'Currentorder_stand', order_no)
                with open(filepath, 'w', encoding='utf-8') as f:
                    conf.write(f)
                print(conf['CommonUse']['Currentorder_stand'])
            elif data[0]['status'] == "Close":
                raise Exception('已经关闭的工单不可使用')
            elif data[0]['status'] == "Start":
                raise Exception('此工单已经开始')

        else:
            raise Exception('切换失败,未找到该工单,请检查')

        params = {'order_no': '', 'pagesize': pagesize, 'pagenum': pagenum,
                  'start_time': start_time, 'end_time': end_time}
        print(params)
        response = requests.get(url=url, params=params)
        ret_data = json.loads(response.text)
        print("--------------------")
        print(ret_data)
        meta = {
            "msg": "切换成功",
            "result": "OK"
        }
        backdata = {
            "data": ret_data['data'],
            "meta": meta,
        }
    except Exception as err:
        log.info(">>>>>>>>ChangePlanOrder_btn_stand ERROR: " + str(err))
        params = {'order_no': '', 'pagesize': pagesize, 'pagenum': pagenum,
                  'start_time': start_time, 'end_time': end_time}
        print(params)
        response = requests.get(url=url, params=params)
        ret_data = json.loads(response.text)
        print("--------------------")
        print(ret_data)
        meta = {
            "msg": str(err),
            "result": "NG"
        }
        backdata = {
            "data": ret_data['data'],
            "meta": meta,
        }
    print(backdata)
    return HttpResponse(List_Json(backdata))


# 内存泄露测试
last_snapshot = None
start_snapshot = None

import gc
import tracemalloc

def begin_show(request):
    """
    刚启动程序时执行，记录下创世内存快照
    """
    tracemalloc.start()

    global last_snapshot
    global start_snapshot
    last_snapshot = None

    start_snapshot = tracemalloc.take_snapshot()
    return HttpResponse("ok", content_type="application/json")


def show(request):
    """
    用当前快照分别跟上次快照，创世快照对比，找出没释放的内存差值
    """
    dump_string = ""
    try:
        gc.collect()  # 在快照之前手动回收，确保差值
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics('lineno')

        global last_snapshot
        global start_snapshot
        if last_snapshot:

            dump_string += "\n>>>>>>compare to last:\n"
            top_stats = snapshot.compare_to(last_snapshot, 'lineno')
            for stat in top_stats[:50]:
                dump_string += "%s\n" % stat

        dump_string += "\n>>>>>>current shot:\n"
        for stat in top_stats[:50]:
            dump_string += "%s\n" % stat

        if start_snapshot:

            dump_string += "\n>>>>>>compare to start:\n"
            top_stats = snapshot.compare_to(start_snapshot, 'lineno')
            for stat in top_stats[:50]:
                dump_string += "%s\n" % stat

        last_snapshot = snapshot


    except Exception as e:
        dump_string += "%s\n" % str(e)

    return HttpResponse(dump_string, content_type="application/json")

def clean_ram(request):
    try:
        dump_string = Ram_clean()
    except Exception as e:
        dump_string = "%s\n" % str(e)

    return HttpResponse(dump_string, content_type="application/json")

def sql_test(request):
    thread_name("sql_test")
    SQL = "SELECT * FROM sta_total"
    data = my_sql_test(SQL)
    return HttpResponse(data, content_type="application/json")
