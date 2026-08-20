import configparser
import os.path

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
from django.core.cache import cache

from COMMON.getmqtt import *
from django.db import transaction
import uuid
import time
import datetime
from django.http import StreamingHttpResponse

def stream(request):
    print("stream views:")
    def event_stream():
        while True:
            time.sleep(3)
            yield 'data: The server time is: %s\n\n' % datetime.datetime.now()

    return StreamingHttpResponse(event_stream(), content_type='text/event-stream')

def test(request):
    print("test")
    equip_connect = cache.get('EquipConnect')
    print(equip_connect)
    if equip_connect is None:
        equip_connect = {}
        equip_connect['test'] = "127.0.0.9:9999"
    cache.set('EquipConnect', equip_connect)

@csrf_exempt
def login(request):
    # print(request.POST.get('username', None))
    # print(request.POST.get('password', None))
    print(request.POST)
    """登录验证"""
    if request.method == 'POST':
        try:
            ascii_values = ""
            request.POST.get('username', None)
            for character in request.POST.get("password", None):
                ascii_values += str(ord(character))
            SQL = " select ID,userid from employee_tab WHERE userid='" + request.POST.get('username', None) + "'"
            # cs = connections['aview'].cursor()
            print(SQL)
            cs = connection.cursor()

            cs.execute(SQL)
            data = cs.fetchone()
            cs.close()
            print(data)
            if data:
                SQL = " select ID,userid,password,level from employee_tab WHERE userid='" + request.POST.get('username',
                                                                                                             None) + "'" \
                                                                                                                     " and password='" + ascii_values + "'"

                print(SQL)
                data = sql_list_first(SQL)
                print(data)
                cs.close()
                if data:
                    print(111)
                    b = {'username': request.POST.get('username'), 'password': request.POST.get('password')}
                    token = "Bearer " + jwt.encode(b, 'sercet', algorithm='HS256')
                    # 用户名和密码都满足，保存token到表中
                    user_uuid = uuid.uuid1().hex
                    print(user_uuid)
                    user_cache = {
                        "userid": data[0],
                        "username": request.POST.get('username'),
                        "level": data[3]
                    }
                    cache.set(user_uuid, List_Json(user_cache))
                    a = cache.get(user_uuid, default=None)
                    print(">>>>>")
                    print(json.loads(a))
                    Data = {
                        "username": request.POST.get('username'),
                        "password": request.POST.get('password'),
                        "token": token,
                        "level": data[3],
                        "uuid": user_uuid
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
                    # 初始化全局变量
                    GolbalGroup_Ini()

                    return HttpResponse(List_Json(backdata))

                else:
                    Data = {
                        "username": request.POST.get('username'),
                        "password": request.POST.get('password'),
                        "token": "",
                        "level": " ",
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
            print(err)
    else:
        if request.session.get('username', None) == None:
            return redirect('/')
        else:
            return render(request, 'login.html')


@csrf_exempt
def main(request):
    try:
        user_uuid = request.GET.get('uuid', '')
        print(">>>>>")
        print(user_uuid)

        print(cache.get(user_uuid, default=None))
        if cache.get(user_uuid, default=None) == None:
            Data = {

            }
            meta = {
                "msg": "获取菜单列表失败:uuid不存在",
                "result": "NG"
            }

            backdata = {
                "data": Data,
                "meta": meta,
            }
            return HttpResponse(json.dumps(backdata, ensure_ascii=False))
        cache.touch(user_uuid)
        user_cache = json.loads(cache.get(user_uuid, default=None))
        if user_cache['level'] == "1":
            print("1")

        groups = group.objects.all().filter(group_main_id="0")
        menus = menu.objects.all()
        i = 0
        menu_chk = []
        r_arr = []
        menulist = []
        for o in groups:
            temp = model_to_dict(o)
            menulist.append(temp)
        # print(menulist)
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
        print(Data)

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


@csrf_exempt
def local_users(request):
    try:
        loginName = request.GET.get('loginName', '')
        if (loginName == 'administrator'):
            SQL = " select ID,userid,password,level from employee_tab"
        else:
            SQL = " select ID,userid,password,level from employee_tab WHERE userid='" + loginName + "'"

        print(SQL)

        data = easy_sql_reader(SQL)

        print(data)
        meta = {
            "msg": "查询成功!",
            "result": "OK"
        }
        backdata = {
            "data": data,
            "meta": meta,
        }

        print(backdata)

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

        print(SQL)

        data = aview_easy_sql_reader_page1(SQL, pagenum, pagesize)
        # print(data)
        meta = {
            "msg": "获取用户列表成功!",
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
@csrf_exempt
def devices(request):
    try:
        query = request.GET.get('query', '')
        pagenum = request.GET.get('pagenum', '')
        pagesize = request.GET.get('pagesize', '')

        SQL = "select id,equipment_name,equipment_num,equipment_ip,equipment_serial from equipment_tab"
        if len(query) != 0:
            SQL += " WHERE equipment_name like '%" + query + "%'"

        print(SQL)

        data = aview_easy_sql_reader_page1(SQL, pagenum, pagesize)
        print(data)
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


# --------------------------------删除设备列表----------------------------

@csrf_exempt
def DeleteDevice(request):
    try:
        print('###########################')
        print(request)
        id = request.POST.get('id', '')
        name = request.POST.get('name', '')

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
            cache.set('Equip_Status', equip_status, None)

            # DeviceClass
            device_class = cache.get('DeviceClass')
            print(">>>>>>")
            print(device_class)
            for i in range(len(device_class)):
                if device_class[i]['EquipName'] == name:
                    device_class.pop(i)
                    break
            print(device_class)
            cache.set('DeviceClass', device_class, None)

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


# --------------------------------添加设备列表----------------------------

@csrf_exempt
def AddDevice(request):
    try:
        Data = {}
        meta = {}
        print(request)
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
        SQL = "select id from equipment_tab where equipment_name='" + equipment_name + "' or equipment_num='" + equipment_num + "'or equipment_ip='" + equipment_ip + "'or equipment_serial='" + equipment_serial + "'"
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
        print(request)
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

        for key, value in re_list.items():
            if value != "":
                SQL = "select id from equipment_tab where  " + key + "='" + value + "' and id != '" + id + "'"
                # print(SQL)
                data1 = sql_list_first(SQL)
                if data1:
                    raise Exception("设备已经包含重复属性" + value + "！！！")

                else:
                    First_list[key] = value
                    # print(First_list)

        SQL = "select equipment_name from equipment_tab where id='" + str(id) + "'"
        data1 = sql_list_first(SQL)
        # print(data1)
        for key, value in First_list.items():
            SQL = "UPDATE equipment_tab SET " + key + "='" + value + "' WHERE id=" + id + ""
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
        if cache.get('current_model') == result[0][0]:
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
            cache.set('Equip_Status', equip_status, None)
            print(cache.get('Equip_Status'))

            # DeviceClass
            device_class = cache.get('DeviceClass')
            print(">>>>>>>>DeviceClass")
            print(device_class)
            for it in device_class:
                if it['EquipName'] == data1[0]:
                    it['EquipName'] = equipment_name
                    it['EquipNumber'] = equipment_num
                    it['EquipIP'] = equipment_ip
                    it['EquipSerial'] = equipment_serial
            cache.set('DeviceClass', device_class, None)
            print(cache.get('DeviceClass'))

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


# ---------------------------------设备控制------------------------------

# --------------获取型号&设备列表-------------------
def GetLocalModel_Equipment(request):
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
        SQL = "SELECT equipment_name, equipment_num, equipment_ip, equipment_serial FROM station_tab WHERE gp_model ='" + current_model + "'"
        cs = connection.cursor()
        cs.execute(SQL)
        result = cs.fetchall()
        cs.close()
        device_class = cache.get('DeviceClass')
        for it in result:
            back_data_list.append(
                {"equipment_name": it[0], "equipment_num": it[1], "equipment_ip": it[2], "equipment_serial": it[3],
                 "equipStatus": False, "equipOrder": "NA", "equipResult": "NA"})

        for it1 in device_class:
            if it1["EquipStatus"] is True:
                for it2 in back_data_list:
                    if it1["EquipName"] == it2["equipment_name"]:
                        it2["equipStatus"] = True

        back_data = {
            "localmodel": current_model,
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


# --------------功能按钮-------------------
def Function_Btn(request):
    # from django.core.cache import cache
    try:
        back_data = {}
        back_meta = {
            "msg": "操作成功",
            "result": "OK"
        }
        type_name = request.POST.get('Function_Type', '')
        match type_name:
            case "0":
                print("start")
                # 发送信息给station   SendToStation()
            case "1":
                print("stop")
                # 发送信息给station   SendToStation()
            case "2":
                print("reset")
                # 发送信息给station   SendToStation()
            case "3":
                print("clean")
                # 发送信息给station   SendToStation()
            case "":
                print("error")
                back_meta = {
                    "msg": "错误：未识别操作字符，为空字符串",
                    "result": "NG"
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


# --------------换型-------------------
def Remodel(request):
    try:
        print("Remodel>>>>>>>>>>>")
        print(request.GET.get('selectvalue'))
        back_data = {}
        # back_data_list = []
        back_meta = {}
        Selected_Model = request.GET.get('Selected_Model', '')
        Condition = request.GET.get('Condition').upper()
        equip_status = cache.get('Equip_Status', default=None)
        equip_connect = cache.get('EquipConnect', default=None)
        device_class = cache.get('DeviceClass', default=None)
        print(Selected_Model)

        if Condition == "YES":
            print("YES>>>>>>>>>>>")
            back_data = {}
            back_data_list = []
            back_meta = {}
            Selected_Model = request.GET.get('selectvalue', '')
            current_model = cache.get('current_model')
            if current_model == Selected_Model:
                print("换型型号与当前运行型号相同")
                back_meta = {
                    "msg": "换型型号与当前运行型号相同",
                    "result": "NG"
                }
                backdata = {
                    "data": back_data,
                    "meta": back_meta,
                }
                return HttpResponse(List_Json(backdata))
            if Selected_Model == '':
                print("Selected_Model为空")
                back_meta = {
                    "msg": "Selected_Model为空",
                    "result": "NG"
                }
                backdata = {
                    "data": back_data,
                    "meta": back_meta,
                }
                return HttpResponse(List_Json(backdata))

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

            # 修改current_model的内存和本地信息
            cache.set('current_model', Selected_Model, None)
            filepath = GetFilePath("SoftWare.ini")
            conf = ConfigParser()  # 需要实例化一个ConfigParser对象
            conf.read(filepath)  # 需要添加上config.ini的路径，不需要open打开，直接给文件路径就读取，也可以指定encoding='utf-8'
            print(conf['CommonUse']['CurrentModel'])
            conf.set('CommonUse', 'CurrentModel', str(Selected_Model))
            with open(filepath, 'w', encoding='utf-8') as f:
                conf.write(f)
            print(conf['CommonUse']['CurrentModel'])

            # 修改换型后设备各种变量信息
            print("------INI")
            GolbalGroup_Ini()
            print("------INI")

            # 修改equip_status中Order信息
            equip_status = cache.get('Equip_Status', default=None)
            equip_connect = cache.get('EquipConnect', default=None)
            device_class = cache.get('DeviceClass', default=None)

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
                it["EquipOrder"] = "ReModel"
                it["EquipResult"] = "NA"
            cache.set('Equip_Status', equip_status, None)

            # 对比EquipConnect  DeviceClass
            for it1 in equip_connect:
                for it2 in device_class:
                    if (it1 == it2.EquipIP):
                        it2.EquipStatus = True
            cache.set('DeviceClass', device_class, None)
            # back_data_list 状态同步
            for it in device_class:
                data = {
                    "equipment_name": it["EquipName"], "equipment_num": it["EquipNumber"],
                    "equipOrder": "ReModel", "equipResult": "NA",
                    "equipStatus": it["EquipStatus"]
                }
                back_data_list.append(data)

            back_data = {
                "localmodel": Selected_Model,
                "data": back_data_list,
                "table": [{"ProductSum": "", "ProductQuantity": "", "Accept": "", "Yield": ""}]
            }
            back_meta = {
                "msg": "换型成功",
                "result": "OK"
            }
            backdata = {
                "data": back_data,
                "meta": back_meta,
            }
            print(backdata)
            return HttpResponse(List_Json(backdata))

        elif Condition == "NO":
            equiplist = request.GET.get('EquipList', '')
            SQL = "SELECT * FROM station_tab WHERE gp_model = '" + Selected_Model + "'"
            print(SQL)
            data = easy_sql_reader(SQL)

            # Device_Connect_Class
            Device_Connect_Class = Device_Connect_Select(Selected_Model, data)

            for it1 in Device_Connect_Class:
                ret = False
                for it2 in equiplist:
                    if it1["EquipIP"] == it2["EquipIP"]:
                        ret = True
                        break
                if ret is False:
                    Device_Connect_Class.remove(it1)

            if equiplist == '':
                print("EquipList为空")
                back_meta = {
                    "msg": "EquipList为空",
                    "result": "OK"
                }
                backdata = {
                    "data": back_data,
                    "meta": back_meta,
                }
                print(backdata)
                return HttpResponse(List_Json(backdata))

            back_meta = {
                "msg": "换型成功",
                "result": "OK"
            }
            backdata = {
                "data": back_data,
                "meta": back_meta,
            }
            print(backdata)
            return HttpResponse(List_Json(backdata))

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


# --------------一键换型-------------------
def QuickRemodel(request):
    print("QuickRemodel>>>>>>>>>>>")
    print(request.GET.get('selectvalue'))
    try:
        back_data = {}
        back_data_list = []
        back_meta = {}
        Selected_Model = request.GET.get('selectvalue', '')
        current_model = cache.get('current_model')
        if current_model == Selected_Model:
            print("换型型号与当前运行型号相同")
            back_meta = {
                "msg": "换型型号与当前运行型号相同",
                "result": "NG"
            }
            backdata = {
                "data": back_data,
                "meta": back_meta,
            }
            return HttpResponse(List_Json(backdata))
        if Selected_Model == '':
            print("Selected_Model为空")
            back_meta = {
                "msg": "Selected_Model为空",
                "result": "NG"
            }
            backdata = {
                "data": back_data,
                "meta": back_meta,
            }
            return HttpResponse(List_Json(backdata))

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
        for it in device_class:
            if not it["EquipStatus"]:
                back_meta = {
                    "msg": "全自动状态才可使用此功能",
                    "result": "NG"
                }
                backdata = {
                    "data": back_data,
                    "meta": back_meta,
                }
                print("全自动状态才可使用此功能")
                return HttpResponse(List_Json(backdata))
        cache.set('ModelSetFlag', 1, None)
        # 修改current_model的内存和本地信息
        cache.set('current_model', Selected_Model, None)
        filepath = GetFilePath("SoftWare.ini")
        conf = ConfigParser()  # 需要实例化一个ConfigParser对象
        conf.read(filepath)  # 需要添加上config.ini的路径，不需要open打开，直接给文件路径就读取，也可以指定encoding='utf-8'
        print(conf['CommonUse']['CurrentModel'])
        conf.set('CommonUse', 'CurrentModel', str(Selected_Model))
        with open(filepath, 'w', encoding='utf-8') as f:
            conf.write(f)
        print(conf['CommonUse']['CurrentModel'])

        # 向第一台机器下发换型信息
        # device_class = cache.get('DeviceClass', default=None)
        remodel_send = {
            "Command": " 0x05",
            "Gp_Model": Selected_Model
        }
        # publish("commands/msg/" + str(device_class[0]["EquipIP"]), json.loads(remodel_send))
        # 修改换型后设备各种变量信息
        print("------INI")
        GolbalGroup_Ini()
        print("------INI")
        # 修改equip_status中Order信息
        equip_status = cache.get('Equip_Status', default=None)
        equip_connect = cache.get('EquipConnect', default=None)
        device_class = cache.get('DeviceClass', default=None)

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
            it["EquipOrder"] = "ReModel"
            it["EquipResult"] = "NA"
        cache.set('Equip_Status', equip_status, None)

        # 对比EquipConnect  DeviceClass
        for it1 in equip_connect:
            for it2 in device_class:
                if (it1 == it2.EquipIP):
                    it2.EquipStatus = True
        cache.set('DeviceClass', device_class, None)
        # back_data_list 状态同步
        for it in device_class:
            data = {
                "equipment_name": it["EquipName"], "equipment_num": it["EquipNumber"],
                "equipOrder": "ReModel", "equipResult": "NA",
                "equipStatus": it["EquipStatus"]
            }
            back_data_list.append(data)

        back_data = {
            "localmodel": Selected_Model,
            "data": back_data_list,
            "table": [{"ProductSum": "", "ProductQuantity": "", "Accept": "", "Yield": ""}]
        }
        back_meta = {
            "msg": "换型成功",
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
    # publish("commands/msg", json.loads(backdata))
    # print(rc)
    # print(mid)
    return HttpResponse(List_Json(backdata))


# ---------------------------------型号管理------------------------------

@csrf_exempt
def models(request):
    try:
        SQL = "select id,gp_model from model_tab"
        # data1 = sql_list_first(SQL)
        data = easy_sql_reader(SQL)
        print(data)
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

@transaction.atomic
@csrf_exempt
def AddModels(request):
    try:
        meta = {}
        print(request.POST)
        data = request.POST.get('data', '')
        print(data)
        data = json.loads(data)
        print(type(data))
        print(data[0])

        xinghao = request.POST.get('xinghao', '')
        SQL = "SELECT gp_model FROM model_tab WHERE gp_model = '" + xinghao + "'"
        print(SQL)
        cs = connection.cursor()
        cs.execute(SQL)
        result = cs.fetchall()
        cs.close()
        print(result)
        if len(result) > 0:
            print("已经存在" + str(xinghao) + "无法添加")
            meta = {
                "msg": "型号已经存在 无法添加",
                "result": "NG"
            }
        elif len(result) == 0:
            SQL = "INSERT INTO model_tab(gp_model,Pass,Fail)VALUES ('" + xinghao + "',0,0)"
            print(SQL)
            cs = connection.cursor()
            result = cs.execute(SQL)
            if result == 1:
                for i in data:
                    SQL = "INSERT INTO station_tab(equipment_name,equipment_num,equipment_ip,equipment_serial,gp_model)VALUES ('" + \
                          i["equipment_name"] + "','" + i["equipment_num"] + "','" + i["equipment_ip"] + "','" + i[
                              "equipment_serial"] + "','" + xinghao + "')"
                    print(SQL)
                    result = cs.execute(SQL)
                    if result == 1:
                        meta = {
                            "msg": "添加型号管理成功!",
                            "result": "OK"
                        }
                    else:
                        meta = {
                            "msg": "SQL执行失败",
                            "result": "NG"
                        }
                        raise Exception('SQL执行失败！')
            else:
                meta = {
                    "msg": "SQL执行失败",
                    "result": "NG"
                }
                raise Exception('SQL执行失败！')

        backdata = {
            "data": xinghao,
            "meta": meta,
        }

        return HttpResponse(List_Json(backdata))

    except Exception as err:

        meta = {
            "msg": "添加型号管理失败",
            "result": "NG"
        }

        backdata = {
            "data": xinghao,
            "meta": meta,
        }
        print(err)
        return HttpResponse(List_Json(backdata))


# --------------------------------删除设备列表----------------------------

@csrf_exempt
def DeleteModel_Device(request):
    try:
        meta = {}
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
            cache.set('Equip_Status', equip_status, None)

            # DeviceClass
            device_class = cache.get('DeviceClass')
            print(">>>>>>")
            print(device_class)
            for i in range(len(device_class)):
                if device_class[i]['EquipName'] == result[0][1]:
                    device_class.pop(i)
                    break
            print(device_class)
            cache.set('DeviceClass', device_class, None)

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


# --------------------------------获取设备列表----------------------------
@csrf_exempt
def Modeldevices(request):
    try:
        query = request.GET.get('query', '')
        pagenum = request.GET.get('pagenum', '')
        pagesize = request.GET.get('pagesize', '')
        print(query)
        SQL = "select id,equipment_name,equipment_num,equipment_ip,equipment_serial from station_tab WHERE gp_model='" + query + "'"
        print(111)
        print(SQL)

        data = aview_easy_sql_reader_page1(SQL, pagenum, pagesize)
        print(data)
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

        # SQL = " delete from station_tab where equipment_name= '" + name + "' and gp_model='"+gpmodel+"'"
        print(SQL)
        if not sql_execute(SQL):
            raise Exception('SQL执行失败！')

        SQL = " delete from model_tab where gp_model= '" + gpmodel + "'"

        # SQL = " delete from station_tab where equipment_name= '" + name + "' and gp_model='"+gpmodel+"'"
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


# --------------------------------------------------料盘管理------------------------------------------

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


# ------------------------------删除料盘-----------------------------------------
def DeleteTray(request):
    try:
        back_data = ""
        back_meta = {}
        SQL = " DELETE FROM tray_tab WHERE trayno = '" + request.POST.get('trayno', '') + "'"
        print(SQL)
        cs = connection.cursor()
        cs.execute(SQL)
        cs.close()
        back_meta = {"msg": "删除成功", "result": "OK"}
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

    # -----------------------------------------生产追溯----------------------------------


# ----------------------查询产品号信息----------------------
@csrf_exempt
def ProInfo(request):
    try:

        flag = request.POST.get('flag', '')
        code = request.POST.get('code', '')
        # print(flag)
        # print(int(flag)==1)
        if int(flag) == 1:
            # print(flag)
            # 查找产品在工位的测试结果
            SQL = "select distinct B.equipment_name,B.equipment_num,A.id,A.serial_no, A.datetime,A.test_result, A.gp_model from qr_confrimation_tab A,station_tab B where A.station_no=B.equipment_num and A.serial_no='" + code + "' "
            data = easy_sql_reader(SQL)
            # print(SQL)
            # print(data)

        else:
            SQL = "select qr_code from qr_bind_tab where  pcba_code = '" + code + "'"
            data = sql_list_first(SQL)
            # print(data)
            # print(len(data))

            if len(data) != 1:
                raise Exception("没有找到绑定前端外壳代码")
            # print(data[0])
            SQL = "select distinct B.equipment_name,B.equipment_num,A.id, A.serial_no,A.datetime,A.test_result, A.gp_model from qr_confrimation_tab A,station_tab B where A.station_no=B.equipment_num and A.serial_no='" + \
                  data[0] + "' "
            # print(SQL)
            data = easy_sql_reader(SQL)

        meta = {
            "msg": "查询条码信息成功!",
            "result": "OK"
        }
        backdata = {
            "data": data,
            "meta": meta,
        }

        # print(backdata)

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
        return HttpResponse(json.dumps(backdata, ensure_ascii=False))

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

# -----------------------根据工位型号查询产品生产信息--------------------
def StaInfo(request):
    try:
        model = request.GET.get('model', '')
        sta = request.GET.get('sta', '')
        starttime = request.GET.get('starttime', '')
        endtime = request.GET.get('endtime', '')

        #
        # print(111)
        # print(sta)
        # print(starttime)
        # print(type(endtime))



        SQL = "SELECT station_no,SUM(tiaojian = 1) + SUM(tiaojian = 0) as total,SUM(tiaojian = 1) As good,SUM(tiaojian = 0) As ng " \
              "FROM (select station_no, CASE when test_result='OK' then 1  when test_result='NG' then 0 END AS tiaojian from qr_confrimation_tab " \
              "where station_no = '"+sta+"' and gp_model = '"+model+"' and datetime BETWEEN '"+starttime+"' and  '"+endtime+"')B  " \

        print(SQL)

        data = easy_sql_reader(SQL)
        # print(data)
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



@csrf_exempt
def DeleteProInfo(request):
    try:
        id = request.POST.get('id', '')
        model = request.POST.get('model', '')
        sn = request.POST.get('sn', '')
        station_no = request.POST.get('station_no', '')
        # print(id)
        # print(sn)
        # print(station_no)



        # 删除产品生产记录
        SQL = " delete  from qr_confrimation_tab where id= " + id + ""
        # print(SQL)
        if not sql_execute(SQL):
            raise Exception("删除在工位号"+station_no+ "的测试结果失败！")
        # 查询产品的工位测试结果
        SQL = "Select test_result from " + station_no+"_test_tab where serial_no='"+sn+"' and gp_model ='"+model+"'"
        # print(SQL)
        data=sql_list(SQL)
        # print(data)
        if len(data) != 1:
            raise Exception("查找产品在当前工位"+station_no+"的测试结果失败")
        # print(data)

        if data[0][0]=="NG":
            # 删除产品结果

            SQL = " Delete from product_statistics_tab where serial_no='"+sn+"' and gp_model='"+model+"'"
            if not sql_execute(SQL):
                raise Exception('删除产品在整线的测试结果失败！')
        # 删除对应工位数据表格的数据

        SQL = "delete  from "+ station_no+"_test_tab where serial_no = '"+sn+"' and station_no = '"+station_no+"' and gp_model = '"+model+"'"
        if not sql_execute(SQL):
            raise Exception('产品详细测试数据删除失败！')


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
            "msg": str(err),
            "result": "NG"
        }

        backdata = {
            "data": Data,
            "meta": meta,
        }
        print(err)
        return HttpResponse(List_Json(backdata))