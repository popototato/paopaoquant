"""OKX 手续费配置（ETH-USDT-SWAP 永续，普通用户标准费率）。"""

# OKX U 本位永续：https://www.okx.com/zh-hans/fees
# 标准费率：Maker 0.02%，Taker 0.05%
# 实盘 CSV 加权有效约 0.016–0.020% 往返/持仓周期，中位数约 Maker 0.02%
TAKER_FEE_RATE = 0.0005  # 0.05%
MAKER_FEE_RATE = 0.0002  # 0.02%

# 回测默认按 OKX Maker 0.02%（与实盘 OKX 手续费口径一致）
DEFAULT_FEE_RATE = MAKER_FEE_RATE
FEE_LABEL = "OKX ETH-USDT-SWAP Maker 0.02%"


def calc_trade_fee(price: float, size: float, fee_rate: float = DEFAULT_FEE_RATE) -> float:
    """单笔成交手续费（USDT）= 名义价值 × 费率。"""
    return abs(size) * price * fee_rate
