# Family_Investment_Agent

家庭投资雷达 Agent 是一个给父母使用的手机网页工具。它只做家庭投资风险体检和学习参考，不荐股，不预测明天涨跌，不自动交易，也不承诺收益。

## 主要功能

- 输入家庭现金、风险承受能力、多只股票或基金持仓。
- 默认支持 3 行持仓，可以继续增加持仓行。
- 页面默认优先读取 `stock_metrics.csv`，不会在 Streamlit Cloud 每次启动时自动抓全市场行情。
- 可以在"高级选项：数据缓存工具"里手动更新当前持仓数据。
- "更新全部 A 股行情缓存"也放在高级选项里，接口可能失败，失败时页面会继续使用本地缓存。
- 如果本地缓存没有该股票，会显示"数据缺失"，不会强行给绿色评级。
- 输出综合评分、红黄绿风险等级、数据状态、家庭仓位、资产配置饼图、持仓明细、风险提示、家人建议和 txt 报告。
- 可选接入 DeepSeek AI，点击"生成 AI 风险说明"按钮后，AI 会用通俗语言把体检结果解释给父母听。

## AI 风险说明功能（可选）

本工具支持接入 DeepSeek API，生成适合父母阅读的通俗风险说明。

**AI 功能的原则：**
- 不荐股，不预测涨跌，不给出买入、卖出、加仓、减仓指令
- 只做家庭投资风险体检说明
- 语言口语化，适合没有金融背景的父母阅读
- 页面启动时不会自动调用，只有用户点击按钮才会请求 AI
- 未配置 API Key 时，页面显示"未配置 AI 分析功能"，其他体检功能完全正常

### 如何在 Streamlit Cloud 配置 DEEPSEEK_API_KEY

1. 打开你的 Streamlit Cloud 应用管理页面：
   [https://share.streamlit.io/](https://share.streamlit.io/)

2. 找到你的 `Family_Investment_Agent` 应用，点击右侧的 **⋮（三个点）** 菜单，选择 **Settings**。

3. 在弹出页面中点击左侧的 **Secrets** 选项卡。

4. 在文本框中输入以下内容（替换为你自己的 Key）：

   ```toml
   DEEPSEEK_API_KEY = "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
   ```

5. 点击 **Save** 保存。Streamlit Cloud 会自动重启应用，Key 生效。

**注意事项：**
- API Key 只保存在 Streamlit Secrets 中，不要写进任何代码文件或提交到 GitHub。
- 如果不需要 AI 功能，不配置 Key 即可，体检功能完全不受影响。
- DeepSeek API Key 可以在 [https://platform.deepseek.com/](https://platform.deepseek.com/) 注册后获取。

### 如何在本地使用 AI 功能

在项目根目录创建 `.streamlit/secrets.toml` 文件（此文件已在 `.gitignore` 中，不会被提交到 GitHub）：

```toml
DEEPSEEK_API_KEY = "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

然后正常启动：

```bash
streamlit run app.py
```

## 重要说明

这个项目不是完整行情软件。它的目标是家庭风险体检：

- 行情数据：默认读取 `stock_metrics.csv`。
- 手动更新：本地运行 `python update_cache.py` 或在页面高级选项里点击更新按钮。
- 财务数据：如果缓存里没有完整财务指标，会保守判断，最高不会轻易给绿色。
- 云端部署：Streamlit Cloud 会读取 GitHub 仓库中的 `stock_metrics.csv`。手机端使用时不依赖实时抓取。

## 项目结构

```
Family_Investment_Agent/
├── app.py               # 主页面
├── analyzer.py          # 风险分析逻辑
├── data_fetcher.py      # 数据读取与缓存
├── report_generator.py  # txt 报告生成
├── ai_report.py         # DeepSeek AI 风险说明（新增）
├── update_cache.py      # 本地更新缓存脚本
├── stock_metrics.csv    # 本地行情缓存
├── requirements.txt
└── README.md
```

## 本地运行

进入项目目录：

```
cd C:\Users\Administrator\Desktop\FI_Agent\Family_Investment_Agent
```

安装依赖：

```
pip install -r requirements.txt
```

启动网页：

```
streamlit run app.py
```

浏览器打开：

```
http://localhost:8501
```

如果 Windows 上 `pip` 或 `streamlit` 命令不可用，可以使用：

```
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## 本地更新 A 股缓存

在上传 GitHub 前，建议先在本地运行一次：

```
python update_cache.py
```

这个脚本会调用 AkShare 的 `stock_zh_a_spot_em()`，把沪深京 A 股行情保存到 `stock_metrics.csv`。缓存字段至少包括：

- 代码
- 名称
- 最新价
- 涨跌幅
- 成交额
- 市盈率-动态
- 市净率
- 换手率
- 总市值
- 流通市值

如果 AkShare 接口失败，脚本会提示：

```
实时行情更新失败，已使用本地缓存数据。
```

这时页面仍然可以使用已有的 `stock_metrics.csv`，不会崩溃。

## 手机访问本地网页

手机和电脑连接同一个 Wi-Fi。启动 Streamlit 后，终端会显示类似下面的地址：

```
Network URL: http://192.168.x.x:8501
```

在手机浏览器打开这个 `Network URL` 即可。如果打不开，请检查 Windows 防火墙是否允许 Python 或 Streamlit 访问局域网。

## 部署到 Streamlit Community Cloud

1. 打开 [GitHub](https://github.com/) 并登录。
2. 点击右上角 `+`，选择 `New repository`。
3. Repository name 填：

   ```
   Family_Investment_Agent
   ```

4. 选择 `Public`，然后点击 `Create repository`。
5. 上传本项目根目录中的文件：

   ```
   app.py
   requirements.txt
   analyzer.py
   data_fetcher.py
   report_generator.py
   ai_report.py
   update_cache.py
   stock_metrics.csv
   README.md
   ```

6. 打开 [Streamlit Community Cloud](https://share.streamlit.io/) 并登录。
7. 点击 `New app`。
8. 选择刚创建的 GitHub 仓库。
9. 部署参数填写：

   ```
   Repository: 你的用户名/Family_Investment_Agent
   Branch: main
   Main file path: app.py
   ```

10. 点击 `Deploy`。
11. 部署完成后，按照上方"如何在 Streamlit Cloud 配置 DEEPSEEK_API_KEY"的步骤配置 API Key（可选）。

## 上传 GitHub 后的数据逻辑

上传 GitHub 后，Streamlit Cloud 会直接读取仓库里的 `stock_metrics.csv`。因此：

- 手机端打开云端链接时，不需要每次实时抓 AkShare。
- 如果想更新缓存，先在本地运行 `python update_cache.py`。
- 然后把更新后的 `stock_metrics.csv` 再上传或提交到 GitHub。
- Streamlit Cloud 重新部署后，就会读取新的缓存。

## 免责声明

本工具仅用于家庭投资风险体检和学习参考，不构成投资建议。市场有风险，投资需谨慎。

本工具不预测明天涨跌，不自动交易，不承诺收益，也不会输出确定性的买卖建议。
