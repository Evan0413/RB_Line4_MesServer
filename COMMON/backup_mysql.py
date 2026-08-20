import subprocess
import datetime
import time
from COMMON.file_operation import *
from appDjango.settings import db_config

def BackUp():
    while True:
        print("---------Auto save")
        filepath = GetFilePath("SoftWare.ini")
        conf = ConfigParser()  # 需要实例化一个ConfigParser对象
        conf.read(filepath)  # 需要添加上config.ini的路径，不需要open打开，直接给文件路径就读取，也可以指定encoding='utf-8'
        backup_date = conf['CommonUse']['backup_date']
        if backup_date == "":
            latestdate = datetime.datetime.now().replace(microsecond=0)
        else:
            latestdate = datetime.datetime.strptime(backup_date, "%Y-%m-%d %H:%M:%S")

        bk_time = int(conf['CommonUse']['backup_time'])
        bk_path = conf['CommonUse']['backip_path']

        t = datetime.datetime.now().replace(microsecond=0)
        delta_t = (t-latestdate).days
        if not delta_t < bk_time:
            backup_mysql(bk_path)
            conf.set('CommonUse', 'backup_date', str(t))
            with open(filepath, 'w', encoding='utf-8') as f:
                conf.write(f)
        time.sleep(10)

def backup_mysql(bk_path):
    log.info("------Saving")
    t = datetime.datetime.now().replace(microsecond=0)
    year = t.year
    mon = t.month
    day = t.day
    # username = 'root'
    # password = '123456'
    # database_name = 'aview_mysql'
    username = db_config['default']['USER']
    password = db_config['default']['PASSWORD']
    database_name = db_config['default']['NAME']
    filename = f'backup_{year}_{mon}_{day}.sql'
    command = f'mysqldump -u {username} -p{password} --databases {database_name}'
    with open(bk_path + filename, 'w') as backup_file:
        subprocess.run(command, stdout=backup_file, shell=True)
    log.info("------Saving Done " + str(t))

if __name__ == '__main__':
    backup_mysql()