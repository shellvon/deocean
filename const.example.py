# -*- coding: utf-8 -*-

DOMAIN: str = 'deocean'

# 德能森内置场景(只关心面板,因为面板按下之后网关收到消息转发给德能森,德能森再决定此面板可以干啥->)
# 如果去掉德能森之后,必须把德能森要做的事情一并处理了.
# 所以此处依旧从 dev_rep_list.txt 中提取.

BUILTIN_SCENE_STR: str = '''
# 以#开始可以认为是注释, 大概可以这样  格式: 
# 场景名 面板地址 面板channel(德能森数据库有), 关联设备名(name支持特殊:all|all_light all_cover), 支持的功能:turn_on|turn_off|toggle
# 场景配置格式类似CSV。即以逗号隔开分组。如果是注释可以以 # 开头。
#    name, addr, channel, devices, op
#    其中devices 是已经add 的设备名。多个名字使用|分割.
#    特殊设备名包括: 
#        all :不区分设备类型，所有设备
#        all_light: 所有灯具
#        all_cover: 所有窗帘
#   devices 本身也可以特定指定某一个设备的op.
# 比如:
#   离家, 0x0A0B0C0D, 1, all_light|主卧纱帘, turn_off 
#   回家, 0x0A0B0C0D, 2, all_light:turn_off|客厅布帘|过道灯:toggle, turn_on
#   开帘, 0x0A0B0C0D, 3, 主卧纱帘:80
#   
# ⬆上述执行:所有灯具先turn_off关闭。然后窗帘没有指定则用通用结果 turn_on, 过道灯虽然也在all_light中被先关闭了，此处会toggle一次。
# 需要注意的，解析顺序按照从左到右执行，且各op是异步的。在一个场景中出现互斥指令不见得一定符合预期。比如上述: 
#   过道灯turn_off之后再toggle应该是turn_on,但实际上可能在执行toggle的时候本地状态还是on,所以toggle之后是turn_off。不符合预期结果.
'''


# 德能森内置灯具和窗帘
# grep -E 'blind|light' dev_rep_list.txt  | grep -v '^light' | cut -d, -f1-3
BUILTIN_DEVICES_STR = '''
# 设备名, 设备类型(light|blind) 设备地址。 这个可以在德能森数据库中找到
生活阳台灯,     light,  abcedef
'''
