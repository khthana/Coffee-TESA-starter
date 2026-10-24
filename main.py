"""Coffee market starter agent: poll the market, appraise once, send offers every round.

    python main.py              # play until the market closes
    python main.py --forever    # sandbox: keep playing game after game
"""
import json
import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path

import strategy
from appraisal import appraisal_items, estimate_lots
from llm import LLM
from market import Market, MarketError
from memory import Memory

HERE = Path(__file__).parent
LOGS = HERE / "logs"


def load_env(path: Path) -> None:
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def log(event: str, **data) -> None:
    LOGS.mkdir(exist_ok=True)
    row = {"time": datetime.now().isoformat(timespec="seconds"), "event": event, **data}
    with open(LOGS / "decisions.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    short = {k: v for k, v in data.items() if k not in ("offers", "notes")}
    print(row["time"][11:], event, json.dumps(short, ensure_ascii=False)[:160], flush=True)


def send_offers(api: Market, offers: list[dict]) -> list[dict]:
    """Send all offers at once; if the batch is rejected, send them one by one and skip the bad ones."""
    try:
        return api.offer_batch(offers)["offers"]
    except MarketError as e:
        log("batch_rejected", error=str(e))
    sent = []
    for o in offers:
        try:
            sent.append(api.offer(o))
        except MarketError as e:
            log("offer_rejected", offer=o, error=str(e))
    return sent


def play(api: Market, llm: LLM | None, forever: bool) -> None:
    info = api.calendar()
    rules = info["rules"]
    memory, tv, acted, game = None, {}, set(), None
    rng = random.Random()
    while True:
        try:
            state = api.state()
        except Exception as e:                      # noqa: BLE001 — never die on a network error
            log("state_error", error=str(e))
            time.sleep(3)
            continue
        lots_key = tuple(sorted(l["lot_id"] for l in state["lots"]))
        if lots_key != game:                        # new game (or sandbox reset): start fresh
            game, acted, tv = lots_key, set(), estimate_lots(rules, state["lots"])
            memory = Memory(LOGS / f"memory-{state['market']}-{lots_key[0] if lots_key else 'none'}.json")
            log("new_game", market=state["market"], lots=len(state["lots"]), tv=tv)
        phase = state["phase"]

        if phase == "APPRAISAL" and not state["appraisal_submitted"]:
            try:
                api.appraise(appraisal_items(rules, state["lots"], tv))
                log("appraisal_sent", tv=tv)
            except MarketError as e:
                log("appraisal_error", error=str(e))

        elif phase == "ROUND_OPEN" and not state["paused"] and state["round"]["round_id"] not in acted:
            rid = state["round"]["round_id"]
            acted.add(rid)
            memory.record_results(state["last_results"])
            if any(o["round_id"] == rid for o in state["my_open_offers"]):
                # restarted after sending this round: the market already holds our offers, and a new batch
                # would replace them (capacity_left_kg no longer counts them, so it would offer less)
                log("round_already_sent", round=rid, n=len(state["my_open_offers"]))
                continue
            ctx = strategy.Context(rules, info["calendar"], tv, rng, memory, llm, state["seconds_left"] or 999)
            t0 = time.time()
            try:
                offers, source = strategy.decide(state, ctx)
            except Exception as e:                  # noqa: BLE001 — a bug in strategy must not stop the agent
                log("strategy_crashed", error=repr(e))
                offers, source = strategy.guard(state, ctx, strategy.rule_plan(state, ctx, strategy.candidates(state, ctx))), "rules"
            sent = send_offers(api, offers) if offers else []
            memory.record_sent(rid, offers, state, tv)
            log("offers_sent", round=rid, source=source, n=len(sent), kg=sum(o["kg"] for o in sent),
                seconds=round(time.time() - t0, 1), offers=offers, notes=ctx.notes)

        elif phase == "CLOSED" and game is not None and "closed" not in acted:
            acted.add("closed")
            memory.record_results(state["last_results"])
            log("market_closed", standings=state["standings"])
            if not forever:
                return

        # Read the clock from the server; never hard-code round times.
        left = state["seconds_left"] or 5
        time.sleep(min(5.0, max(0.5, left + 0.2)))


def main() -> None:
    load_env(HERE / ".env")
    api = Market(os.environ["MARKET_URL"], os.environ["TEAM_KEY"])
    llm = None
    if os.environ.get("USE_LLM", "1") == "1":
        llm = LLM(os.environ["LLM_BASE_URL"], os.environ["LLM_MODEL"], os.environ.get("LLM_API_KEY", ""),
                  timeout=float(os.environ.get("LLM_TIMEOUT", "60")), thinking=os.environ.get("LLM_THINKING") == "1")
    play(api, llm, "--forever" in sys.argv)


if __name__ == "__main__":
    main()
