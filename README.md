# 泡泡量化（paopaoquant）

Streamlit 多页量化应用 + React 交易面板（Binance K 线、清算热力图等）。

## 本地运行

```bash
pip install -r requirements.txt
cd frontend && npm install && npm run build && cd ..
streamlit run app.py
```

回测数据 `eth.csv` 体积较大，已在 `.gitignore` 中排除；首次运行可在应用内从 Binance 下载。

## 部署

| 目标 | 平台 | 说明 |
|------|------|------|
| **完整 Streamlit 应用** | [Streamlit Community Cloud](https://share.streamlit.io)、Railway、VPS | 需 Python 运行时，见 [DEPLOY.md](./DEPLOY.md) |
| **交易面板静态预览** | [Vercel](https://vercel.com) | 仅 `frontend` 构建产物，不含回测/Streamlit |

详细步骤（GitHub 推送、Vercel 导入、限制说明）：**[DEPLOY.md](./DEPLOY.md)**。

### 快速：推送到 GitHub

```bash
git remote add origin https://github.com/<你的用户名>/paopaoquant.git
git push -u origin master
```

### 快速：Vercel 一键导入

1. [vercel.com/new](https://vercel.com/new) → Import Git Repository → 选择本仓库  
2. 框架选 **Other**，保持默认 `vercel.json`（构建 `frontend`，输出 `static/trading_panel`）  
3. Deploy — 无需配置 Python 环境变量  

## 安全

勿将 `.env`、`.streamlit/secrets.toml`、API 密钥或 `eth.csv` 提交到 Git。
