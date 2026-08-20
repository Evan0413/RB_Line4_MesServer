from django.db import models

# Create your models here.


class menu(models.Model):
    menu_id = models.CharField(max_length=100, primary_key=True, unique=True)
    menu_name = models.CharField(max_length=100)
    # menu_desc = models.CharField(max_length=100)
    menu_link = models.CharField(max_length=50)
    menu_group = models.CharField(max_length=50)
    # menu_sub = models.CharField(max_length=10)


class group(models.Model):
    group_id = models.CharField(max_length=100, primary_key=True, unique=True)
    group_name = models.CharField(max_length=100)
    group_icon = models.CharField(max_length=100)
    group_main_id = models.CharField(max_length=100)

class view_auth(models.Model):
    view_id = models.CharField(max_length=100, primary_key=True, unique=True)
    sfc_id = models.CharField(max_length=100)
