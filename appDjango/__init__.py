import pymysql
import sys
import time
from threading import Thread
pymysql.install_as_MySQLdb()

if len(sys.argv) > 1 and sys.argv[1] == 'runserver':
    from COMMON import getmqtt
    from COMMON import setmqtt
    t_s = Thread(target=setmqtt.main)  # Start the embedded MQTT broker.
    t_s.start()
    print("----------MQTT_Broker Start----------")
    time.sleep(2)
    t_c = Thread(target=getmqtt.main2)
    t_c.start()
    print("----------MQTT_Client Start----------")



# getmqtt.main()

