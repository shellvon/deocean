DOMAIN: str = 'deocean'

# 德能森内置场景(只关心面板,因为面板按下之后网关收到消息转发给德能森,德能森再决定此面板可以干啥->)
# 如果去掉德能森之后,必须把德能森要做的事情一并处理了.
# 所以此处依旧从 dev_rep_list.txt 中提取.

BUILTIN_SCENE_STR: str = '''
# 以#开始可以认为是注释, 大概可以这样  格式: 
# 场景名 面板地址 面板channel(德能森数据库有), 关联设备名(name支持特殊:all|all_light all_cover), 支持的功能:turn_on|turn_off|toggle
主卧床头纱帘按键, abcdef, 4,    主卧纱帘, toggle
'''


# 德能森内置灯具和窗帘
# grep -E 'blind|light' dev_rep_list.txt  | grep -v '^light' | cut -d, -f1-3
BUILTIN_DEVICES_STR = '''
# 设备名, 设备类型(light|blind) 设备地址。 这个可以在德能森数据库中找到
生活阳台灯,     light,  abcedef
'''
