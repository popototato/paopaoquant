# Streamlit Community Cloud 部署指南（新手向）

本文只讲 **GitHub + [Streamlit Community Cloud](https://share.streamlit.io)** 托管完整应用（`streamlit run app.py`）。  
Vercel 仅适合静态交易面板预览，见 [DEPLOY.md](./DEPLOY.md)。

---

## 部署前检查清单

在推送到 GitHub 之前，请确认：

| 项 | 状态 | 说明 |
|----|------|------|
| `.python-version` | 建议 `3.12` | 本地/CI 对齐；Cloud **部署时**在 Advanced settings 选 **3.12**（勿用 3.14） |
| `requirements.txt` | 已包含 | `streamlit>=1.57,<1.58`（**勿**用 `>=1.28`，否则缺 `st.Page`）、`backtrader`、`pandas`、`numpy`、`requests`、`altair` |
| `packages.txt` | 空文件即可 | 无额外系统依赖 |
| 入口文件 | `app.py` | Cloud 里 **Main file path** 填 `app.py` |
| `static/trading_panel/` | **已提交到 Git** | Cloud **默认不会**跑 `npm build`，需本地构建后 push |
| `.streamlit/config.toml` | 主题 + static 服务 | 已启用 `[server] enableStaticServing`（首页面板走 `/app/static/`） |
| `eth.csv` | **不要提交** | 已在 `.gitignore`；上线后在应用内下载 |
| 密钥 | **不要提交** | 用 Cloud Secrets 或本地 `secrets.toml`（见下文） |
| `git remote` | 需自行添加 | 当前仓库若 `git remote -v` 无输出，先关联 GitHub 再 push |

### 前端构建（重要）

Streamlit Cloud 的 Python 环境**通常没有 Node.js**，不会在部署时自动执行 `frontend` 构建。

**推荐做法（已为本仓库准备好构建产物时）：**

```bash
cd /Users/fanxuelin/Desktop/paopaoquant
# 若你修改了 frontend 源码，本地重新构建：
cd frontend && npm install && npm run build && cd ..
git add static/trading_panel/
git commit -m "更新交易面板构建产物"
```

构建输出目录：`static/trading_panel/`（`index.html` + `assets/`）。  
请确认 `git ls-files static/trading_panel/` 能看到这些文件再推送。

---

## 第一步：在 GitHub 创建空仓库

1. 浏览器打开 [https://github.com/new](https://github.com/new)
2. **Repository name**：例如 `paopaoquant`
3. 选择 Public 或 Private（Cloud 均支持私有仓库，需授权）
4. **不要**勾选 “Add a README file”（本地已有代码和提交）
5. 点击 **Create repository**

记下仓库地址，形如：

`https://github.com/GITHUB_USERNAME/paopaoquant.git`

（将 `GITHUB_USERNAME` 换成你的 GitHub 用户名。）

---

## 第二步：本地关联远程并推送

在项目目录执行：

```bash
cd /Users/fanxuelin/Desktop/paopaoquant

# 确认没有误加敏感/大文件
git status
# 不应出现：eth.csv、.streamlit/secrets.toml、.env

# 若尚未配置远程（git remote -v 无输出时执行）：
git remote add origin https://github.com/GITHUB_USERNAME/paopaoquant.git

# 当前默认分支为 master；若你希望与 GitHub 默认 main 一致：
# git branch -M main

git push -u origin master
# 若已改名为 main：git push -u origin main
```

首次 push 会提示 GitHub 登录（HTTPS）或需配置 SSH 密钥。

**请勿使用** `git push --force`，尤其不要 force 到 `main`/`master`。

### 若本地还没有任何提交

```bash
git add .
git commit -m "初始提交：泡泡量化 Streamlit 应用"
git remote add origin https://github.com/GITHUB_USERNAME/paopaoquant.git
git push -u origin master
```

---

## 第三步：在 Streamlit Cloud 创建应用

1. 打开 [https://share.streamlit.io](https://share.streamlit.io)
2. 用 **GitHub** 登录，按提示授权访问仓库
3. 点击 **Create app**（或 **New app**）
4. 填写：
   - **Repository**：`GITHUB_USERNAME/paopaoquant`
   - **Branch**：`master`（或你使用的 `main`）
   - **Main file path**：`app.py`
5. **Advanced settings**（强烈建议）：
   - **Python version**：选择 **3.12**（或 3.11）。Cloud 若默认到 **3.14** 等过新版本，部分依赖可能不兼容。
   - 仓库根目录的 `.python-version`（内容为 `3.12`）用于本地与文档对齐；**已部署应用无法在设置里改 Python**，需删除应用后按相同仓库重新 Deploy 并在此下拉框选 3.12。
6. 点击 **Deploy**

首次部署会安装 `requirements.txt` 中的依赖，约 2–5 分钟。  
成功后地址类似：`https://paopaoquant-xxxx.streamlit.app`

---

## 第四步：Secrets（可选）

当前版本使用 **Binance 公开 REST API**，不配置密钥也能运行回测下载与首页行情。

### 本地开发

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# 编辑 .streamlit/secrets.toml（该文件已在 .gitignore，不会进 Git）
```

### Streamlit Cloud

1. 打开已部署应用的 **⋮** 菜单 → **Settings**
2. 左侧 **Secrets**
3. 粘贴 TOML，例如（按需取消注释）：

```toml
# 示例 — 当前功能可不填
# [binance]
# api_key = "your-key"
# api_secret = "your-secret"
```

4. **Save** 后应用会自动重启

**切勿**把真实密钥写进仓库或截图公开。

---

## 第五步：上线后下载 `eth.csv`

`eth.csv` 约 150MB+，**不能**放进 Git（已在 `.gitignore`）。

1. 打开云端应用 → **有限层级均值回归网格策略回测** 页面  
2. 在侧栏使用 **从 Binance 下载 / 更新数据**（具体文案以界面为准）  
3. 等待进度完成；数据保存在 Cloud 实例的工作目录（重启应用可能需重新下载，属免费 tier 限制）

本地开发同样在应用内下载，或自行放到项目根目录命名为 `eth.csv`。

---

## 常见问题

### 1. `ModuleNotFoundError: No module named 'altair'`

确保仓库根目录 `requirements.txt` 含 `altair>=5.0.0`，保存后 Cloud 会重新部署。

### 2. 首页交易面板空白 / 404

- 未提交 `static/trading_panel/`：在本地 `cd frontend && npm run build`，再 `git add static/trading_panel/` 并 push  
- 浏览器缓存：强制刷新或无痕窗口

### 3. 回测页提示找不到 `eth.csv`

正常：先在应用内下载数据，不要尝试把 `eth.csv` 提交到 GitHub。

### 4. Binance 下载失败或很慢

- **HTTP 451 / 403**：Binance 主站 `api.binance.com` 会按服务器所在地区拒绝请求（Streamlit Cloud 上较常见）。本仓库 `data.py` 会自动改用公开数据端点 `data-api.binance.vision`；若仍失败，请稍后重试或在本地下载 `eth.csv` 后放到实例工作目录。  
- 若超时，稍后重试；全量下载约 5 年 1 分钟线，耗时较长。  
- 检查 Binance API 是否临时限流（HTTP 429 会自动等待重试）。

### 5. `git push` 被拒绝（rejected）

- 远程已有提交而本地没有：先用 `git pull origin master --rebase`（**不要**随意 `--force`）  
- 未登录：配置 `gh auth login` 或 SSH key

### 6. 部署成功但页面一直 “Running…”

- 查看 Cloud 日志 **Manage app → Logs**  
- 常见原因：依赖安装失败、入口文件路径不是 `app.py`

### 7. 修改代码后未更新

推送到 GitHub 同一分支后，Cloud 通常会自动重建；也可在控制台点 **Reboot app**。

### 8. 「Oh no. Error running app」或日志里 `ConnectionClosedError: keepalive ping timeout`

**常见原因**：首页在每次 rerun 时同步内联约 **450KB** 的 React 构建 JS，首屏脚本执行过久，WebSocket 保活超时。

**本仓库已做缓解**：

- 交易面板改为 `st.iframe("/app/static/trading_panel/index.html")`，由浏览器按需加载 `static/trading_panel/assets/`，不再在 Python 侧内联整包 JS。
- `.streamlit/config.toml` 中 `enableStaticServing = true`。
- 默认 iframe 高度由 2600px 降为 **1600px**。
- `requirements.txt` 使用 `streamlit>=1.57,<1.58`，并迁移 `st.components.v1.html` → `st.iframe`（1.57 起弃用旧 API）。

**若仍失败**：

1. 在 **Manage app → Logs** 确认 Python 是否为 **3.12**（若为 3.14，删除应用后重新 Deploy 并在 Advanced settings 选 3.12）。
2. 确认 `git ls-files static/trading_panel/` 含 `index.html` 与 `assets/*.js`。
3. 强制刷新浏览器或无痕窗口；必要时 **Reboot app**。

### 9. 日志提示 `replace st.components.v1.html with st.iframe`

Streamlit 1.57+ 弃用 `st.components.v1.html`。本仓库 `chart_component.py` 已改用 `st.iframe`；推送后重建即可消除该警告。

### 10. 日志里 `AttributeError: module 'streamlit' has no attribute 'Page'`

**原因**：`app.py` 使用 `st.Page` / `st.navigation`（Streamlit **1.36+**），但 Cloud 仍按旧版 `requirements.txt`（例如 `streamlit>=1.28.0`）安装了 **1.32 或更早**，启动即崩溃，页面只显示 **「Oh no. Error running app」**。

**修复**：

1. 确认本地 `requirements.txt` 为 `streamlit>=1.57,<1.58`（或至少 `>=1.36.0`）。
2. `git push` 到 Cloud 所跟踪的分支（如 `master`）。
3. 在 **Manage app → Logs** 确认安装日志出现 `streamlit-1.57.x`。
4. 必要时 **Reboot app**。

`app.py` 在版本过低时会显示中文错误提示而非裸崩溃；若仍见 Oh no，以 Logs 堆栈为准。

### 11. 依赖安装失败（`backtrader` / `numpy` / `altair`）

在 Logs 的 **Installing dependencies** 阶段搜索 `ERROR`：

- `No matching distribution`：检查 Cloud Python 版本（建议 **3.12**）。
- `backtrader` 编译失败：极少见；可暂时在 Logs 确认是否完整安装 `backtrader-1.9.x`。
- 缺 `numpy`：本仓库已在 `requirements.txt` 显式声明 `numpy>=1.24.0`（`pandas`/`altair` 的传递依赖有时在 Cloud 上未装上）。

### 12. Cloud Logs 应重点看什么

| 阶段 | 关键字 | 含义 |
|------|--------|------|
| 安装 | `Successfully installed streamlit-1.57` | 版本正确，支持 `st.Page` |
| 安装 | `streamlit-1.3` 或 `1.32` | 版本过低，会触发 §10 |
| 运行 | `AttributeError: ... Page` | 同 §10，需更新 `requirements.txt` 并 push |
| 运行 | `ModuleNotFoundError` | 缺包，对照 `requirements.txt` 补全后 push |
| 运行 | `keepalive ping timeout` | 首屏过重，见 §8；确认已 push 使用 `st.iframe` 的 `chart_component.py` |
| 运行 | `FileNotFoundError` / `eth.csv` | 正常，进回测页下载即可 |
| 运行 | `BinanceKlinesError` / `451` | 地区限制，见 §4 |

---

## 与本仓库相关的文件一览

| 文件 | 作用 |
|------|------|
| `app.py` | Streamlit 入口（顶部导航） |
| `requirements.txt` | Python 依赖 |
| `.python-version` | 本地推荐 Python 3.12（Cloud 以 Deploy 时 Advanced settings 为准） |
| `packages.txt` | 系统 apt 包（本项目为空） |
| `.streamlit/config.toml` | 深色主题 + static 文件服务 |
| `.streamlit/secrets.toml.example` | 密钥模板（复制为本地 secrets，勿提交） |
| `static/trading_panel/` | React 面板构建产物（需进 Git） |
| `eth.csv` | 仅运行时数据，**禁止**提交 |

---

## 快速命令汇总（复制用）

将 `GITHUB_USERNAME` 替换为你的 GitHub 用户名：

```bash
cd /Users/fanxuelin/Desktop/paopaoquant
cd frontend && npm install && npm run build && cd ..
git status   # 确认无 eth.csv / secrets.toml
git remote add origin https://github.com/GITHUB_USERNAME/paopaoquant.git   # 仅首次
git push -u origin master
```

然后在 [share.streamlit.io](https://share.streamlit.io) 选择该仓库，**Main file path** = `app.py`，Deploy。

更多 VPS / Vercel 方案见 [DEPLOY.md](./DEPLOY.md)。
