# 德能森(纯净版)

> 该版本还在开发中,大多数功能都未测试
> 该版本只支持 窗帘/灯具。 空调需要搭配 [zhong_hong](https://www.home-assistant.io/integrations/zhong_hong/) 使用
> 该方案旨在去掉德能森中控以及 mqtt.资料: 思路可以参见这里[德能森分析](https://docs.qq.com/doc/DQmNHdnFpVlF3UWVZ)
> 该代码在 `hass-2022.10.5` 版本下成功运行

因为没有文档，所有内容均为主观臆断。

其中所有协议分析等逻辑均位于 `hub.py` 文件中。代码基本上都是抄袭由 [@crhan](https://github.com/crhan) 几年前开发的[中弘网关](https://github.com/crhan/ZhongHongHVAC/tree/master/zhong_hong_hvac)

如果您不介意使用德能森的服务，依旧可以使用原来的 [v1.0.0](https://github.com/shellvon/deocean/tree/v1.0.0) 版本。该版本仅在 hass 2021.10.6 版本中测试通过 具体参见 [版本 1.0.0 变更文档](https://github.com/shellvon/deocean/releases/tag/v1.0.0)

# 已知限制

    - 不知道怎么发现网关 IP 以及端口(自动)
    - 不知道怎么列出所有设备以及场景(模拟了发送，但实际返回的不全)

由于以上限制，所以已有的设备/场景需要人工添加进去.因此提供了 `register_devices` 以及 `register_scenes` 帮助完成注册.

# 使用指南

0. 关闭德能森现有服务: `/home/deocean_v2/stop.sh` 以让本集成可以正常连
1. 把 `const.example.py` 替换成 `const.py` 并按说明配置好设备/场景
2. 将本项目放入 hass 的 `config/custom_components` 目录。如果没有则新建
3. 进入 hass 后台，在集成中搜索 `deocean` 或者 `德能森` 即可

# 调试方式

代码内大部分日志都是 `DEBUG` 你可以参考 [此处](https://www.home-assistant.io/integrations/logger/) 配置查看日志:

```yaml
# Example configuration.yaml entry
logger:
  default: info
  logs:
    custom_components.deocean: debug
```
