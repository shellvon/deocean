# -*- coding: utf-8 -*-

DOMAIN: str = "deocean"

# 配置常量
CONF_DEVICES = "devices"
CONF_SCENES = "scenes"

# 版本信息
VERSION = "2.2.0"

# 默认网关配置
DEFAULT_HOST = "192.168.5.201"
DEFAULT_PORT = 50016

# 德能森内置灯具和窗帘
# grep -E 'blind|light' dev_rep_list.txt  | grep -v '^light' | cut -d, -f1-3
DEFAULT_DEVICES = """# 设备配置格式: 设备名, 设备类型(light|blind), 设备地址
# 设备名, 设备类型(light|blind) 设备地址。 这个可以在德能森数据库中找到
生活阳台灯, light,   001E9DFE
主卫灯, light,   001E9A68
厨房灯, light,   001E9ABD
次卧主灯,   light, 001E99F4
公卫灯, light,   001E9A5D
主卧左阅读灯,   light, 001EA071
阳台灯, light,   001E9E0C
主卧布帘,   blind, 7554D501
客厅纱帘,   blind, 7554CB01
主卧右阅读灯,   light, 001E9E0D
主卧过道灯, light,   001E9DF8
次卧1主灯,  light,    001E9E39
客厅筒灯,   light, 001E9792
客厅主灯,   light, 001E9DF7
过道灯, light,   001E976A
主卧主灯,   light, 001E9E3D
主卧灯带,   light, 001E9A5A
客厅布帘,   blind, 7554C701
主卧纱帘,   blind, 7554D401
客厅灯带,   light, 001E9A0A
餐厅灯, light, 	001E9F56
"""

DEFAULT_SCENES = """# 场景配置格式: 场景名, 面板地址, 面板channel, 关联设备名, 操作
# 设备名支持: all(所有设备), all_light(所有灯), all_cover(所有窗帘), 或具体设备名
# 操作支持: turn_on, turn_off, toggle, 或窗帘位置(0-100)

主卧床头右阅读, BA530400, 8, 主卧左阅读灯|主卧右阅读灯, toggle
主卧床头右起夜, BA530400, 1, 主卧过道灯|主卫灯, toggle
主卧床头左全开, 44540400, 16, 主卧过道灯|主卧左阅读灯|主卧右阅读灯|主卧灯带|主卧主灯|主卧纱帘|主卧布帘, turn_on
客厅全关,      8B550400, 2, 客厅灯带|客厅主灯|客厅筒灯|餐厅灯|过道灯|厨房灯｜阳台灯, turn_off
主卧床头纱帘,  44540400, 4, 主卧纱帘, toggle
主卧床头布帘,  44540400, 8, 主卧布帘, toggle
主卧入门全开,  F7540400, 16, 主卧过道灯|主卧左阅读灯|主卧右阅读灯|主卧灯带|主卧主灯|主卧纱帘|主卧布帘, turn_on
入户离家,      E1550400, 2, all_light, turn_off
主卧床头右全开, BA530400, 16, 主卧过道灯|主卧左阅读灯|主卧右阅读灯|主卧灯带|主卧主灯|主卧纱帘|主卧布帘, turn_on
主卧入门全关,   F7540400, 2, 主卧过道灯|主卧左阅读灯|主卧右阅读灯|主卧灯带|主卧主灯, turn_off
主卧入门阅读,   F7540400, 8, 主卧左阅读灯|主卧右阅读灯, toggle
主卧床头右睡眠, BA530400, 2, 主卧过道灯|主卧左阅读灯|主卧右阅读灯|主卧灯带|主卧主灯|主卧纱帘|主卧布帘, turn_off
入户回家,      E1550400, 16, 客厅灯带|客厅主灯|客厅筒灯, turn_on
主卧床头左起夜, 44540400, 1, 主卧过道灯|主卫灯, toggle
主卧床头左睡眠, 44540400, 2, 主卧过道灯|主卧左阅读灯|主卧右阅读灯|主卧灯带|主卧主灯|主卧纱帘|主卧布帘, turn_off
客厅纱帘,      8B550400, 4, 客厅纱帘,toggle
主卧床头左起床, 44540400, 32,主卧纱帘|主卧布帘,turn_on
客厅布帘,      8B550400, 8, 客厅布帘,toggle
"""
