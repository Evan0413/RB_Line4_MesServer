
from django.urls import path, include
# from rest_framework.routers import DefaultRouter

from ManDe import views
# web api组件
from rest_framework import routers

router = routers.DefaultRouter()  # 声明一个默认的路由注册器
# router.register(r'goods', UserViewSet)  # 注册写好的接口视图
# router.register(r'goodsType', TypeViewSet)  # 注册写好的接口视图

urlpatterns = [
    # path('', views.main, name='main'),
    # path('phone/', views.phone, name='phone'),
    # path('id', views.id,name='id'),
    path('urltest', views.urltest, name='urltest'),
    path('test', views.test, name='test'),
    path('test1', views.test1, name='test1'),
    path('test2', views.test2, name='test2'),
    path('test_database', views.test_database, name='test_database'),
    # path('sttest', views.alltest, name='alltest'),
    path('ws', views.ws, name='ws'),
    # path('stream', views.stream, name='stream'),
    path('index/board', views.board, name='board'),
    # 保存胶水码号接口
    path('Save_JS_PART_NO', views.Save_JS_PART_NO, name='Save_JS_PART_NO'),
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
    # 设备轮询
    path('device/updateCarrierStatus', views.updateCarrierStatus, name='updateCarrierStatus'),
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
    # 设备点检
    path('CheckDevice', views.CheckDevice, name='CheckDevice'),
    # 修改设备点检
    path('EditCheckDevice', views.EditCheckDevice, name='EditCheckDevice'),
    # -----------------设备控制--------------------

    #获取型号&设备列表
    path('station/GetLocalModel_Equipment', views.GetLocalModel_Equipment, name='GetLocalModel_Equipment'),
    path('station/Function_Btn', views.Function_Btn, name='Function_Btn'),
    path('station/Remodel', views.Remodel, name='Remodel'),
    path('station/QuickRemodel', views.QuickRemodel, name='QuickRemodel'),
    path('station/Remodel_SP', views.Remodel_SP, name='Remodel_SP'),
    path('station/GetLocalModel_Equipment_SP', views.GetLocalModel_Equipment_SP, name='GetLocalModel_Equipment_SP'),



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
    # 修改型号对应的上料方式
    path('EditModel_Snway', views.EditModel_Snway, name='EditModel_Snway'),
    # 获取设备列表 包含对应的站点绑定信息
    path('model/Modeldevices_Bind', views.Modeldevices_bind, name='Modeldevices_bind'),
    # 修改型号中工位对应的绑定方式
    # path('EditModel_Bind', views.EditModel_Bind, name='EditModel_Bind'),

    # -----------------料盘管理-------------------
    path('tray/ST_Tarys', views.ST_Tarys, name='ST_Tarys'),
    path('tray/ST_TarysDetail', views.ST_TarysDetail, name='ST_TarysDetail'),
    path('tray/CheckTraysn', views.CheckTraysn, name='CheckTraysn'),

    #获取料盘列表
    path('tray/tray_list', views.tray, name='tray'),
    #获取料盘对应的码
    path('tray/TarySeries', views.TarySeries, name='TarySeries'),
    #添加料盘
    path('tray/AddTray', views.AddTray, name='AddTray'),
    path('tray/AddTrays', views.AddTrays, name='AddTrays'),
    #删除料盘
    path('tray/DeleteTray', views.DeleteTray, name='DeleteTray'),
    #删除治具
    path('Fixs/DeleteFixs', views.DeleteFixs, name='DeleteFixs'),

    # 6-27 新加------------------------------ 料号管理-------------------------------------
    # 获取料盘号列表接口
    path('pan/pan_list', views.pan_list, name='pan_list'),
    # 添加料盘号
    path('pan/AddPan', views.AddPan, name='AddPan'),
    # 获取料盘绑定的码
    path('pan/PanSeries', views.PanSeries, name='PanSeries'),
    # 删除料盘号
    path('pan/DeletePan', views.DeletePan, name='DeletePan'),

    # ------------------------------ 生产追溯-------------------------------------
    # 产品追溯接口
    # 按码查询
    path('Product/ProInfo', views.ProInfo, name='ProInfo'),
    # 按码查询下载
    path('Product/ProInfo_dl', views.ProInfo_dl, name='ProInfo_dl'),
    # 按工站查询
    path('Product/ProInfo_sta', views.ProInfo_sta, name='ProInfo_sta'),
    # 按工站查询下载
    path('Product/ProInfo_sta_dl', views.ProInfo_sta_dl, name='ProInfo_sta_dl'),
    # 按时间查询
    path('Product/ProInfo_time', views.ProInfo_time, name='ProInfo_time'),
    # 按时间查询下载
    path('Product/ProInfo_time_dl', views.ProInfo_time_dl, name='ProInfo_time_dl'),
    # 产品历史追溯
    path('Product/ProInfo_history', views.ProInfo_history, name='ProInfo_history'),
    # 产品历史追溯下载
    path('Product/ProInfo_history_dl', views.ProInfo_history_dl, name='ProInfo_history_dl'),
    # 型号追溯
    path('Product/ModelInfo', views.ModelInfo, name='ModelInfo'),
    # 站位追溯 良率统计
    path('Product/StaInfo', views.StaInfo, name='StaInfo'),
    # 删除产品生产记录 重投
    path('Product/DeleteProInfo', views.DeleteProInfo, name='DeleteProInfo'),
    # 手动绑定按钮
    path('Product/Bind_manual_btn', views.Bind_manual_btn, name='Bind_manual_btn'),
    # -----------------------------手动测试过站--------------------------------------
    # 获取产线上所有正在生产的产品信息
    path('Jump/GetOnline', views.GetOnline, name='GetOnline'),
    # 手动过站，将产品跳到目标站点
    path('Jump/ToStation', views.ToStation, name='ToStation'),
    # -----------------------------NG过站---------------------------------------
    # 三次NG重测
    # 获取主界面信息
    path('Jump/Get_retestmsg', views.Get_retestmsg, name='Get_retestmsg'),
    # 站点区间设置
    path('Jump/retest_setting', views.retest_setting, name='retest_setting'),
    # 重测按钮
    path('Jump/retest', views.retest, name='retest'),
    # -----------------------------工单管理-------------------------------------
    # 手动添加摄像头工单
    path('Order/Addorder', views.Addorder, name='Addorder'),
    # path('Order/Deleteorder', views.Deleteplan, name='Deleteplan'),
    # path('Order/Editorder', views.Editplan, name='Editplan'),
    # 获取全部摄像头工单记录
    path('Order/Getorder', views.Getorder, name='Getorder'),
    # 获取当前生产的摄像头工单
    path('Order/GetCurrentorder', views.GetCurrentorder, name='GetCurrentorder'),
    #-----------------------------------------------
    # 手动添加支架工单
    path('Order/Addorder_stand', views.Addorder_stand, name='Addorder_stand'),
    # 获取全部支架工单记录
    path('Order/Getorder_stand', views.Getorder_stand, name='Getorder_stand'),
    #------------------------------------------------
    # -----------------------------------------------工单关闭和切换
    # 关闭当前工单按钮
    path('Order/ClosePlanOrder_btn', views.ClosePlanOrder_btn, name='ClosePlanOrder_btn'),
    path('Order/ClosePlanOrder_btn_stand', views.ClosePlanOrder_btn_stand, name='ClosePlanOrder_btn_stand'),
    # 切换当前工单按钮
    path('Order/ChangePlanOrder_btn', views.ChangePlanOrder_btn, name='ChangePlanOrder_btn'),
    path('Order/ChangePlanOrder_btn_stand', views.ChangePlanOrder_btn_stand, name='ChangePlanOrder_btn_stand'),
    #------------------------------------------------工单重传
    # 工单重传数据获取
    path('Order/Getorder_re', views.Getorder_re, name='Getorder_re'),
    # 产品重传数据获取
    path('Order/Getpro_re', views.Getpro_re, name='Getpro_re'),
    # 工单数据重传
    path('Order/Order_dataup', views.Order_dataup, name='Order_dataup'),
    # 产品数据重传
    path('Order/Pro_dataup', views.Pro_dataup, name='Pro_dataup'),
    # 产品数据一键重传
    path('Order/Pro_dataup_all', views.Pro_dataup_all, name='Pro_dataup_all'),
    #------------------------------------------------物料维护
    # 工单物料信息上传  物料维护 上传和获取
    path('Order/Info_upload', views.Info_upload, name='Info_upload'),
    path('Order/Get_info', views.Get_info, name='Get_info'),
    #------------------------------------------------镭雕码维护
    # 镭雕码维护 上传\获取\测试输出
    # path('Order/Lasercode_setting', views.Lasercode_setting, name='Lasercode_setting'),
    path('Order/Lasercode_get', views.Lasercode_get, name='Lasercode_get'),
    path('Order/Lasercode_set', views.Lasercode_set, name='Lasercode_set'),
    # path('Order/Lasercode_save', views.Lasercode_save, name='Lasercode_save'),
    # path('Order/Lasercode_test', views.Lasercode_test, name='Lasercode_test'),
    #
    # path('Order/Lasercode_stand_get', views.Lasercode_stand_get, name='Lasercode_stand_get'),
    # path('Order/Lasercode_stand_set', views.Lasercode_stand_set, name='Lasercode_stand_set'),
    # path('Order/Lasercode_stand_test', views.Lasercode_stand_test, name='Lasercode_stand_test'),

    # ----------------------------Setting设置接口---------------------------------------
    # MES设置获取
    path('Setting/Get_setting', views.Get_setting, name='Get_setting'),
    # MES设置保存
    path('Setting/Set_setting', views.Set_setting, name='Set_setting'),

    # ----------------------------MOM接口---------------------------------------
    # 修改工单数量接口(MOM主动访问)
    path('Order/ChangePlanOrderList', views.ChangePlanOrderList, name='ChangePlanOrderList'),
    # 主动请求MOM工单按钮
    path('Order/GetPlanOrder_btn', views.GetPlanOrder_btn, name='GetPlanOrder_btn'),
    # 主动请求MOM工单支架按钮
    path('Order/GetPlanOrder_btn_stand', views.GetPlanOrder_btn_stand, name='GetPlanOrder_btn_stand'),

    # 内存泄露测试
    path('begin_show',views.begin_show,name = 'begin_show'),
    path('show',views.show,name = 'show'),
    path('clean_ram',views.clean_ram,name = 'clean_ram'),
    path('sql_test',views.sql_test,name = 'sql_test'),
]