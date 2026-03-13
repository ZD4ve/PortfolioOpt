"""Entry point for the Portfolio Dash application.

Run with:

    python -m portfolio_dash

This will start a Dash development server on port 8050 by default.
"""

from __future__ import annotations

import os

from .app import app


def main() -> None:
    """Run the Dash development server.

    This is used by ``python -m portfolio_dash`` and by the Poetry console script.
    """
    app.run_server(host="0.0.0.0", port=8050, debug=True)


if __name__ == "__main__":
    main()
