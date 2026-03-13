# Portfolio Dash

A small Plotly Dash web app built from the ideas in the Colab notebook. It includes:

- an efficient frontier chart
- a target-return allocation chart with whole-share allocation
- a normalized asset growth chart
- Docker files for deployment
- Poetry for dependency management

## Local development

1. Install Poetry.
2. Install dependencies:
   - `poetry install`
3. Start the app:
   - `poetry run portfolio-dash`
4. Open `http://localhost:8050`

## Docker

Build and run with Compose:

- `docker compose up --build`

The app is exposed on port `8050`.

## Notes

- This is a hobby project and not a financial advice tool. Always do your own research before investing.
- Data is sourced from Yahoo Finance via the yfinance library. It may contain errors or omissions. Verify critical data points independently.
