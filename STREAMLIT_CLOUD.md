# Streamlit Community Cloud 部署指南（新手向）

本文只讲 **GitHub + [Streamlit Community Cloud](https://share.streamlit.io)** 托管完整应用（`streamlit run app.py`）。  
Vercel 仅适合静态交易面板预览，见 [DEPLOY.md](./DEPLOY.md)。

---

## 部署前检查清单

在推送到 GitHub 之前，请确认：

| 项 | 状态 | 说明 |
|----|------|------|
| `requirements.txt` | 已包含 | `streamlit`、`backtrader`、`pandas`、`requests`、`altair` |
| `packages.txt` | 空文件即可 | 无额外系统依赖 |
| 入口文件 | `app.py` | Cloud 里 **Main file path** 填 `app.py` |
| `static/trading_panel/` | **已提交到 Git** | Cloud **默认不会**跑 `npm build`，需本地构建后 push |
| `.streamlit/config.toml` | 主题配置 | 云端可用，无需改 `server` 段 |
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
5. **Advanced settings**（可选）：
   - Python version：保持默认（3.10+ 一般即可）
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

- Cloud 服务器在国外，访问 Binance 一般可行；若超时，稍后重试或缩短下载时间范围  
- 检查 Binance API 是否临时限流

### 5. `git push` 被拒绝（rejected）

- 远程已有提交而本地没有：先用 `git pull origin master --rebase`（**不要**随意 `--force`）  
- 未登录：配置 `gh auth login` 或 SSH key

### 6. 部署成功但页面一直 “Running…”

- 查看 Cloud 日志 **Manage app → Logs**  
- 常见原因：依赖安装失败、入口文件路径不是 `app.py`

### 7. 修改代码后未更新

推送到 GitHub 同一分支后，Cloud 通常会自动重建；也可在控制台点 **Reboot app**。

---

## 与本仓库相关的文件一览

| 文件 | 作用 |
|------|------|
| `app.py` | Streamlit 入口（顶部导航） |
| `requirements.txt` | Python 依赖 |
| `packages.txt` | 系统 apt 包（本项目为空） |
| `.streamlit/config.toml` | 深色主题 |
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
