# ETH/USDT 交易面板（React）

首页 Streamlit 嵌入的专业行情面板：5m K 线、EMA20/50、RSI、MACD、EB/ES 买卖标记。

## 构建

```bash
cd frontend
npm install
npm run build
```

产物输出到 `../static/trading_panel/`（Vite `base: './'`，相对路径便于 Streamlit 内联加载）。

## 本地预览

```bash
npm run dev
```

## 修改后

每次改完前端代码需重新 `npm run build`，再刷新 Streamlit 页面。
