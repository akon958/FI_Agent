# Family_Investment_Agent

家庭投资雷达 Agent 是一个给父母使用的手机网页工具。它只做家庭投资风险体检和学习参考，不荐股，不预测明天涨跌，不自动交易，也不承诺收益。

## 主要功能

- 输入家庭现金、风险承受能力、多只股票或基金持仓。
- 默认支持 3 行持仓，可以继续增加持仓行。
- 支持输入任意 A 股代码。程序会优先通过 AkShare 查询真实行情。
- 如果真实接口失败，会自动读取 `stock_metrics.csv` 本地缓存。
- 页面提供“更新全部 A 股行情缓存”按钮，可以把本地缓存逐步扩展到更多 A 股。
- 页面提供“更新当前持仓财务缓存”按钮，会尝试为当前填写的股票补充财务指标。
- 如果真实接口和本地缓存都没有该股票，会显示“数据缺失”，不会强行给绿色评级。
- 输出综合评分、红黄绿风险等级、数据状态、家庭仓位、资产配置饼图、持仓明细、风险提示、家人建议和 txt 报告。

## 重要说明

这个项目不是完整行情软件。它的目标是家庭风险体检：

- 行情数据：优先查 AkShare，失败后用本地缓存。
- 财务数据：真实接口能拿到就更新，拿不到就用缓存；缺失时会保守降级。
- 云端部署时，缓存文件可能是临时写入，重启后可能回到 GitHub 仓库里的初始 CSV。

## 项目结构

```text
Family_Investment_Agent/
├── app.py
├── analyzer.py
├── data_fetcher.py
├── report_generator.py
├── stock_metrics.csv
├── requirements.txt
└── README.md
```

## 本地运行

进入项目目录：

```powershell
cd C:\Users\Administrator\Desktop\FI_Agent\Family_Investment_Agent
```

安装依赖：

```powershell
pip install -r requirements.txt
```

启动网页：

```powershell
streamlit run app.py
```

浏览器打开：

```text
http://localhost:8501
```

如果 Windows 上 `pip` 或 `streamlit` 命令不可用，可以使用：

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## 手机访问本地网页

手机和电脑连接同一个 Wi-Fi。启动 Streamlit 后，终端会显示类似下面的地址：

```text
Network URL: http://192.168.x.x:8501
```

在手机浏览器打开这个 `Network URL` 即可。如果打不开，请检查 Windows 防火墙是否允许 Python 或 Streamlit 访问局域网。

## 部署到 Streamlit Community Cloud

1. 打开 [GitHub](https://github.com/) 并登录。
2. 点击右上角 `+`，选择 `New repository`。
3. Repository name 填：

```text
Family_Investment_Agent
```

4. 选择 `Public`，然后点击 `Create repository`。
5. 上传本项目根目录中的 7 个文件：

```text
app.py
requirements.txt
analyzer.py
data_fetcher.py
report_generator.py
stock_metrics.csv
README.md
```

6. 打开 [Streamlit Community Cloud](https://share.streamlit.io/) 并登录。
7. 点击 `New app`。
8. 选择刚创建的 GitHub 仓库。
9. 部署参数填写：

```text
Repository: 你的用户名/Family_Investment_Agent
Branch: main
Main file path: app.py
```

10. 点击 `Deploy`。

## 数据缓存使用

`stock_metrics.csv` 同时是示例数据和本地缓存文件。字段包括：

- 基础信息：股票代码、股票名称、所属行业。
- 行情与交易热度：最新收盘价、涨跌幅、换手率、量比、振幅、成交额、内外盘比例。
- 财务质量：ROE、净利率、毛利率、营收增长率、净利润增长率、资产负债率、经营现金流/净利润。
- 数据来源、更新时间。

建议使用方式：

1. 第一次打开页面，先点“数据缓存工具”。
2. 点“更新全部 A 股行情缓存”，让缓存覆盖更多股票。
3. 输入家里的持仓代码和金额。
4. 如需补充财务指标，点“更新当前持仓财务缓存”。
5. 点“开始体检”查看风险颜色和家人建议。

如果 AkShare 接口失败，页面仍会继续使用本地缓存，不会崩溃。

## 免责声明

本工具仅用于家庭投资风险体检和学习参考，不构成投资建议。市场有风险，投资需谨慎。

本工具不预测明天涨跌，不自动交易，不承诺收益，也不会输出确定性的买卖建议。
