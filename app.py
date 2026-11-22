"""Day Trader tools: a Streamlit front end for the scripts in tools/.

The scripts are the unchanged MIT-licensed originals from
github.com/Jakeschincariol/day-trader-skill. Each runs as a subprocess in a
private temp folder per browser session, so visitors never share trader/
files. Nothing here places an order.
"""
import datetime as dt
import io
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import streamlit as st

TOOLS = Path(__file__).parent / "tools"
DEFAULT_CFG = (TOOLS / "config.example.json").read_text()

st.set_page_config(page_title="Day Trader Tools", page_icon="📈", layout="wide")


# ---------------------------------------------------------------- helpers
def secret(name, default=""):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


def workdir():
    """A private working folder per browser session; the tools write trader/ in it."""
    if "wd" not in st.session_state:
        wd = Path(tempfile.mkdtemp(prefix="trader_"))
        (wd / "trader" / "state").mkdir(parents=True)
        st.session_state["wd"] = str(wd)
    return Path(st.session_state["wd"])


def run(script, args, timeout=900):
    wd = workdir()
    cfg = st.session_state.get("cfg", DEFAULT_CFG)
    try:
        json.loads(cfg)
    except ValueError as e:
        return -1, "Settings JSON is invalid: %s" % e
    (wd / "trader" / "config.json").write_text(cfg)
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    ua = st.session_state.get("ua", "").strip()
    if ua:
        env["SEC_USER_AGENT"] = ua
    args = [str(a) for a in args]
    with st.spinner("Running: " + " ".join([script] + args)):
        try:
            p = subprocess.run([sys.executable, str(TOOLS / script)] + args, cwd=str(wd),
                               capture_output=True, text=True, timeout=timeout, env=env)
        except subprocess.TimeoutExpired:
            return -1, "Timed out after %d seconds. Try fewer symbols." % timeout
    out = p.stdout
    if p.stderr.strip():
        out += "\n[stderr]\n" + p.stderr
    return p.returncode, out.strip() or "(no output)"


def go(label, script, args, key):
    """A button that runs a tool and keeps its output on screen."""
    if st.button(label, key=key, type="primary"):
        st.session_state[key + "_out"] = run(script, args)
    if key + "_out" in st.session_state:
        code, out = st.session_state[key + "_out"]
        st.caption("exit code %s" % code)
        st.code(out, language=None)


def syms(text):
    return [s for s in text.replace(",", " ").upper().split() if s]


def opt(flag, val):
    return [flag, val] if val not in ("", None) else []


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.title("📈 Day Trader Tools")
    st.text_input("SEC user agent (your name + email)", value=secret("SEC_USER_AGENT"), key="ua",
                  help="News and Analyst read SEC EDGAR, which asks callers to identify themselves.")
    st.text_area("Settings (trader/config.json)", value=DEFAULT_CFG, height=380, key="cfg")
    st.caption("Not financial advice. Most day traders lose money. This app reads public data and does "
               "arithmetic; it cannot place orders. Paper first.")

st.info("Run in order: Scanner, News, Entry, Exit, Time Machine, Budget, Risk, Broker. Each step writes a "
        "file in trader/ that the next one reads (see the Files tab). Files last for this browser session only.")

names = ["Scanner", "News", "Entry", "Exit", "Time Machine", "Budget", "Risk", "Broker",
         "Alerts", "Analyst", "Pelosi", "Files"]
T = dict(zip(names, st.tabs(names)))

# ---------------------------------------------------------------- Scanner
with T["Scanner"]:
    st.caption("Chart scanner. A whole-universe scan is thousands of requests: start with a symbol list.")
    mode = st.radio("Scan", ["daily", "orb", "universe"], horizontal=True, key="sc_mode",
                    help="daily = pre-market setups, orb = opening-range breakouts, universe = download symbol list")
    sc = st.text_input("Symbols (comma separated, blank = whole universe)", "TSLA, AAPL, NVDA, AMD, META", key="sc_syms")
    c1, c2 = st.columns(2)
    limit = c1.number_input("Max symbols (0 = no limit)", 0, 6000, 100, key="sc_limit")
    at = c2.text_input("Cut the clock at (New York HH:MM, orb only)", "", key="sc_at")
    a = [mode]
    if mode != "universe":
        if syms(sc):
            a += ["--symbols", ",".join(syms(sc))]
        if limit:
            a += ["--limit", limit]
        if mode == "orb":
            a += opt("--at", at.strip())
    go("Run scan", "scan.py", a, "sc")

# ---------------------------------------------------------------- News
with T["News"]:
    st.caption("Headlines, 8-K filings and the move since yesterday's close. Needs the SEC user agent for filings.")
    nt = st.text_input("Tickers (blank = watchlist + plan)", "TSLA", key="nw_t")
    c1, c2, c3 = st.columns(3)
    hours = c1.number_input("Hours back", 1, 240, 24, key="nw_h")
    seen = c2.checkbox("Show items already seen", key="nw_all")
    nosec = c3.checkbox("Headlines only (skip SEC)", key="nw_nosec")
    a = []
    if syms(nt):
        a += ["--tickers"] + syms(nt)
    a += ["--hours", hours]
    a += ["--all"] if seen else []
    a += ["--no-sec"] if nosec else []
    go("Get news", "news.py", a, "nw")

# ---------------------------------------------------------------- Entry
with T["Entry"]:
    st.caption("Is the setup triggered? Long side only. Saves trader/entry.json when you tick Save.")
    how = st.radio("Check", ["one symbol", "every hit in the scanner's watchlist"], horizontal=True, key="en_how")
    c1, c2, c3, c4 = st.columns(4)
    sym = c1.text_input("Symbol", "TSLA", key="en_sym")
    setup = c2.selectbox("Setup", ["orb", "level"], key="en_setup")
    orm = c3.number_input("Opening range (min)", 1, 60, 15, key="en_or")
    itv = c4.selectbox("Bars", ["5m", "1m"], key="en_itv")
    level = st.number_input("Level to close above (setup = level)", 0.0, step=0.01, key="en_lvl")
    save = st.checkbox("Save result for the Exit tab", True, key="en_save")
    common = ["--setup", setup, "--or-minutes", orm, "--interval", itv]
    if setup == "level" and level > 0:
        common += ["--level", level]
    if how == "one symbol":
        a = ["check", sym.strip().upper()] + common + (["--write"] if save else [])
    else:
        a = ["watchlist"] + common
    go("Check entry", "entry.py", a, "en")

# ---------------------------------------------------------------- Exit
with T["Exit"]:
    st.caption("Stop and target before you enter. Reads trader/entry.json, or fill the entry by hand.")
    src = st.radio("Entry from", ["last Entry check", "by hand"], horizontal=True, key="ex_src")
    a = ["plan"]
    if src == "by hand":
        c1, c2, c3, c4, c5 = st.columns(5)
        s = c1.text_input("Symbol", "TSLA", key="ex_sym")
        e = c2.number_input("Entry price", 0.0, step=0.01, key="ex_e")
        tm = c3.text_input("Entry time (NY)", "10:15 AM", key="ex_time")
        h = c4.number_input("Range high", 0.0, step=0.01, key="ex_h")
        l = c5.number_input("Range low", 0.0, step=0.01, key="ex_l")
        a += ["--symbol", s.strip().upper(), "--entry", e] + opt("--time", tm.strip())
        if h > 0 and l > 0:
            a += ["--or-high", h, "--or-low", l]
    c1, c2, c3 = st.columns(3)
    stop = c1.text_input("Stop", "or-mid", key="ex_stop", help="or-mid, or-low, price:X, pct:X, atr:K")
    target = c2.text_input("Target", "2R", key="ex_tgt", help="2R, 1.5R, 1R, price:X")
    flat = c3.text_input("Flat by (NY HH:MM, blank = settings)", "", key="ex_flat")
    a += ["--stop", stop, "--target", target] + opt("--flat-by", flat.strip()) + ["--write"]
    go("Plan the exit", "exit.py", a, "ex")

# ---------------------------------------------------------------- Time Machine
with T["Time Machine"]:
    st.caption("Replays the rest of the session from the stock's own recent 5-minute bars. A simulation, not a prediction.")
    c1, c2 = st.columns(2)
    n = c1.number_input("Replays", 100, 20000, 10000, step=1000, key="tm_n")
    seed = c2.number_input("Seed", 0, 99999, 19, key="tm_seed")
    with st.expander("Plan by hand (otherwise trader/plan.json from the Exit tab)"):
        c1, c2, c3, c4, c5 = st.columns(5)
        s = c1.text_input("Symbol", key="tm_sym")
        e = c2.number_input("Entry", 0.0, step=0.01, key="tm_e")
        et = c3.text_input("Entry time (NY)", "10:15 AM", key="tm_et")
        sp = c4.number_input("Stop", 0.0, step=0.01, key="tm_s")
        tg = c5.number_input("Target", 0.0, step=0.01, key="tm_t")
    a = ["run", "--replays", n, "--seed", seed]
    if s.strip() and e > 0 and sp > 0 and tg > 0 and et.strip():
        a += ["--symbol", s.strip().upper(), "--entry", e, "--entry-time", et.strip(),
              "--stop", sp, "--target", tg]
    a += ["--write"]
    go("Run the Time Machine", "timemachine.py", a, "tm")
    go("Show fan chart of the last run", "timemachine.py",
       ["chart", "--from", "trader/timemachine.json"], "tmc")

# ---------------------------------------------------------------- Budget
with T["Budget"]:
    st.caption("Sizes one bracket order to your budget and max loss, from trader/plan.json. Nothing is placed.")
    b = st.number_input("Budget in dollars (0 = use Settings)", 0.0, step=100.0, key="bd_b")
    a = opt("--budget", b if b > 0 else "") + ["--write"]
    go("Size the trade", "size.py", a, "bd")

# ---------------------------------------------------------------- Risk
with T["Risk"]:
    st.caption("Checks trader/orders.json against your limits: PASS or BLOCK with the reason.")
    go("Run risk check", "check.py", [], "rk")

# ---------------------------------------------------------------- Broker
with T["Broker"]:
    st.warning("This page only builds and logs tickets. It does not connect to a broker or send orders; "
               "you place any order yourself, at your broker.")
    act = st.radio("Action", ["show", "log", "flatten"], horizontal=True, key="br_act")
    a = [act]
    if act == "flatten":
        c1, c2 = st.columns(2)
        s = c1.text_input("Symbol", key="br_sym")
        q = c2.text_input("Shares held (blank = trader/portfolio.json)", key="br_qty")
        a += ["--symbol", s.strip().upper()] + opt("--qty", q.strip())
    go("Run", "ticket.py", a, "br")

# ---------------------------------------------------------------- Alerts
with T["Alerts"]:
    st.caption("Alerts only fire when you press Check; there is no background process in Streamlit.")
    act = st.radio("Action", ["quote", "clock", "add", "list", "check"], horizontal=True, key="al_act")
    a = [act]
    if act == "quote":
        a += syms(st.text_input("Symbols", "TSLA", key="al_q")) + ["--write"]
    elif act == "add":
        kind = st.radio("Rule", ["from plan (stop, target, flat by close)", "above", "below", "stop", "target"],
                        horizontal=True, key="al_kind")
        if kind.startswith("from plan"):
            a += ["--from-plan"]
        else:
            c1, c2 = st.columns(2)
            s = c1.text_input("Symbol", "TSLA", key="al_sym")
            p = c2.number_input("Price", 0.0, step=0.01, key="al_p")
            a += ["--symbol", s.strip().upper(), "--" + kind, p]
    go("Run", "alerts.py", a, "al")

# ---------------------------------------------------------------- Analyst
with T["Analyst"]:
    st.caption("Quarterly revenue, margins and EPS from SEC EDGAR. Needs the SEC user agent in the sidebar.")
    c1, c2 = st.columns([3, 1])
    tk = c1.text_input("Tickers", "AAPL", key="an_t")
    qn = c2.number_input("Quarters", 2, 20, 6, key="an_q")
    go("Analyze", "facts.py", syms(tk) + ["--quarters", qn], "an")

# ---------------------------------------------------------------- Pelosi
with T["Pelosi"]:
    st.caption("Congress stock-trade disclosures (public, filed up to 45 days after the trade).")
    act = st.radio("Action", ["index", "new", "fetch"], horizontal=True, key="pl_act")
    c1, c2, c3 = st.columns(3)
    member = c1.text_input("Member (blank = all)", "pelosi", key="pl_m")
    year = c2.number_input("Year", 2008, 2100, dt.date.today().year, key="pl_y")
    lim = c3.number_input("Rows", 1, 500, 50, key="pl_l")
    a = [act]
    if act == "index":
        a += opt("--member", member.strip()) + ["--year", year, "--limit", lim]
    elif act == "new":
        a += opt("--member", member.strip()) + ["--year", year, "--dry-run"]
        if st.checkbox("Also read the PDFs (needs pdftotext; packages.txt installs it)", key="pl_read"):
            a += ["--read"]
    else:
        doc = st.text_input("Document ID", key="pl_doc")
        a += [doc.strip(), "--year", year]
    go("Run", "ptr.py", a, "pl")

# ---------------------------------------------------------------- Files
with T["Files"]:
    wd = workdir()
    st.caption("What the tools wrote in this session's trader/ folder. Upload a portfolio.json or watchlist.json "
               "to feed Budget and Risk.")
    up = st.file_uploader("Add a file to trader/", type=["json", "txt"], key="fl_up")
    if up is not None:
        (wd / "trader" / Path(up.name).name).write_bytes(up.getvalue())
        st.success("Saved trader/" + Path(up.name).name)
    files = sorted(p for p in (wd / "trader").rglob("*") if p.is_file())
    if not files:
        st.info("Nothing yet. Run a tool first.")
    else:
        pick = st.selectbox("File", [str(f.relative_to(wd)) for f in files], key="fl_pick")
        st.code((wd / pick).read_text(errors="replace")[:30000], language="json" if pick.endswith(".json") else None)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for f in files:
                z.write(f, str(f.relative_to(wd)))
        st.download_button("Download all as ZIP", buf.getvalue(), "trader_files.zip", "application/zip")
