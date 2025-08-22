# 德能森(纯净版)

> 最新版支持 `hass-2024.5.5`

> 该版本只支持 窗帘/灯具。 空调需要搭配 [zhong_hong](https://www.home-assistant.io/integrations/zhong_hong/) 使用
> 该方案旨在去掉德能森中控以及 mqtt。资料: 思路可以参见这里[德能森技术分析](https://docs.qq.com/doc/DQmNHdnFpVlF3UWVZ)

> 德能森关闭方式: 编辑 `/etc/rc.local` 文件，将德能森的相关配置关闭。比如像如下注释: 否则设备重启后可能会让 hass 失效（因为 hass 启动可能更慢）

```bash
#cd /home/deocean
#./daemon_deocean.sh &
#cd /home/deocean_v2
#./start.sh &
#./deocean_daemon.sh &
#exit 0
```

因为没有文档，所有内容均为主观臆断。

其中所有协议分析等逻辑均位于 `hub.py` 文件中。代码基本上都是抄袭由 [@crhan](https://github.com/crhan) 几年前开发的[中弘网关](https://github.com/crhan/ZhongHongHVAC/tree/master/zhong_hong_hvac)

如果您不介意使用德能森的服务，依旧可以使用原来的 [v1.0.0](https://github.com/shellvon/deocean/tree/v1.0.0) 版本。该版本仅在 hass 2021.10.6 版本中测试通过 具体参见 [版本 1.0.0 变更文档](https://github.com/shellvon/deocean/releases/tag/v1.0.0)

# 已知限制

    - 不知道怎么发现网关 IP 以及端口(自动)
    - 不知道怎么列出所有设备以及场景(模拟了发送，但实际返回的不全)
    - 网关只能被一个hub.py 链接，若不停止原有的德能森服务，新的hub.py无法连接

由于以上限制，所以已有的设备/场景需要人工添加进去.因此提供了 `register_devices` 以及 `register_scenes` 帮助完成注册。

> 需要注意的是，需要先注册设备，才可以注册场景。因为场景是按照设备名查找的。否则没有设备的场景会被忽略。更多细节参见源代码。

## 安装方法

现在支持完全通过 UI 进行配置，无需手动创建和编辑 `const.py` 文件啦！

### 通过 HACS 安装（推荐）

1. 确保已安装 [HACS](https://hacs.xyz/)
2. 在 HACS 中添加自定义存储库：
   - 进入 HACS → 集成
   - 点击右上角三个点 → 自定义存储库
   - 添加存储库 URL：`https://github.com/shellvon/deocean`
   - 类别选择：集成
3. 搜索"德能森"并安装
4. 重启 Home Assistant

### 手动

1. 将 custom_components 下的所有内容复制到 Home Assistant 的 `custom_components` 目录下
2. 重启 Home Assistant
3. 在集成页面添加"德能森"集成

## 设备配置格式

> 这些设备信息可以从之前德能森的 `dev_rep_list.txt` 获取。当然也可以直接查看她的 sqlite 数据库。
> grep -E 'blind|light' dev_rep_list.txt | grep -v '^light' | cut -d, -f1-3

### 内置场景配置

这是一个关于德能森（Deocean）内置场景的设备配置文件，用于管理面板触发的自动化操作。该配置以类似 **CSV** 的格式定义，每行代表一个场景。

**格式说明：**

```
# name, addr, channel, devices, op
```

- `name`: **场景名称**，例如 "离家"、"回家"、"开帘" 等。
- `addr`: **面板地址**，一个十六进制字符串，如 `0x0A0B0C0D`。
- `channel`: **面板通道**，一个整数，表示面板上的特定按键。
- `devices`: **关联设备**，多个设备名可以使用 `|` 分隔。
  - 特殊设备名：
    - `all`: 所有设备，不区分类型。
    - `all_light`: 所有灯具设备。
    - `all_cover`: 所有窗帘设备。
  - 你也可以为特定设备单独指定操作，格式为 `设备名:操作`。
- `op`: **通用操作**，当 `devices` 中没有为特定设备指定操作时，将使用此操作。
  - 支持的操作：`turn_on` (开启), `turn_off` (关闭), `toggle` (切换状态)。

**配置示例：**

```
# 示例 1: 离家场景
# 离家, 0x0A0B0C0D, 1, all_light|主卧纱帘, turn_off
# 解释: 当按下地址为 0x0A0B0C0D 的面板的通道 1 时，所有灯具和名为“主卧纱帘”的窗帘都会执行 turn_off 操作。

# 示例 2: 回家场景
# 回家, 0x0A0B0C0D, 2, all_light:turn_off|客厅布帘|过道灯:toggle, turn_on
# 解释: 当按下通道 2 时，所有灯具会执行 turn_off，而“客厅布帘”会执行通用的 turn_on 操作，“过道灯”则会执行 toggle 操作。
# 注意: 各操作是异步执行的，如果一个设备同时被通用操作和特定操作指定，会按从左到右的顺序执行。比如，过道灯会先被 all_light 里的 turn_off 关闭，然后再被 toggle 一次。

# 示例 3: 开帘场景
# 开帘, 0x0A0B0C0D, 3, 主卧纱帘:80
# 解释: 当按下通道 3 时，名为“主卧纱帘”的窗帘将打开到 80% 的位置。
```

---

### 内置设备配置

此配置用于定义内置的灯具和窗帘设备，这些信息可以从德能森的数据库中获取。我是通过 `grep -E 'blind|light' dev_rep_list.txt | grep -v '^light' | cut -d, -f1-3` 获取的。

**格式说明：**

```
# 设备名, 设备类型, 设备地址
```

- `设备名`: 设备的友好名称，如 `生活阳台灯`。
- `设备类型`: 设备的类型，目前支持 `light` (灯具) 或 `blind` (窗帘)。
- `设备地址`: 设备的十六进制地址。

**配置示例：**

```
# 设备名,     设备类型, 设备地址
# 生活阳台灯, light,    abcedef
```

### 后续管理

配置完成后，您可以通过集成的选项菜单：

- 管理所有设备配置
- 管理所有场景配置
- 添加单个设备
- 添加单个场景

# 调试方式

代码内大部分日志都是 `DEBUG` 你可以参考 [此处](https://www.home-assistant.io/integrations/logger/) 配置查看日志:

```yaml
# Example configuration.yaml entry
logger:
  default: info
  logs:
    custom_components.deocean: debug
```

如果不想直接在 `hass` 内调试，你可以直接 执行 `python3 -m deocean.hub` 执行相关测试。 [hub.py](./custom_components/deocean/hub.py) 内的代码随意修改调.

如果不需要以相对目录导入，可以不以 `module` 形式执行。直接 `python3 deocean/hub.py` 即可。

# 其他您可能需要的

- 德能森配套的 [NanoPI-Neo-Plus2](http://nanopi.io/nanopi-neo-plus2.html) 以及[其 Wiki 资料](https://wiki.friendlyelec.com/wiki/index.php/NanoPi_NEO_Plus2)
- 集成 [HomeKit](https://www.home-assistant.io/integrations/homekit/) 以让苹果的家庭 APP 无缝衔接
- 集成 [ZhongHong](https://www.home-assistant.io/integrations/zhong_hong/) 以让空调一起加入苹果大家庭- 集成 [SmartIR](https://github.com/smartHomeHub/SmartIR) 以让支持红外设备的（比如电视）加入苹果
- 如何开发一个 Hass 插件的[开发者文档](https://developers.home-assistant.io/docs/creating_component_index)

# Change Logs

- **25.08.22** 完全 UI 化配置，无需手动编辑配置文件，引入 hacs.json 使其支持 hacs 安装
- **24.05.28** 使用新版 HA API 以修复`Deprecated` 提示和删除没用日志,并将版本号设置为`1.1.0`
- **22.11.04** 去掉 MQTT 等外部依赖，改为自己实现网关
- **21.10.09** 首个版本
