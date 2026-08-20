
from django.urls import path, include
# from rest_framework.routers import DefaultRouter

from ManDe import views
#
# router = DefaultRouter()
# router.register(r'phone', views.phone, basename='phone')
#
# urlpatterns = [
#     path('', include(router.urls)),
# ]
# urlpatterns = [
#     # path('', views.main, name='main'),
# ]
# urlpatterns = []
# urlpatterns += router.urls
urlpatterns = [
    # path('', views.main, name='main'),
    # path('phone/', views.phone, name='phone'),
    # path('id', views.id,name='id'),
    path('test', views.test, name='test'),
    path('stream', views.stream, name='stream'),
    # 登录接口
    path("login", views.login),
    # 获取菜单列表接口
    path('menus', views.main, name='main'),
    # 获取用户信息（权限）接口
    path('local_users', views.local_users, name='local_users'),
    # 获取用户数据列表
    path('users', views.users, name='users'),
    # 修改密码
    path('users/changpsw', views.changpsw, name='changpsw'),

    # 删除用户
    path('Deleteusers', views.Deleteusers, name='Deleteusers'),
    # 添加用户
    path('Addusers', views.Addusers, name='Addusers'),

    # 根据 ID 查询用户信息
    path('users/id', views.usersid, name='usersid'),
    # 修改用户信息
    path('EditUsersInfo', views.EditUsersInfo, name='EditUsersInfo'),
    # -----------------设备管理-------------------

    # 获取设备列表
    path('devices', views.devices, name='devices'),
    # 删除设备
    path('DeleteDevice', views.DeleteDevice, name='DeleteDevice'),
    # 添加设备
    path('AddDevice', views.AddDevice, name='AddDevice'),
    # 根据 ID 查询设备信息
    path('device/id', views.deviceid, name='deviceid'),
    # # 修改设备信息
    path('EditDeviceInfo', views.EditDeviceInfo, name='EditDeviceInfo'),
    # -----------------设备控制--------------------

    #获取型号&设备列表
    path('station/GetLocalModel_Equipment', views.GetLocalModel_Equipment, name='GetLocalModel_Equipment'),
    path('station/Function_Btn', views.Function_Btn, name='Function_Btn'),
    path('station/Remodel', views.Remodel, name='Remodel'),
    path('station/QuickRemodel', views.QuickRemodel, name='QuickRemodel'),




    # -----------------型号管理-------------------

    # 获取型号列表接口
    path('model/models_list', views.models, name='models'),
    # 获取设备名列表接口
    path('model/equips_list', views.equips_list, name='equips_list'),
    # 获取设备列表
    path('model/Modeldevices', views.Modeldevices, name='Modeldevices'),
    # 添加型号
    path('AddModels', views.AddModels, name='AddModels'),
    # 删除型号下的工位
    path('DeleteModel_Device', views.DeleteModel_Device, name='DeleteModel_Device'),
    # 删除型号
    path('DeleteModel', views.DeleteModel, name='DeleteModel'),



    # -----------------料盘管理-------------------
    #获取料盘列表
    path('tray/tray_list', views.tray, name='tray'),
    #获取料盘对应的码
    path('tray/TarySeries', views.TarySeries, name='TarySeries'),
    #添加料盘
    path('tray/AddTray', views.AddTray, name='AddTray'),
    #删除料盘
    path('tray/DeleteTray', views.DeleteTray, name='DeleteTray'),

    # ------------------------------ 生产追溯-------------------------------------
    # 获取料盘号列表接口
    path('Product/ProInfo', views.ProInfo, name='ProInfo'),
    # 型号追溯
    path('Product/ModelInfo', views.ModelInfo, name='ModelInfo'),
    # 站位追溯
    path('Product/StaInfo', views.StaInfo, name='StaInfo'),

    # 删除产品生产记录
    path('Product/DeleteProInfo', views.DeleteProInfo, name='DeleteProInfo'),


]