"""Binance 手续费配置（普通用户 VIP0）。"""

# U 本位永续合约：https://www.binance.com/zh-CN/fee/futureFee
# 普通用户默认：Maker 0.02%，Taker 0.05%（无 VIP、无 BNB 抵扣）
TAKER_FEE_RATE = 0.0005
MAKER_FEE_RATE = 0.0002

# 回测按 K 线收盘价成交，视为 Taker
DEFAULT_FEE_RATE = TAKER_FEE_RATE
FEE_LABEL = "Binance U本位合约 Taker 0.05%（普通用户）"


def calc_trade_fee(price: float, size: float, fee_rate: float = DEFAULT_FEE_RATE) -> float:
    """单笔成交手续费（USDT）= 名义价值 × 费率。"""
    return abs(size) * price * fee_rate
