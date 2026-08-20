from django.db import models

# Create your models here.
# class station_tab(models.Model):
#     id = models.CharField(max_length=100, primary_key=True, unique=True)
#     equipment_name = models.CharField(max_length=100)
#     equipment_num = models.CharField(max_length=100)
#     equipment_ip = models.CharField(max_length=100)
#     equipment_serial = models.CharField(max_length=100)
#     gp_model = models.CharField(max_length=50)
class menu(models.Model):
    menu_id = models.CharField(max_length=100, primary_key=True, unique=True)
    menu_name = models.CharField(max_length=100)
    # menu_desc = models.CharField(max_length=100)
    menu_link = models.CharField(max_length=50)
    menu_group = models.CharField(max_length=50)
    # menu_sub = models.CharField(max_length=10)

    def toDict(self):
        param = {
            "menu_id": self.menu_id,
            "menu_name": self.menu_name,
            # "menu_desc": self.menu_desc,
            "menu_link": self.menu_link,
            "menu_group": self.menu_group,
            # "menu_sub": self.menu_sub,
        }
        return param
    class Meta:
        ordering = ['menu_id']
        db_table = 'menu'


class group(models.Model):
    group_id = models.CharField(max_length=100, primary_key=True, unique=True)
    group_name = models.CharField(max_length=100)
    group_icon = models.CharField(max_length=100)
    group_main_id = models.CharField(max_length=100)

    class Meta:
        ordering = ['group_id']
        db_table = 'group'

class view_auth(models.Model):
    view_id = models.CharField(max_length=100, primary_key=True, unique=True)
    sfc_id = models.CharField(max_length=100)

    class Meta:
        ordering = ['view_id']
        db_table = 'view_auth'

class qr_confrimation_tab(models.Model):
    id = models.IntegerField(primary_key=True,db_index=True)
    datetime = models.DateTimeField()
    serial_no = models.CharField(max_length=50,db_index=True)
    pcba_code1 = models.CharField(max_length=255,db_index=True)
    pcba_code2 = models.CharField(max_length=255,db_index=True)
    qr_code1 = models.CharField(max_length=255,db_index=True)
    qr_code2 = models.CharField(max_length=255,db_index=True)
    lens = models.CharField(max_length=255)
    check_result = models.CharField(max_length=255)
    test_result = models.CharField(max_length=200)
    gp_model = models.CharField(max_length=255)
    station_no = models.CharField(max_length=255)
    site_name = models.CharField(max_length=255)
    stand_code = models.CharField(max_length=255)
    check_time = models.DateTimeField()
    test_time = models.DateTimeField()
    part_no = models.CharField(max_length=255)
    part_batch = models.CharField(max_length=255)

