import time
import hashlib
import hmac
from typing import Optional
from urllib.parse import urlencode

import httpx
from app.core.config import get_settings
from app.core.encryption import decrypt_value

settings = get_settings()


class BinanceClient:
    def __init__(self, api_key: str, api_secret: str, testnet: bool = True):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = settings.BINANCE_TESTNET_API_URL if testnet else settings.BINANCE_API_URL
        self.ws_url = settings.BINANCE_TESTNET_WS_URL if testnet else settings.BINANCE_WS_URL
        self.headers = {"X-MBX-APIKEY": self.api_key}

    def _sign(self, params: dict) -> dict:
        params["timestamp"] = int(time.time() * 1000)
        params["recvWindow"] = 5000
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature
        return params

    async def _request(self, method: str, path: str, params: Optional[dict] = None, signed: bool = False):
        params = params or {}
        if signed:
            params = self._sign(params)
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=30) as client:
            if method == "GET":
                response = await client.get(url, params=params, headers=self.headers)
            elif method == "POST":
                response = await client.post(url, params=params, headers=self.headers)
            elif method == "DELETE":
                response = await client.delete(url, params=params, headers=self.headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            response.raise_for_status()
            return response.json()

    async def get_account(self) -> dict:
        return await self._request("GET", "/fapi/v2/account", signed=True)

    async def get_balance(self, asset: str = "USDT") -> dict:
        account = await self.get_account()
        for balance in account.get("assets", []):
            if balance["asset"] == asset:
                return balance
        return {"asset": asset, "balance": "0", "availableBalance": "0"}

    async def get_position(self, symbol: str) -> Optional[dict]:
        positions = await self._request("GET", "/fapi/v2/positionRisk", signed=True)
        for pos in positions:
            if pos["symbol"] == symbol and float(pos.get("positionAmt", 0)) != 0:
                return pos
        return None

    async def get_all_positions(self) -> list:
        positions = await self._request("GET", "/fapi/v2/positionRisk", signed=True)
        return [p for p in positions if float(p.get("positionAmt", 0)) != 0]

    async def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        reduce_only: bool = False,
    ) -> dict:
        params = {
            "symbol": symbol,
            "side": side.upper(),
            "type": order_type.upper(),
            "quantity": f"{quantity}",
        }
        if price:
            params["price"] = f"{price}"
        if stop_price:
            params["stopPrice"] = f"{stop_price}"
        if reduce_only:
            params["reduceOnly"] = "true"
        return await self._request("POST", "/fapi/v1/order", params=params, signed=True)

    async def place_market_order(self, symbol: str, side: str, quantity: float, reduce_only: bool = False) -> dict:
        return await self.place_order(symbol, side, "MARKET", quantity, reduce_only=reduce_only)

    async def place_limit_order(self, symbol: str, side: str, quantity: float, price: float, reduce_only: bool = False) -> dict:
        return await self.place_order(symbol, side, "LIMIT", quantity, price=price, reduce_only=reduce_only)

    async def place_stop_market_order(self, symbol: str, side: str, quantity: float, stop_price: float, reduce_only: bool = False) -> dict:
        return await self.place_order(symbol, side, "STOP_MARKET", quantity, stop_price=stop_price, reduce_only=reduce_only)

    async def place_take_profit_market_order(self, symbol: str, side: str, quantity: float, stop_price: float, reduce_only: bool = False) -> dict:
        return await self.place_order(symbol, side, "TAKE_PROFIT_MARKET", quantity, stop_price=stop_price, reduce_only=reduce_only)

    async def cancel_order(self, symbol: str, order_id: int) -> dict:
        return await self._request("DELETE", "/fapi/v1/order", params={"symbol": symbol, "orderId": order_id}, signed=True)

    async def cancel_all_orders(self, symbol: str) -> dict:
        return await self._request("DELETE", "/fapi/v1/allOpenOrders", params={"symbol": symbol}, signed=True)

    async def get_open_orders(self, symbol: Optional[str] = None) -> list:
        params = {}
        if symbol:
            params["symbol"] = symbol
        return await self._request("GET", "/fapi/v1/openOrders", params=params, signed=True)

    async def get_order(self, symbol: str, order_id: int) -> dict:
        return await self._request("GET", "/fapi/v1/order", params={"symbol": symbol, "orderId": order_id}, signed=True)

    async def get_klines(self, symbol: str, interval: str, limit: int = 500) -> list:
        return await self._request("GET", "/fapi/v1/klines", params={"symbol": symbol, "interval": interval, "limit": limit})

    async def get_ticker_price(self, symbol: str) -> dict:
        return await self._request("GET", "/fapi/v1/ticker/price", params={"symbol": symbol})

    async def get_24h_ticker(self, symbol: str) -> dict:
        return await self._request("GET", "/fapi/v1/ticker/24hr", params={"symbol": symbol})

    async def get_orderbook(self, symbol: str, limit: int = 20) -> dict:
        return await self._request("GET", "/fapi/v1/depth", params={"symbol": symbol, "limit": limit})

    async def get_exchange_info(self) -> dict:
        return await self._request("GET", "/fapi/v1/exchangeInfo")

    async def get_funding_rate(self, symbol: str) -> dict:
        return await self._request("GET", "/fapi/v1/premiumIndex", params={"symbol": symbol})

    async def get_open_interest(self, symbol: str) -> dict:
        return await self._request("GET", "/fapi/v1/openInterest", params={"symbol": symbol})

    async def get_income_history(self, symbol: Optional[str] = None, limit: int = 100) -> list:
        params = {"limit": limit}
        if symbol:
            params["symbol"] = symbol
        return await self._request("GET", "/fapi/v1/income", params=params, signed=True)

    async def change_leverage(self, symbol: str, leverage: int) -> dict:
        return await self._request("POST", "/fapi/v1/leverage", params={"symbol": symbol, "leverage": leverage}, signed=True)

    async def change_margin_type(self, symbol: str, margin_type: str) -> dict:
        return await self._request("POST", "/fapi/v1/marginType", params={"symbol": symbol, "marginType": margin_type}, signed=True)

    async def get_historical_klines(self, symbol: str, interval: str, start_time: int, end_time: int) -> list:
        all_klines = []
        current_start = start_time
        while current_start < end_time:
            klines = await self._request("GET", "/fapi/v1/klines", params={
                "symbol": symbol,
                "interval": interval,
                "startTime": current_start,
                "endTime": min(current_start + 1000 * 60 * 60 * 24 * 7, end_time),
                "limit": 1000,
            })
            if not klines:
                break
            all_klines.extend(klines)
            current_start = klines[-1][0] + 1
        return all_klines


def get_binance_client(api_key_encrypted: str, api_secret_encrypted: str, testnet: bool = True) -> BinanceClient:
    api_key = decrypt_value(api_key_encrypted)
    api_secret = decrypt_value(api_secret_encrypted)
    return BinanceClient(api_key, api_secret, testnet)
