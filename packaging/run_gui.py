from __future__ import annotations

from anti_silo.config import load_config
from anti_silo.gui import serve_gui


if __name__ == "__main__":
    serve_gui(load_config())
