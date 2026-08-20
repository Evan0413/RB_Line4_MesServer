import pymysql
import time
from threading import Thread
pymysql.install_as_MySQLdb()

from COMMON import getmqtt
from COMMON import setmqtt
t_s = Thread(target=setmqtt.main)  # 执行的函数如果需要传递参数，threading.Thread(target=函数名,args=(参数，逗号隔开))
t_s.start()
print("----------MQTT_Broker Start----------")
time.sleep(2)
t_c = Thread(target=getmqtt.main2)
t_c.start()
print("----------MQTT_Client Start----------")

# getmqtt.main()

