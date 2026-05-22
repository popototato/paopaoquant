#!/bin/bash
# 从脚本所在目录运行，避免「找不到 app.py」
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo ">>> 工作目录: $ROOT"
if [[ ! -f "$ROOT/app.py" ]]; then
  echo "错误: 未找到 app.py，请确认在 paopaoquant 项目根目录。"
  exit 1
fi

echo ">>> 停止旧 Streamlit..."
pkill -f "streamlit run" 2>/dev/null || true
sleep 1

echo ">>> 拉取代码（可选）..."
git pull 2>/dev/null || true

# 避免 ~/.npm 无写权限：缓存放到项目内
export NPM_CONFIG_CACHE="$ROOT/.npm-cache"
mkdir -p "$NPM_CONFIG_CACHE"

echo ">>> 构建交易面板（frontend）..."
if ! (cd "$ROOT/frontend" && npm install && npm run build); then
  echo ""
  echo "npm 构建失败。若提示 _logs 无权限，请在终端执行："
  echo "  sudo chown -R \$(whoami) ~/.npm"
  echo "然后重新运行: bash $ROOT/run_local.sh"
  exit 1
fi

if [[ ! -f "$ROOT/static/trading_panel/panel.bundle.js" ]]; then
  echo "错误: 未生成 static/trading_panel/panel.bundle.js"
  exit 1
fi

echo ">>> 构建成功: $(ls -lh "$ROOT/static/trading_panel/panel.bundle.js")"
echo ">>> 启动 Streamlit → http://localhost:8501"
echo ">>> 按 Ctrl+C 停止"
cd "$ROOT"
streamlit run app.py
