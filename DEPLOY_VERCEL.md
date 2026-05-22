# Vercel 部署指南（泡泡量化）

> 推荐架构：**Vercel = 公网交易面板**；**回测 / Streamlit 多页 = 本地或 Railway / Render**（Vercel 无法运行 Python + backtrader）。

## 能部署什么

| 组件 | Vercel | 说明 |
|------|--------|------|
| React 交易面板（Binance K 线、指标） | ✅ | `frontend` → `static/trading_panel/` |
| Streamlit 回测（`backtest_page.py`） | ❌ | 需 Python 长进程，见下文「回测放哪」 |
| `eth.csv` 大文件 | ❌ | 勿提交 Git；回测环境本地下载 |

交易面板直接请求 **Binance 公开 API**，一般**无需**在 Vercel 配置 API Key。

---

## 方式 A：GitHub 一键导入（推荐）

1. 代码已推到 GitHub（勿提交 `.env`、`secrets.toml`、`eth.csv`）。
2. 打开 [vercel.com/new](https://vercel.com/new) → 用 GitHub 登录 → **Import** 本仓库。
3. 保持默认（根目录 `vercel.json` 已写好）：
   - **Framework Preset**：Other
   - **Install Command**：`cd frontend && npm ci`
   - **Build Command**：`npm run build`
   - **Output Directory**：`public`（由 `npm run build` 从 `static/trading_panel` 复制生成，勿手填 `frontend/dist`）
4. **Deploy**。约 1–3 分钟。
5. 访问 `https://<项目名>.vercel.app/` 即为交易面板；`/trading` 同页（rewrite）。

每次 `git push` 到已连接分支，Vercel 自动重新构建。

---

## 方式 B：Vercel CLI（本机）

```bash
# 安装 CLI（一次性）
npm i -g vercel

cd /Users/fanxuelin/Desktop/paopaoquant

# 首次：登录并关联项目
vercel login
vercel link    # 按提示选团队/项目名

# 预览部署
vercel

# 生产部署
vercel --prod
```

本地先验证构建（与云端一致）：

```bash
npm run build
npx --yes serve public -l 3000
# 浏览器打开 http://localhost:3000 ，Network 中 panel.bundle.js / .css 应为 200
```

---

## 环境变量

当前面板使用 Binance 公开 REST/WebSocket，**通常不用**配置变量。

若日后接入需密钥的服务，在 Vercel → **Project → Settings → Environment Variables** 添加（**不要**写入 Git）。前端需通过 `import.meta.env.VITE_*` 读取时，在 `frontend` 构建前注入。

---

## 回测放哪（离开 Streamlit Cloud 之后）

Vercel **不能**替代 `streamlit run app.py`。任选其一：

| 方案 | 适用 |
|------|------|
| **本机** | `pip install -r requirements.txt && streamlit run app.py` |
| **Railway / Render / Fly.io** | 同一仓库，`requirements.txt` + `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`；部署前在构建阶段执行 `cd frontend && npm run build` |
| **VPS + Nginx** | 见 [DEPLOY.md](./DEPLOY.md) 方案 A |

**拆分推荐（省心）**：

- **公网演示 / 看盘**：Vercel 交易面板 URL  
- **策略回测、CSV 下载**：本机 Streamlit 或 Railway 单独服务  
- 不再依赖 Streamlit Community Cloud 亦可

---

## 与 Streamlit 本地联调

本地 Streamlit 仍通过 `chart_component` 嵌入同一套 `panel.bundle.*`；`index.html` 使用根路径 `/panel.bundle.*`，`chart_component` 在 iframe 内自动改写为 `/app/static/trading_panel/`。

```bash
cd frontend && npm install && npm run build
cd .. && streamlit run app.py
```

---

## 常见问题

### 页面空白 / 资源 404

**常见原因（按优先级）**：

1. **Output Directory 错误**  
   Vercel 必须把站点根目录指到构建产物 `public/`，而不是仓库里的 `static/trading_panel/` 或 `frontend/dist`。  
   `vercel.json` 已设置 `"outputDirectory": "public"`；`npm run build` 会把 `panel.bundle.*` 与 `index.html` 复制到 `public/`。

2. **`index.html` 仍使用 Streamlit 路径**  
   若 Network 里请求的是 `/app/static/trading_panel/panel.bundle.js` 且 404，说明构建后未跑 `postbuild` 或提交了旧版 `index.html`。  
   Vercel 上正确路径为 **`/panel.bundle.js`**、**`/panel.bundle.css`**（`verify-build.mjs` 会写入并校验）。

3. **构建未执行或失败**  
   Build Logs 中应出现：`[postbuild] OK — ... public/`。若没有，检查 **Build Command** 为 `npm run build`、**Root Directory** 为 `.`（仓库根，不能是 `frontend`）。

**快速自检（与 Vercel 一致）**：

```bash
cd /path/to/paopaoquant
npm run build
test -f public/panel.bundle.js && test -f public/panel.bundle.css && test -f public/index.html
npx --yes serve public -l 3000
# 打开 http://localhost:3000 ，确认 bundle 为 200
```

**修复后推送并重新部署**：

```bash
cd /Users/fanxuelin/Desktop/paopaoquant
npm run build
git add vercel.json package.json .gitignore frontend/scripts/verify-build.mjs static/trading_panel/index.html DEPLOY_VERCEL.md .vercelignore
git commit -m "fix: Vercel serve panel bundles from public output"
git push
```

然后在 Vercel → **Deployments** → 最新提交 **Redeploy**（建议勾选 **Clear Build Cache**）。

### Binance 请求失败

- 多为网络或地区限制；面板已配置备用域名 `data-api.binance.vision`。
- 与 Vercel 区域无关时，检查浏览器控制台 CORS/网络错误。

### 想「整站」都在 Vercel

不可行：回测依赖 Python + backtrader + 本地/服务端 CSV。请用上文「回测放哪」。

---

## 相关文件

| 文件 | 作用 |
|------|------|
| `vercel.json` | 安装/构建、输出目录 `public`、缓存头、`/trading` 重写 |
| `public/` | Vercel 站点根（构建生成，已 `.gitignore`） |
| `package.json` | 根目录 `npm run build` → `frontend` 构建 |
| `.vercelignore` | 上传时排除 venv、csv 等 |
| [DEPLOY.md](./DEPLOY.md) | 完整方案（VPS、Streamlit Cloud 等） |
