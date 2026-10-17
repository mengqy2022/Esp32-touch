# Codex / Claude Code 用量与人民币费用估算

该功能读取本机日志，提供桌面设备上的用量参考。它没有连接账单接口，
不展示套餐剩余额度，也不代表实际扣款。

## 来源与计数

默认目录为环境变量 `CODEX_HOME`；未设置时使用 `~/.codex`，扫描
`sessions/` 和 `archived_sessions/` 的 JSONL 文件。
终端主机可用 `--codex-home` 覆盖，`--no-codex` 关闭统计。

`codex_usage.py` 按行读取，只解析用量 `event_msg/token_count` 和模型
`turn_context` 信息。原始日志行可能含对话，但程序跳过非目标行的 JSON 解析，
不保存／向设备传送提示词、回复内容、认证文件或 API Key。

- 今日按电脑本地时区统计；设备接收日期和 PC 同步的时间／时区。
- 今日总 Token = 输入＋输出。缓存输入已经计入输入，推理 Token 不额外累加。
- 取累计计数的差值，重复快照不重复统计；计数重置时重新建立增量。
- 首条／fork 首条优先使用 `last_token_usage`，避免继承总数重复计算。
  若缺少该字段，会回退到累计数；异常或不完整日志仍可能影响准确性。
- 保留文件读取偏移，尚未写完的最后一行留待下次读取。
- 跨日重新按今日事件汇总，归档移动不重复累加，删除文件会影响可重建总数。

刷新默认约 5 秒。没有可读的有效用量事件时发送不可用状态，设备显示 NO DATA。
有有效事件但今日没有新增用量时，可以显示 0。计数源是本地实现细节，
日志格式变化可能需要调整程序。不同电脑、删除过的日志、服务器修正不在统计范围内。

## Claude Code 与来源切换

在设备主页点选 `CODEX` 或 `CLAUDE` 按钮，分别查看各自的 Token 和金额，设备会记住选择。
电脑发送两套独立数据，刷新和重连不覆盖设备选择。EXE 控制窗口提供备用入口。
Claude Code 从 `CLAUDE_CONFIG_DIR` 或 `~/.claude` 下
`projects/**/*.jsonl` 读取 assistant 消息的 `message.usage`，包含子代理日志。
按消息 ID 和请求 ID 去重，使用最新快照，避免同一回复的多段记录重复累计。
半行留待下次读取；跨日重建。日志缺失、删除、格式变化仍会影响结果。

Claude 今日总 Token 包含普通输入、缓存读取、缓存写入、输出。Anthropic 的
`input_tokens` 不含缓存字段，读取时会将两类缓存补入输入总量，再使用下方统一公式。
缺少模型单价时保留 Token，金额显示不可用。仅为配置中明确的模型名称计价。
切换后 Token 和金额一起更新；所选来源不可读时显示 `--`，不借用另一个来源的数据。
已删除 AI 每日目标、限额配置与进度条，词汇学习计划不受影响。

## 默认示例单价

**以下是使用者提供并确认的配置示例，未独立核实为官方价格。**
模型标识按日志中的精确名称匹配。每列单位为 **美元／百万 Token**，
默认 `usd_to_cny = 7.20`，可编辑。

| 模型 | 档位 | 普通输入 | 缓存读取 | 缓存写入 | 输出 |
| --- | --- | ---: | ---: | ---: | ---: |
| gpt-6-astra | 短上下文 ≤272,000 | 2.00 | 0.20 | 2.50 | 10.00 |
| gpt-6-astra | 长上下文 >272,000 | 4.00 | 0.40 | 5.00 | 15.00 |
| gpt-6.1-sol | 短上下文 ≤272,000 | 0.40 | 0.02 | 0.50 | 2.00 |
| gpt-6.1-sol | 长上下文 >272,000 | 0.80 | 0.04 | 1.00 | 3.00 |
| claude-fable-5-1 | 统一档位 | 3.00 | 0.075 | 3.75 | 15.00 |

Codex 优先读取事件的 `context_tokens`，缺少时使用 `last_token_usage.input_tokens`，
再缺少才回退到输入增量。超过 272,000 为长档，恰好 272,000 为短档。
日志未必暴露真实计费上下文，因此缺少显式上下文时分档是近似值。日志未提供缓存写入时
按 0 处理，同样是基于日志可见字段的假设。

## 计算方法

```text
普通输入 = input_tokens - cached_input_tokens - cache_write_input_tokens
人民币估算 = 汇率 × (
    普通输入 × 普通输入单价
  + 缓存读取 × 缓存读取单价
  + 缓存写入 × 缓存写入单价
  + 输出 × 输出单价
) / 1,000,000
```

按模型与档位累加后，使用 Decimal 计算，总额一次四舍五入到人民币分。
串口发送整数分，设备显示 `~¥` 和两位小数。

例：gpt-6.1-sol 短档，输入 100,000，其中缓存读取 80,000、缓存写入 0，
输出 10,000；美元估算为 `0.02×0.4 + 0.08×0.02 + 0.01×2 = 0.0296`，
乘 7.20 后为 0.21312 元，显示约 `~¥0.21`。

当任何已消耗用量缺少模型价格／必要细分，或价格格式无效时，金额显示 `~¥--`，
不会把可估算部分当成完整总额。Tokens 仍可正常显示。
已保留当日数据会应用当前价格重新估算，没有历史价格版本／生效日期机制。

## 配置

源码模板：[tools/codex_prices.json](../tools/codex_prices.json)。
已安装程序使用 `%LOCALAPPDATA%/ESP32TouchDashboard/codex_prices.json`。
首次安装复制模板。升级时自动替换与旧内置 USD 单价完全一致的两组 GPT 配置，
并加入缺失的 Claude 单价，备份为 `codex_prices.before-2026-10-17.json`；
自定义单价、汇率和其他模型保留。CNY 自定义文件不注入 USD 单价，请自行补充。

```json
{
  "currency": "USD",
  "usd_to_cny": 7.20,
  "source": "My configured rates; estimate only",
  "models": {
    "gpt-6.1-sol": {
      "short": {
        "input_per_million": 0.4,
        "cached_input_per_million": 0.02,
        "cache_write_input_per_million": 0.5,
        "output_per_million": 2
      },
      "long": {
        "input_per_million": 0.8,
        "cached_input_per_million": 0.04,
        "cache_write_input_per_million": 1,
        "output_per_million": 3
      }
    }
  }
}
```

也支持 `currency: "CNY"`，此时单价直接按人民币／百万 Token，不乘汇率。
模型可按示例分 `short`、`long`，也可直接放一组单价用于两个档位。
代码支持 `"*"` 默认模型价格，但建议为每个实际模型明确配置，避免不同模型套用错误价格。
汇率必须是有限正数，单价必须是有限非负数。

终端运行要显式指定价格文件，否则金额显示不可用：

```powershell
python tools/pc_monitor_host.py --port COM5 --codex-prices tools/codex_prices.json
```

终端默认保留设备选择并发送两套独立数据。显式 `--ai-source codex|claude` 仅在启动时选择一次，`--claude-home` 指定 Claude Code 目录。
串口字段与兼容性见 [PROTOCOL.md](PROTOCOL.md)，安装操作见
[Windows 软件手册](WINDOWS_APP_CN.md)。
