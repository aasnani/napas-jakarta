"""Shared Material-inspired tokens and global styles."""

from nicegui import ui

TOKENS = {
    "primary": "#086B68",
    "primary_container": "#BDECE6",
    "background": "#F7FAF9",
    "surface": "#FFFFFF",
    "surface_container": "#EDF3F1",
    "text": "#172B2B",
    "muted": "#5E706E",
    "outline": "#B8C9C5",
    "good": "#2E7D32",
    "moderate": "#D6A700",
    "unhealthy": "#E45D20",
    "very_unhealthy": "#C62828",
    "hazardous": "#6A1B9A",
    "missing": "#78909C",
}


def install_theme() -> None:
    """Install one stylesheet for every route; page code only uses tokens/classes."""
    ui.colors(
        primary=TOKENS["primary"],
        secondary="#205C8A",
        accent="#D6A700",
        positive=TOKENS["good"],
        negative="#BA1A1A",
        warning="#8A4F00",
        info="#205C8A",
    )
    ui.add_css("""
    :root {
      --napas-primary:#086B68; --napas-primary-container:#BDECE6;
      --napas-bg:#F7FAF9; --napas-surface:#FFFFFF; --napas-surface-container:#EDF3F1;
      --napas-text:#172B2B; --napas-muted:#5E706E; --napas-outline:#B8C9C5;
      --napas-radius:12px; --napas-radius-lg:16px;
    }
    body { background:var(--napas-bg); color:var(--napas-text); font-family:Roboto,Inter,system-ui,sans-serif; }
    .napas-main { max-width:1440px; width:100%; margin:0 auto; padding:32px; }
    .napas-content { max-width:1440px; width:100%; margin:0 auto; box-sizing:border-box; }
    .napas-analytics-content { max-width:100%; }
    .napas-chat-column { max-width:760px; width:100%; margin:0 auto; box-sizing:border-box; }
    .napas-composer { width:100%; max-width:760px; box-sizing:border-box; align-self:center; position:static; flex:none; }
    .napas-composer .q-field, .napas-composer .q-btn, .napas-composer-footer { box-sizing:border-box; max-width:100%; }
    .napas-card { border:1px solid var(--napas-outline); border-radius:var(--napas-radius-lg); background:var(--napas-surface); box-shadow:0 1px 3px rgba(23,43,43,.07); }
    .napas-muted { color:var(--napas-muted); }
    .napas-metric { min-height:112px; }
    .napas-nav-active { background:var(--napas-primary-container); color:#073B39; font-weight:600; }
    .napas-drawer { width:280px !important; }
    .napas-nav-link { min-height:50px; gap:.15rem; color:var(--napas-text); }
    .napas-chat-transcript { min-height:180px; }
    .napas-user-bubble { background:var(--napas-primary-container); border-radius:16px 16px 4px 16px; max-width:80%; }
    .napas-assistant { max-width:100%; line-height:1.6; background:var(--napas-surface); border:1px solid var(--napas-outline); border-radius:4px 16px 16px 16px; padding:14px 16px; box-shadow:0 1px 3px rgba(23,43,43,.07); }
    .napas-assistant-text { max-width:68ch; }
    .napas-sender-label { color:var(--napas-muted); font-size:.75rem; font-weight:600; letter-spacing:.02em; }
    .napas-avatar { width:32px; height:32px; border-radius:50%; display:flex; align-items:center; justify-content:center; flex:none; }
    .napas-avatar-user { background:#DCEAE8; color:#245B58; }
    .napas-avatar-guide { background:#BDECE6; color:#073B39; }
    .napas-starter { min-height:98px; text-align:left; white-space:normal; }
    .napas-rounded-control { border-radius:16px !important; overflow:hidden; }
    .napas-rounded-control.q-btn, .napas-rounded-control.q-card { border-radius:16px !important; }
    .napas-rounded-control .q-focus-helper, .napas-rounded-control .q-ripple,
    .napas-rounded-control .q-focus-helper::before, .napas-rounded-control .q-focus-helper::after {
      border-radius:inherit; overflow:hidden;
    }
    .napas-rounded-control:focus-visible { outline:3px solid #205C8A; outline-offset:2px; }
    .napas-source-link { color:var(--napas-primary); text-decoration:underline; }
    .napas-legend-dot { width:12px; height:12px; border-radius:50%; display:inline-block; margin-right:6px; }
    .napas-table-wrap { width:100%; overflow-x:auto; }
    .napas-analytics-content .napas-table-wrap .q-table__container,
    .napas-analytics-content .napas-table-wrap .q-table { width:100%; }
    .napas-fade { animation:napas-fade .18s ease-out; }
    @keyframes napas-fade { from { opacity:0; transform:translateY(4px); } to { opacity:1; transform:translateY(0); } }
    @media (max-width: 800px) { .napas-main { padding:16px; } .napas-chat-column, .napas-composer { max-width:100%; } .napas-main .q-table__container { min-width:720px; } }
    @media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation-duration:.01ms !important; transition-duration:.01ms !important; } }
    """)
