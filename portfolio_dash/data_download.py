from __future__ import annotations

import pandas as pd
import yfinance as yf

from .tickers import RAW_TICKERS


def clean_name(name: str) -> str:
    value = name.strip()
    while "  " in value:
        value = value.replace("  ", " ")
    return value


def extract_currency(ticker: yf.Ticker, fallback: str) -> str:
    try:
        fast_info = ticker.fast_info
        if fast_info:
            currency = fast_info.get("currency")
            if currency:
                return str(currency)
    except Exception:
        pass

    try:
        metadata = ticker.get_history_metadata()
        currency = metadata.get("currency")
        if currency:
            return str(currency)
    except Exception:
        pass

    try:
        info = ticker.info
        currency = info.get("currency")
        if currency:
            return str(currency)
    except Exception:
        pass

    return fallback


def extract_name(ticker: yf.Ticker, fallback: str) -> str:
    for accessor in (
        lambda: ticker.fast_info.get("shortName"),
        lambda: ticker.info.get("shortName"),
        lambda: ticker.info.get("longName"),
    ):
        try:
            value = accessor()
            if value:
                return clean_name(str(value))
        except Exception:
            continue
    return fallback


def coerce_datetime_index(frame: pd.DataFrame | pd.Series) -> pd.DataFrame | pd.Series:
    frame.index = pd.to_datetime(frame.index).tz_localize(None)
    return frame


def download_price_frame(
    *,
    base_currency: str,
    lookback_months: int,
) -> tuple[pd.DataFrame, dict[str, str], list[str]]:
    end_date = pd.Timestamp.today().normalize()
    start_date = end_date - pd.DateOffset(months=lookback_months)

    raw_prices = pd.DataFrame()
    fx_prices: dict[str, pd.Series] = {}
    stock_currencies: dict[str, str] = {}
    names: dict[str, str] = {}
    failed_tickers: list[str] = []

    for raw_ticker in RAW_TICKERS:
        symbol = raw_ticker
        fallback_name = raw_ticker

        try:
            ticker = yf.Ticker(symbol)
            history = ticker.history(
                start=start_date,
                end=end_date,
                auto_adjust=True,
                repair=True,
            )
            if history.empty or "Close" not in history:
                failed_tickers.append(symbol)
                continue

            close_series = history["Close"].copy()
            coerce_datetime_index(close_series)
            raw_prices[symbol] = close_series
            stock_currencies[symbol] = extract_currency(ticker, base_currency)
            display_name = extract_name(ticker, fallback_name)
            names[symbol] = f"{display_name} ({fallback_name})" if display_name != fallback_name else fallback_name
        except Exception:
            failed_tickers.append(symbol)

    if raw_prices.empty:
        raise RuntimeError("No market data could be downloaded. Check the ticker universe or network access.")

    for currency in sorted({value for value in stock_currencies.values() if value != base_currency}):
        fx_symbol = f"{currency}{base_currency}=X"
        try:
            history = yf.Ticker(fx_symbol).history(
                start=start_date,
                end=end_date,
                auto_adjust=True,
                repair=True,
            )
            if history.empty or "Close" not in history:
                raise RuntimeError(f"Missing FX history for {fx_symbol}")
            close_series = history["Close"].copy()
            coerce_datetime_index(close_series)
            fx_prices[fx_symbol] = close_series
        except Exception as exc:
            raise RuntimeError(f"Could not download FX conversion data for {fx_symbol}: {exc}") from exc

    aligned = raw_prices.ffill().dropna(how="all")
    converted = pd.DataFrame(index=aligned.index)
    retained_names: dict[str, str] = {}

    for symbol in aligned.columns:
        currency = stock_currencies.get(symbol, base_currency)
        series = aligned[symbol]

        if currency == base_currency:
            converted[symbol] = series
            retained_names[symbol] = names[symbol]
            continue

        fx_symbol = f"{currency}{base_currency}=X"
        fx_series = fx_prices.get(fx_symbol)
        if fx_series is None:
            failed_tickers.append(symbol)
            continue

        combined = pd.concat([series, fx_series.rename(fx_symbol)], axis=1).ffill().dropna()
        if combined.empty:
            failed_tickers.append(symbol)
            continue

        converted[symbol] = combined[symbol] * combined[fx_symbol]
        retained_names[symbol] = names[symbol]

    converted = converted.ffill().dropna()
    if converted.shape[1] < 2:
        raise RuntimeError("At least two assets with aligned price history are required to build the dashboard.")

    return converted, retained_names, sorted(set(failed_tickers))
