# 德能森(纯净版)

> 最新版支持 `hass-2024.5.5`

> 该版本只支持 窗帘/灯具。 空调需要搭配 [zhong_hong](https://www.home-assistant.io/integrations/zhong_hong/) 使用
> 该方案旨在去掉德能森中控以及 mqtt。资料: 思路可以参见这里[德能森技术分析](https://docs.qq.com/doc/DQmNHdnFpVlF3UWVZ)

因为没有文档，所有内容均为主观臆断。

其中所有协议分析等逻辑均位于 `hub.py` 文件中。代码基本上都是抄袭由 [@crhan](https://github.com/crhan) 几年前开发的[中弘网关](https://github.com/crhan/ZhongHongHVAC/tree/master/zhong_hong_hvac)

如果您不介意使用德能森的服务，依旧可以使用原来的 [v1.0.0](https://github.com/shellvon/deocean/tree/v1.0.0) 版本。该版本仅在 hass 2021.10.6 版本中测试通过 具体参见 [版本 1.0.0 变更文档](https://github.com/shellvon/deocean/releases/tag/v1.0.0)

# 已知限制

    - 不知道怎么发现网关 IP 以及端口(自动)
    - 不知道怎么列出所有设备以及场景(模拟了发送，但实际返回的不全)

由于以上限制，所以已有的设备/场景需要人工添加进去.因此提供了 `register_devices` 以及 `register_scenes` 帮助完成注册。

> 需要注意的是，需要先注册设备，才可以注册场景。因为场景是按照设备名查找的。否则没有设备的场景会被忽略。更多细节参见源代码。

# 使用指南

0. 关闭德能森现有服务: `/home/deocean_v2/stop.sh` 以让本集成可以正常连
1. 把 `const.example.py` 替换成 `const.py` 并按说明配置好设备/场景
2. 将本项目放入 hass 的 `config/custom_components` 目录。如果没有则新建
3. 进入 hass 后台，在集成中搜索 `deocean` 或者 `德能森` 即可

> 德能森关闭方式: 编辑 `/etc/rc.local` 文件，将德能森的相关配置关闭。比如像如下注释: 否则设备重启后可能会让 hass 失效（因为 hass 启动可能更慢）

```bash
#cd /home/deocean
#./daemon_deocean.sh &
#cd /home/deocean_v2
#./start.sh &
#./deocean_daemon.sh &
#exit 0
```

# 调试方式

代码内大部分日志都是 `DEBUG` 你可以参考 [此处](https://www.home-assistant.io/integrations/logger/) 配置查看日志:

```yaml
# Example configuration.yaml entry
logger:
  default: info
  logs:
    custom_components.deocean: debug
```

如果不想直接在 `hass` 内调试，你可以直接 执行 `python3 -m deocean.hub` 执行相关测试。 [hub.py](./hub.py) 内的代码随意修改调.

如果不需要以相对目录导入，可以不以 `module` 形式执行。直接 `python3 deocean/hub.py` 即可。

# 其他您可能需要的

- 德能森配套的 [NanoPI-Neo-Plus2](http://nanopi.io/nanopi-neo-plus2.html) 以及[其 Wiki 资料](https://wiki.friendlyelec.com/wiki/index.php/NanoPi_NEO_Plus2)
- 集成 [HomeKit](https://www.home-assistant.io/integrations/homekit/) 以让苹果的家庭 APP 无缝衔接
- 集成 [ZhongHong](https://www.home-assistant.io/integrations/zhong_hong/) 以让空调一起加入苹果大家庭- 集成 [SmartIR](https://github.com/smartHomeHub/SmartIR) 以让支持红外设备的（比如电视）加入苹果
- 如何开发一个 Hass 插件的[开发者文档](https://developers.home-assistant.io/docs/creating_component_index)

# Change Logs 

- **24.05.28** 使用新版 HA API 以修复`Deprecated` 提示和删除没用日志,并将版本号设置为`1.1.0`
- **22.11.04** 去掉MQTT等外部依赖，改为自己实现网关
- **21.10.09** 首个版本