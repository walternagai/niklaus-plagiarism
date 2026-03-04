"""
UI Authentication module for Niklaus.
"""

from ui.auth.login import render_login_page
from ui.auth.dashboard import render_dashboard
from ui.auth.history import render_history_page

__all__ = [
    'render_login_page',
    'render_dashboard',
    'render_history_page',
]