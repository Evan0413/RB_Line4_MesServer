# import logging
# import datetime
# import os.path
# def logger():
#     '''志文件名；
#     fi
#     logging.basicConfig函数各参数：
#     filename：指定日lemode：和file函数意义相同，指定日志文件的打开模式，'w'或者'a'；
#     format：指定输出的格式和内容，format可以输出很多有用的信息，
#     level logging.INFO,
#     '''
#     #调用配置函数
#     day_tag = ""
#     if datetime.datetime.now().hour < 12:
#         day_tag = "AM"
#     else:
#         day_tag = "PM"
#
#     path = datetime.datetime.now().strftime("%Y_%m_%d") + f"_{day_tag}" + ".txt"
#     proDir = os.path.split(os.path.realpath(__file__))[0]
#     proDir = os.path.dirname(proDir)
#     proDir = os.path.join(proDir, 'logs')
#     configpath = os.path.join(proDir, path)
#
#     logging.basicConfig(format='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s:%(message)s',
#                         filename=configpath,
#                         # filename= 'C:\\Users\\at342\\Desktop\\djangobackup\\docker_test\\appDjango\\appDjango\logs\\2023_08_11_PM.txt',
#                         level='INFO',
#                         filemode='a'
#                         )
#
#     # logging.basicConfig(format='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s:%(message)s',
#     #                     # filename='logs//' + datetime.datetime.now().strftime(
#     #                     #     "%Y_%m_%d") + f"_{day_tag}" + ".txt",
#     #                     filename='C:\\Users\\at342\\Desktop\\djangobackup\\docker_test\\appDjango\\appDjango\logs\\' + datetime.datetime.now().strftime("%Y_%m_%d") + f"_{day_tag}" + ".txt",
#     #                     # filename= 'C:\\Users\\at342\\Desktop\\djangobackup\\docker_test\\appDjango\\appDjango\logs\\2023_08_11_PM.txt',
#     #                     level='INFO',
#     #                     filemode='a'
#     # )
#     return logging
# if __name__ == '__main__':
#     log = logger()
#     print(datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S"))
#     print(datetime.datetime.now().hour)
#     log.error('---hello---')
#     log.info('---hello---')




import logging
import time
from builtins import OSError
import os.path

from logging.handlers import TimedRotatingFileHandler

new_formatter = '[%(levelname)s]%(asctime)s:%(msecs)s.%(process)d,%(thread)d#>[%(funcName)s]:%(lineno)s  %(message)s'
"""
%(asctime)s 字符串形式的当前时间。默认格式是“2021-09-08 16:49:45,896”。逗号后面的是毫秒
%(created)f 时间戳, 等同于time.time()
%(relativeCreated)d 日志发生的时间相对于logging模块加载时间的相对毫秒数
%(msecs)d 日志时间发生的毫秒部分
%(levelname)s 日志级别str格式
%(levelno)s 日志级别数字形式(10, 20, 30, 40, 50)
%(name)s 日志器名称, 默认root
%(message)s 日志内容
%(pathname)s 日志全路径
%(filename)s 文件名含后缀
%(module)s 文件名不含后缀
%(lineno)d 调用日志记录函数源代码的行号
%(funcName)s 调用日志记录函数的函数名
%(process)d 进程id
%(processName)s 进程名称
%(thread)d 线程ID
%(threadName)s 线程名称
"""
fmt = logging.Formatter(new_formatter)

proDir = os.path.split(os.path.realpath(__file__))[0]
proDir = os.path.dirname(proDir)
proDir = os.path.join(proDir, 'logs')
configpath = os.path.join(proDir, 'mes.log')
# 凌晨0点分割生成log，仅保留最新180个log记录
log_handel = TimedRotatingFileHandler(configpath, when='midnight',backupCount = 180)
log_handel.setFormatter(fmt)

logger = logging.getLogger('info')
logger.setLevel(logging.INFO)
logger.addHandler(log_handel)

