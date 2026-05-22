# 泡泡量化（paopaoquant）部署指南

项目结构：

- **Streamlit 多页应用**：`app.py` + `pages/`（回测、网格策略等）
- **React 交易面板**：`frontend/` 构建到 `static/trading_panel/`

---

## 一、推送到 GitHub（首次）

### 1. 检查本地状态

```bash
cd /Users/fanxuelin/Desktop/paopaoquant
git status
git remote -v   # 无输出表示尚未关联远程仓库
```

以下文件**不应**出现在 `git add` 列表中（已在 `.gitignore`）：

- `eth.csv` 及各类 `*.csv` 数据
- `.env`
- `.streamlit/secrets.toml`
- `frontend/node_modules/`

### 2. 在 GitHub 创建空仓库

**方式 A — 网页**：登录 [github.com/new](https://github.com/new)，仓库名如 `paopaoquant`，不要勾选 “Add a README”（本地已有提交）。

**方式 B — GitHub CLI**（需先安装并登录）：

```bash
# macOS 安装
brew install gh
gh auth login

# 在项目目录创建远程仓库并推送（不要 force push）
cd /Users/fanxuelin/Desktop/paopaoquant
gh repo create paopaoquant --private --source=. --remote=origin --push
```

若仓库已存在，只需关联远程：

```bash
git remote add origin https://github.com/<你的用户名>/paopaoquant.git
git branch -M main   # 可选：GitHub 默认分支多为 main
git push -u origin master   # 若已改名为 main 则用 main
```

### 3. 推送前确认

```bash
git log -1 --oneline
git push -u origin master
```

浏览器按提示完成 GitHub 登录（HTTPS）或配置 SSH 密钥。

---

## 二、Vercel 一键部署（仅交易面板静态站）

> **重要限制**：Vercel 适合托管 **构建后的静态前端**，**不能**替代 Streamlit Python 服务端。  
> Vercel 上看到的是 **ETH/USDT 交易面板演示**；完整回测、数据下载、多页逻辑请用下文「三、完整 Streamlit 应用」。

### 1. 导入项目

1. 打开 [vercel.com/new](https://vercel.com/new)，用 GitHub 登录并授权。
2. **Import** 选择 `paopaoquant` 仓库。
3. 项目设置（一般无需改，已由 `vercel.json` 指定）：
   - **Framework Preset**：Other
   - **Install Command**：`cd frontend && npm install`
   - **Build Command**：`npm run build`
   - **Output Directory**：`static/trading_panel`
4. 点击 **Deploy**。首次构建约 1–3 分钟。

### 2. 环境变量

交易面板使用 Binance 公开行情接口，**通常不需要**在 Vercel 配置环境变量。  
若日后接入需密钥的 API，在 Vercel → Project → **Settings → Environment Variables** 添加，且**不要**写入 Git。

### 3. 自定义域名（可选）

Vercel 项目 → **Settings → Domains** → 添加域名并按提示配置 DNS。

### 4. 每次更新

```bash
git add .
git commit -m "更新说明"
git push
```

Vercel 会自动触发重新构建部署。

### 5. 本地与 Vercel 一致的前端构建

```bash
cd frontend && npm install && npm run build
# 产物在 static/trading_panel/
```

Streamlit 内嵌面板依赖该目录；推送到 GitHub 时建议包含最新构建产物，以便 Streamlit Cloud 无需 Node 构建步骤。

---

## 三、完整 Streamlit 应用托管（推荐）

Vercel **不适合**运行 `streamlit run app.py`。请任选：

| 平台 | 适用 | 步骤概要 |
|------|------|----------|
| **[Streamlit Community Cloud](https://share.streamlit.io)** | 免费、与 GitHub 集成 | 连接仓库 → Main file：`app.py` → 部署 |
| **Railway / Render / Fly.io** | 需要更多控制 | Docker 或 `streamlit run` + `requirements.txt` |
| **VPS + Nginx** | 生产、自定义域名 | 见下文「方案 A」 |

**Streamlit Cloud 注意**：

1. 仓库需包含 `requirements.txt`。
2. 提交前在本地执行 `cd frontend && npm run build`，将 `static/trading_panel/` 一并 push（Cloud 默认无 Node 构建）。
3. `eth.csv` 不要提交；在云端首次打开应用后于界面内下载数据。
4. 密钥放在 Cloud 的 **Secrets**（对应本地 `.streamlit/secrets.toml`），不要进 Git。

---

## 四、VPS / 域名 / CDN（进阶）

以下三种方案任选其一，或组合使用（方案 C）。

---

## 前置准备

1. 在域名服务商（阿里云万网、腾讯云 DNSPod、Cloudflare 等）购买域名并完成实名。
2. 本地或服务器已能正常运行：

```bash
cd /path/to/paopaoquant
pip install -r requirements.txt
streamlit run app.py
```

3. 若使用交易面板，先构建前端：

```bash
cd frontend && npm install && npm run build
```

---

## 方案 A：VPS + Nginx 反向代理（推荐，最灵活）

适用：阿里云 ECS、腾讯云 CVM、轻量应用服务器等 Linux 主机。

### 1. DNS 解析

| 记录类型 | 主机记录 | 记录值 | 说明 |
|---------|---------|--------|------|
| A | `@` | 服务器公网 IP | 根域名 `example.com` |
| A | `www` | 同上（可选） | `www.example.com` |

解析生效通常 5–30 分钟，可用 `dig example.com` 检查。

### 2. 服务器环境

```bash
# Ubuntu/Debian 示例
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nginx certbot python3-certbot-nginx

cd /opt/paopaoquant   # 上传代码或 git clone
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd frontend && npm install && npm run build && cd ..
```

### 3. Streamlit 监听所有网卡

生产环境不要用默认只监听 localhost，需绑定 `0.0.0.0`：

```bash
streamlit run app.py \
  --server.address 0.0.0.0 \
  --server.port 8501 \
  --server.headless true
```

可在项目根目录创建 `.streamlit/config.toml`：

```toml
[server]
address = "0.0.0.0"
port = 8501
headless = true
enableCORS = false
enableXsrfProtection = true
```

### 4. systemd 守护进程

`/etc/systemd/system/paopaoquant.service`：

```ini
[Unit]
Description=Paopaoquant Streamlit
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/paopaoquant
Environment=PATH=/opt/paopaoquant/.venv/bin
ExecStart=/opt/paopaoquant/.venv/bin/streamlit run app.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now paopaoquant
sudo systemctl status paopaoquant
```

### 5. Nginx 反向代理 + HTTPS

`/etc/nginx/sites-available/paopaoquant`：

```nginx
server {
    listen 80;
    server_name example.com www.example.com;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/paopaoquant /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d example.com -d www.example.com
```

certbot 会自动配置 443 证书与 HTTP 跳转 HTTPS。

### 6. 防火墙

```bash
# 仅开放 80/443，不要对公网直接暴露 8501
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

云厂商安全组同样只放行 **22（SSH）、80、443**。

### 7. 更新部署

```bash
cd /opt/paopaoquant && git pull
source .venv/bin/activate && pip install -r requirements.txt
cd frontend && npm run build && cd ..
sudo systemctl restart paopaoquant
```

---

## 方案 B：Streamlit Community Cloud + 自定义域名

适用：不想自己管服务器，代码在 GitHub 公开或私有仓库。

1. 将项目推送到 GitHub。
2. 打开 [share.streamlit.io](https://share.streamlit.io)，用 GitHub 登录并 **New app**。
3. 选择仓库、分支，Main file path 填 `app.py`。
4. 在应用 **Settings → General → Custom subdomain** 可使用 `your-app-name.streamlit.app`。
5. **自定义根域名**：在应用 Settings 中按提示添加 CNAME（具体以 Streamlit 官方文档为准；部分计划/功能可能变动）。

注意：

- 需在仓库中包含 `requirements.txt`；构建产物 `static/trading_panel/` 建议提交到 Git，或在 Cloud 的构建步骤中执行 `npm run build`（需配置 `packages.txt` / 自定义脚本，相对麻烦）。
- 免费 tier 有资源与休眠限制，不适合高并发实盘场景。

---

## 方案 C：静态面板 CDN + Streamlit 子域名

适用：交易面板访问量大、希望静态资源走 CDN，主站仍用 Streamlit。

| 服务 | 域名示例 | 内容 |
|------|----------|------|
| Streamlit | `app.example.com` | 回测、多页逻辑 |
| 静态/CDN | `panel.example.com` 或 CDN 域名 | `static/trading_panel/` |

### DNS

| 类型 | 主机 | 值 |
|------|------|-----|
| A | `app` | VPS 公网 IP（同方案 A） |
| CNAME | `panel` | CDN 提供的 CNAME（如阿里云 CDN、Cloudflare Pages） |

Nginx 可为 `panel` 单独配置 `root /opt/paopaoquant/static/trading_panel;`，或上传到对象存储 + CDN。

Streamlit 页面通过 `chart_component.render_trading_panel()` 内联构建产物，一般仍走 `app` 域名即可；独立子域主要用于直接打开纯 React 面板或减轻主站带宽。

---

## 常见问题

### 访问域名显示 502

- 检查 `systemctl status paopaoquant` 是否在跑。
- 检查 Nginx `proxy_pass` 端口是否为 8501。
- 本机测试：`curl http://127.0.0.1:8501`

### WebSocket / 页面刷新断开

Streamlit 依赖 WebSocket，Nginx 必须保留 `Upgrade` 与 `Connection` 头（见上文配置）。

### 图表时间不对

Binance 时间为 UTC；前端已用 `Asia/Shanghai` 格式化轴标签。部署后若仍不对，清除浏览器缓存并确认 `static/trading_panel/` 为最新 `npm run build` 结果。

### 安全建议

- 不要将 API Key、`.env` 提交到 Git。
- 生产使用 HTTPS。
- 定期 `apt upgrade` / 更新 Python 依赖。

---

## 快速检查清单

- [ ] DNS A/CNAME 已指向正确 IP 或 CDN
- [ ] `frontend` 已 `npm run build`
- [ ] Streamlit `--server.address 0.0.0.0` 或 config.toml
- [ ] systemd 已 enable 且 running
- [ ] Nginx 反代 + certbot HTTPS
- [ ] 防火墙/安全组仅 80/443（及 SSH）
- [ ] 浏览器访问 `https://example.com` 正常
