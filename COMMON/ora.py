
import datetime

import django.db
# import logging
from django.db import connection, connections
# from MES.views import QStoJson,QStoJson2,QStoJson,QStoJson5,QStoJson6
import json
from configparser import ConfigParser
from django.core.cache import cache
from COMMON.logBasic import logger
import threading
log = logger

lock_sql = threading.Lock()


# def get_database_connection(timeout=None):
#     """
#     获取数据库连接对象，并设置超时时间
#     :param timeout: 超时时间（秒）
#     :return: 数据库连接对象
#     """
#     try:
#         # 获取数据库连接对象
#         conn = connection.cursor()
#
#         # 如果传入了超时时间，则设置超时时间
#         if timeout is not None:
#             conn.execute("SET statement_timeout TO %s", [timeout * 1000])  # 将超时时间转换为毫秒
#
#         return conn
#
#     except OperationalError as e:
#         # 处理连接异常
#         print("Error:", e)
#         return None

#QuerySet 转JOSN 数据库端进行分页(适合数据查询量大的)
def QStoJson(qs,total):
    r_arr = []
    r_arra = {"total": total}
    r_arra["data"] = qs
    j = json.dumps(r_arra,ensure_ascii=False)
    return j

# python对象转换成json对象
def List_Json(qs):
    j = json.dumps(qs,ensure_ascii=False)
    return j

def QStoJson1(qs,total,page):
    # r_arr = []
    r_arra = {"total": total, "page": page, "data": qs}
    # 当前页码
    return r_arra


# 执行SQl
def aview_sql_execute(SQL):
    '''
    执行SQL
    :param SQL:
    :return:
    '''
    try:
        cs = connections['aview'].cursor()
        cs.execute(SQL)
        return True
    except Exception as err:
        print(err)
        return False
    finally:
        try:
            cs.close()
        except:
            pass

def sql_execute(SQL):
    '''
    执行SQL
    :param SQL:
    :return:
    '''
    try:
        cs = connections.cursor()
        cs.execute(SQL)
        return True
    except Exception as err:
        print(err)
        return False
    finally:
        try:
            cs.close()
        except:
            pass

def long_sql_reader(SQL):
    try:
        print("-------"+str(datetime.datetime.now()))
        cs = connection.cursor()
        search = cs.execute(SQL)
        SqlDomains = cs.description
        Data = cs.fetchall()
        print("-------"+str(datetime.datetime.now()))
        res_data = []
        for row in Data:
            result = {}
            i = 0
            for SqlDomain in SqlDomains:
                # result[SqlDomain[0]] = str(row[i])
                if row[i] == None:
                    result[SqlDomain[0]] = ""
                else:
                    result[SqlDomain[0]] = str(row[i])
                i += 1
            res_data.append(result)
        return res_data
    except Exception as err:
        print(err)
        return []
    finally:
        try:
            cs.close()
        except:
            pass
# 治具列表
def Tray_reader_page(SQL,SQL_Scan,page,limit):
    try:

        cs = connection.cursor()
        search = cs.execute(SQL)
        print(SQL)
        data = cs.fetchall()
        # data = sql_list(SQL)
        SqlDomains = cs.description
        res_data = []
        search = cs.execute(SQL_Scan)
        data_scan = cs.fetchall()
        print("------------")
        print(data)
        print(data_scan)
        rowcount = 0
        for row in data:
            for o in row[0].split(';'):
                i = 0
                result = {}
                for SqlDomain in SqlDomains:
                    if i < 1:
                        result[SqlDomain[0]] = o
                    else:
                        if row[i] == None:
                            result[SqlDomain[0]] = ""
                        else:
                            result[SqlDomain[0]] = str(row[i])
                    i += 1
                result["Status"] = -1
                for ds in data_scan:
                    if ds[0] == o:
                        if ds[1] == "OK":
                            result["Status"] = 1
                        elif ds[1] == "NG":
                            result["Status"] = 0

                rowcount +=1
                print(result)
                res_data.append(result)
        # print(rowcount)
        print(res_data)
        if (int(page) - 1) * int(limit) > rowcount:
            page = 1

        if int(page) > 0 and int(limit) > 0:
            res_data=res_data[((int(page)-1)*int(limit)):int(page)*int(limit):1]
        print(res_data)
        return QStoJson1(res_data,rowcount,int(page))
    except Exception as err:
        print(err)
        return []
    finally:
        try:
            cs.close()
        except:
            pass


# 处理COUNT SQL
# 输入 SQL语句,页码,每页笔数
def aview_sql_reader(SQL, page, limit,db='aview'):
    try:
        cs = connections[db].cursor()
        search = cs.execute(SQL)

        Data = cs.fetchall()
        #Data = cs.execute(SQL).fetchall()
        rowcount= len(Data)
        if (int(page)-1)*int(limit)>rowcount:
            page = 1
        if int(page) > 0 and int(limit) > 0:
            result_data=Data[((int(page)-1)*int(limit)):int(page)*int(limit):1]
            return result_data,rowcount
        else:
            return Data
    except Exception as err:
        print(err)
        if int(page) > 0 and int(limit) > 0:
            return [],0
        else:
            return []
    finally:
        try:
            cs.close()
        except:
            pass

# 处理COUNT SQL
# 输入 SQL语句,页码,每页笔数
def sql_reader(SQL, page, limit):
    try:
        cs = connections.cursor()
        search = cs.execute(SQL)

        Data = cs.fetchall()
        #Data = cs.execute(SQL).fetchall()
        rowcount= len(Data)
        if (int(page)-1)*int(limit)>rowcount:
            page = 1
        if int(page) > 0 and int(limit) > 0:
            result_data=Data[((int(page)-1)*int(limit)):int(page)*int(limit):1]
            return result_data,rowcount
        else:
            return Data
    except Exception as err:
        print(err)
        if int(page) > 0 and int(limit) > 0:
            return [],0
        else:
            return []
    finally:
        try:
            cs.close()
        except:
            pass



def aview_sql_list_first(SQL,db='aview'):
    """
    执行SQL 返回第一笔
    :param SQL:
    :return List:
    """
    try:
        cs = connections[db].cursor()
        search = cs.execute(SQL)
        Data = cs.fetchone()
        return Data
    except Exception as err:
        print(err)
        return []
    finally:
        try:
            cs.close()
        except:
            pass

def sql_list_first(SQL):
    """
    执行SQL 返回第一笔
    :param SQL:
    :return List:
    """
    try:
        cs = connection.cursor()
        search = cs.execute(SQL)
        Data = cs.fetchone()
        return Data
    except Exception as err:
        print(err)
        return []
    finally:
        try:
            cs.close()
        except:
            pass




# 输入SQL返回列表
def aview_sql_list(SQL,db='aview'):
    '''
    执行SQL
    :param SQL:
    :return 列表:
    '''
    try:
        cs = connections[db].cursor()
        search = cs.execute(SQL)
        Data = cs.fetchall()
        return Data
    except Exception as err:
        print(err)
        return []
    finally:
        try:
            cs.close()
        except:
            pass

# 输入SQL返回列表
def sql_list(SQL):
    '''
    执行SQL
    :param SQL:
    :return 列表:
    '''
    try:
        cs = connection.cursor()
        search = cs.execute(SQL)
        Data = cs.fetchall()
        return Data
    except Exception as err:
        print(err)
        return []
    finally:
        try:
            cs.close()
        except:
            pass

# 输入SQL返回列表分页
def aview_sql_list_page(SQL,page,limit,db='aview'):
    try:
        cs = connections[db].cursor()
        search = cs.execute(SQL)
        Data = cs.fetchall()
        Data = Data[((int(page) - 1) * int(limit)):int(page) * int(limit):1]
        return Data
    except Exception as err:
        print(err)
        return []
    finally:
        try:
            cs.close()
        except:
            pass

# 输入SQL返回列表分页
def sql_list_page(SQL,page,limit):
    try:
        cs = connection.cursor()
        search = cs.execute(SQL)
        Data = cs.fetchall()
        Data = Data[((int(page) - 1) * int(limit)):int(page) * int(limit):1]
        return Data
    except Exception as err:
        print(err)
        return []
    finally:
        try:
            cs.close()
        except:
            pass

# 输入SQL返回列表和笔数
def aview_sql_list_pageandcont(SQL,page,limit,db='aview'):
    try:
        cs = connections[db].cursor()
        search = cs.execute(SQL)
        Data = cs.fetchall()
        cnt = len(Data)
        Data = Data[((int(page) - 1) * int(limit)):int(page) * int(limit):1]
        return Data,cnt
    except Exception as err:
        print(err)
        return [],0
    finally:
        try:
            cs.close()
        except:
            pass


# 输入SQL返回列表和笔数
def sql_list_pageandcont(SQL,page,limit):
    try:
        cs = connections.cursor()
        search = cs.execute(SQL)
        Data = cs.fetchall()
        cnt = len(Data)
        Data = Data[((int(page) - 1) * int(limit)):int(page) * int(limit):1]
        return Data,cnt
    except Exception as err:
        print(err)
        return [],0
    finally:
        try:
            cs.close()
        except:
            pass


# 简单SQL 查询 不分页
def aview_easy_sql_reader(SQL,db='aview'):
    try:
        cs = connections[db].cursor()
        search = cs.execute(SQL)
        SqlDomains = cs.description
        Data = cs.fetchall()
        res_data = []
        for row in Data:
            result = {}
            i = 0
            for SqlDomain in SqlDomains:
                # result[SqlDomain[0]] = str(row[i])
                if row[i] == None:
                    result[SqlDomain[0]] = ""
                else:
                    result[SqlDomain[0]] = str(row[i])
                i += 1
            res_data.append(result)
        return List_Json(res_data)
    except Exception as err:
        print(err)
        return []
    finally:
        try:
            cs.close()
        except:
            pass

# 简单SQL 查询 不分页
def easy_sql_reader(SQL):
    try:
        cs = connection.cursor()
        search = cs.execute(SQL)
        SqlDomains = cs.description
        Data = cs.fetchall()
        res_data = []
        for row in Data:
            result = {}
            i = 0
            for SqlDomain in SqlDomains:
                # result[SqlDomain[0]] = str(row[i])
                if row[i] == None:
                    result[SqlDomain[0]] = ""
                else:
                    result[SqlDomain[0]] = str(row[i])
                i += 1
            res_data.append(result)
        return List_Json(res_data)
    except Exception as err:
        print(err)
        return []
    finally:
        log.debug("database_close")
        try:
            cs.close()
        except:
            pass

# 简单SQL 查询 不分页 不转json
def easy_sql_reader(SQL):
    try:
        django.db.close_old_connections()
        cs = connection.cursor()
        search = cs.execute(SQL)
        SqlDomains = cs.description
        Data = cs.fetchall()
        res_data = []
        for row in Data:
            result = {}
            i = 0
            for SqlDomain in SqlDomains:
                # result[SqlDomain[0]] = str(row[i])
                if row[i] == None:
                    result[SqlDomain[0]] = ""
                else:
                    result[SqlDomain[0]] = str(row[i])
                i += 1
            res_data.append(result)
        log.debug("database_success")
        return res_data
    except Exception as err:
        print(err)
        log.error("database_error: " + str(err))
        raise Exception("网络异常:" + str(err))
        return []
    finally:
        try:
            log.debug("database_close")
            cs.close()
            connection.close()
        except:
            pass

# 简单SQL 查询 不分页 {'':""}
def easy_sql_reader1(SQL):
    try:
        cs = connection.cursor()
        search = cs.execute(SQL)
        SqlDomains = cs.description
        Data = cs.fetchall()
        for row in Data:
            result = {}
            i = 0
            for SqlDomain in SqlDomains:
                # result[SqlDomain[0]] = str(row[i])
                if row[i] == None:
                    result[SqlDomain[0]] = ""
                else:
                    result[SqlDomain[0]] = str(row[i])
                i += 1
        return result
    except Exception as err:
        print(err)
        return []
    finally:
        try:
            cs.close()
        except:
            pass


# 简单SQL 查询 分页
def aview_easy_sql_reader_page(SQL,page,limit,db='aview'):
    try:
        cs = connections[db].cursor()
        search = cs.execute(SQL)
        SqlDomains = cs.description
        Data = cs.fetchall()
        res_data = []
        rowcount = len(Data)
        if (int(page)-1) * int(limit) > rowcount:
            page = 1
        for row in Data:
            result = {}
            i = 0
            for SqlDomain in SqlDomains:
                if row[i] == None:
                    result[SqlDomain[0]] = ""
                else:
                    result[SqlDomain[0]] = str(row[i])
                i += 1
            res_data.append(result)

        if int(page) > 0 and int(limit) > 0:
            res_data=res_data[((int(page)-1)*int(limit)):int(page)*int(limit):1]
        return QStoJson(res_data,rowcount)
    except Exception as err:
        print(err)
        return []
    finally:
        try:
            cs.close()
        except:
            pass


# 简单SQL 查询 分页
def aview_easy_sql_reader_page1(SQL,page,limit):
    try:
        cs = connection.cursor()
        search = cs.execute(SQL)
        SqlDomains = cs.description
        Data = cs.fetchall()
        res_data = []
        rowcount = len(Data)
        if (int(page)-1) * int(limit) > rowcount:
            page = 1
        for row in Data:
            result = {}
            i = 0
            for SqlDomain in SqlDomains:
                if row[i] == None:
                    result[SqlDomain[0]] = ""
                else:
                    result[SqlDomain[0]] = str(row[i])
                i += 1
            res_data.append(result)
        print(res_data)

        if int(page) > 0 and int(limit) > 0:
            res_data=res_data[((int(page)-1)*int(limit)):int(page)*int(limit):1]
        return QStoJson1(res_data,rowcount,int(page))
    except Exception as err:
        print(err)
        return []
    finally:
        try:
            cs.close()
        except:
            pass

# 简单SQL 查询 分页
def aview_easy_sql_reader_page2(SQL,page,limit,db='aview'):
    try:
        cs = connections[db].cursor()
        search = cs.execute(SQL)
        SqlDomains = cs.description
        Data = cs.fetchall()
        res_data = []
        rowcount = len(Data)
        if (int(page)-1) * int(limit) > rowcount:
            page = 1
        for row in Data:
            result = {}
            i = 0
            n = 1
            a = 1

            for SqlDomain in SqlDomains:
                if i < 7:
                    if i==4:
                        if row[i] == None:
                            result["Result"] = ""
                        else:
                            result["Result"] = str(row[i])
                    else:

                        if row[i] == None:
                            result[SqlDomain[0]] = ""
                        else:
                            result[SqlDomain[0]] = str(row[i])
                    i += 1

                else:

                    if (i-7) % 2 == 0:
                        name_ = 'Test_Name' + str(n)
                        value_ = "Test_Value" + str(n)
                        n += 1
                        result[name_] = SqlDomain[0]
                        result[value_] = str(row[i])
                    if (i-7) % 2 == 1:
                        result_ = "Test_Result" + str(a)
                        a += 1
                        result[result_] = str(row[i])
                    i += 1
            res_data.append(result)
        if int(page) > 0 and int(limit) > 0:
            res_data = res_data[((int(page)-1)*int(limit)):int(page)*int(limit):1]
        print(res_data)
        return QStoJson6(res_data,rowcount)
    except Exception as err:
        print(err)
        return []
    finally:
        try:
            cs.close()
        except:
            pass


# 简单SQL 查询 分页
def easy_sql_reader_page(SQL,page,limit):
    try:
        cs = connection.cursor()
        search = cs.execute(SQL)
        SqlDomains = cs.description
        Data = cs.fetchall()
        res_data = []
        rowcount = len(Data)
        if (int(page)-1) * int(limit) > rowcount:
            page = 1
        for row in Data:
            result = {}
            i = 0
            for SqlDomain in SqlDomains:
                if row[i] == None:
                    result[SqlDomain[0]] = ""
                else:
                    result[SqlDomain[0]] = str(row[i])
                i += 1
            res_data.append(result)

        if int(page) > 0 and int(limit) > 0:
            res_data=res_data[((int(page)-1)*int(limit)):int(page)*int(limit):1]
        return QStoJson(res_data,rowcount)
    except Exception as err:
        print(err)
        return []
    finally:
        try:
            cs.close()
        except:
            pass

# 简单SQL 查询 不分页
def aview_easy_sql_dict(SQL,db='aview'):
    '''
    SQL 转字典
    :param SQL:
    :return: list[dict]
    '''
    try:
        cs = connections[db].cursor()
        search = cs.execute(SQL)
        SqlDomains = search.description
        Data = cs.fetchall()
        res_data = []
        for row in Data:
            result = {}
            i = 0
            for SqlDomain in SqlDomains:
                #result[SqlDomain[0]] = str(row[i])
                if row[i] == None:
                    result[SqlDomain[0]] = ""
                else:
                    result[SqlDomain[0]] = str(row[i])
                i += 1
            res_data.append(result)
        return res_data
    except Exception as err:
        print(err)
        return []
    finally:

        try:
            cs.close()
        except :
            pass


# # 简单SQL 查询 不分页
# def easy_sql_dict(SQL):
#     '''
#     SQL 转字典
#     :param SQL:
#     :return: list[dict]
#     '''
#     try:
#         cs = connections.cursor()
#         search = cs.execute(SQL)
#         SqlDomains = search.description
#         Data = cs.fetchall()
#         res_data = []
#         for row in Data:
#             result = {}
#             i = 0
#             for SqlDomain in SqlDomains:
#                 #result[SqlDomain[0]] = str(row[i])
#                 if row[i] == None:
#                     result[SqlDomain[0]] = ""
#                 else:
#                     result[SqlDomain[0]] = str(row[i])
#                 i += 1
#             res_data.append(result)
#         return res_data
#     except Exception as err:
#         print(err)
#         return []
#     finally:
#
#         try:
#             cs.close()
#         except :
#             pass


def sql_execute(SQL):
    try:
        django.db.close_old_connections()
        cs = connection.cursor()
        cs.execute(SQL)
        log.debug("database_success")
        return True
    except Exception as err:
        print(err)
        log.error("database_error: " + str(err))
        err_str = str(err)
        # 1060：同一包 Test_Value 重复项，或列已加过，按成功处理
        if "1060" in err_str or "Duplicate column name" in err_str:
            return True
        raise Exception("网络异常")
        return False
    finally:
        try:
            log.debug("database_close")
            cs.close()
            connection.close()
        except:
            pass

def ReadModelProduction(model):
    SQL = "SELECT Pass FROM model_tab WHERE gp_model ='" + model + "'"
    cs = connection.cursor()
    cs.execute(SQL)
    result = cs.fetchall()

