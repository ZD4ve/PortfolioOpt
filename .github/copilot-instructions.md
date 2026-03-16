# Copilot Instructions - Portfolio Dash

This workspace contains a Dash application for portfolio optimization, utilizing `PyPortfolioOpt` and `yfinance`. All AI-generated code and architectural changes must adhere to the standards outlined below.

## 1. Code Style

- **Naming Conventions**: 
    - Use `snake_case` for functions, variables, and file names.
    - Use `SCREAMING_SNAKE_CASE` for constants (e.g., `PARCHMENT_CREAM`, `DEFAULT_BUDGET`).
    - Use `PascalCase` for classes and dataclasses (e.g., `PortfolioBundle`).
- **Type Hinting**: 
    - Consistent use of `from __future__ import annotations`.
    - Explicit type hints for all function signatures and complex variables (e.g., `list[str | dict[str, object]]`).
- **Formatting**: 
    - Follows **Black/Ruff** standards (double quotes for strings, 4-space indentation, consistent line breaks).
    - Imports are grouped: standard library, third-party, and then local modules.

## 2. Architecture

- **Data Flow**: `yfinance` fetches raw market data $\rightarrow$ `portfolio_service.py` processes it using `PyPortfolioOpt` into a `PortfolioBundle` $\rightarrow$ `app.py` consumes the bundle to render Dash components.
- **Service Layer**: `portfolio_service.py` encapsulates all logic for downloading data, calculating efficient frontiers, and cleaning weights. It uses `@lru_cache` for performance.
- **View Layer**: `app.py` defines the layout and callbacks. It relies on helper functions in `portfolio_service.py` (e.g., `make_growth_figure`, `allocation_table_rows`) to generate UI elements.
- **Configuration**: `tickers.py` acts as the single source of truth for the asset universe (`RAW_TICKERS`).

## 3. Build and Test

- **Tooling**: Managed by **Poetry**. Configuration is located in the root `pyproject.toml`.
- **Execution**: 
    - Start the app using `python -m portfolio_dash`.
    - Alternatively, use the poetry script: `portfolio-dash`.
- **Environment**: Requires Python 3.11+. Environment variables like `PORTFOLIO_BUDGET` and `PORTFOLIO_LOOKBACK_MONTHS` can override defaults.

## 4. Design Philosophy: Archival Ledger

The UI must embody the **"Archival Ledger"** aesthetic—a fusion of historical accounting and modern precision.

- **Core Directive**: UI changes should favor a "paper and ink" feel over a "digital screen" look.
- **Color Palette**:
    - **Backgrounds**: `PARCHMENT_CREAM` (#ede2c2) and `MUTED_PARCHMENT` (#f5edd8).
    - **Primary Text/Ink**: `ARCHIVAL_INDIGO` (#2f3b4c).
    - **Accents**: `AGED_TERRACOTTA` (#d97b4a), `CALM_SAGE` (#88a99f), `VINTAGE_MUSTARD` (#d8a62b).
- **Typography**: Prefer **IBM Plex Sans** for readability and **IBM Plex Mono** for data/monetary values to mimic typewriter or ledger entries.
- **Visual Elements**:
    - All charts must use the `apply_archival_theme` helper to ensure consistent grid colors and fonts.
    - Tables should use high-contrast borders (`BORDER_TINT`) and uppercase headers to resemble traditional bookkeeping.

## 5. Detailed Design Aesthetics

The workspace follows a strict "Archival Ledger" identity based on mid-century scientific journals and mechanical blueprints.

### **UI & Layout**
- **Wireframe Grids**: Use visible, 1-pixel dark borders (`BORDER_TINT`) instead of shadows. Separate sections with edge-to-edge solid lines.
- **Matte Flatness**: Strictly avoid digital gradients, glows, or drop shadows.
- **Motion**: Animations should feel like mechanical dials clicking or slide-rules adjusting. No "bouncy" or elastic transitions.

### **Data Visualization**
- **Stepped Traces**: For time-series data (like growth), prefer rigid "stepped" (`hv`) line shapes over smooth curves.
- **Stratified Layers**: Use solid, flat colors to represent data "strata" (inspired by geological maps).
- **Isometric & Concentric**: Favor isometric block diagrams or concentric layouts for complex multi-variable summaries.

### **Typographic Hierarchy**
- **Headers**: Wide-spaced all-caps sans-serif for section titles.
- **Data/Numerals**: Monospace (typewriter-inspired) for all numeric values and financial tickers to ensure perfect vertical alignment in tables.
