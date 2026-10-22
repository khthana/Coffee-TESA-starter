"""What the agent remembers between rounds, saved as JSON so a restart does not forget."""
import json
from collections import defaultdict
from pathlib import Path


class Memory:
    def __init__(self, path: str):
        self.path = Path(path)
        data = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
        self.sent: dict = data.get("sent", {})         # round_id -> offers we sent (with markup and buyer type)
        self.rounds: list = data.get("rounds", [])     # results of cleared rounds, oldest first

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"sent": self.sent, "rounds": self.rounds}, ensure_ascii=False, indent=1),
                             encoding="utf-8")

    def record_sent(self, round_id: str, offers: list[dict], state: dict, tv: dict) -> None:
        types = {r["rfq_id"]: r["buyer_type"] for r in state["rfqs"]}
        self.sent[round_id] = [{**o, "buyer_type": types[o["rfq_id"]],
                                "markup": round(o["price_per_kg"] / tv[o["lot_id"]], 3)} for o in offers]
        self.save()

    def record_results(self, results: dict | None) -> None:
        if not results or not results.get("round_id") or any(r["round_id"] == results["round_id"] for r in self.rounds):
            return
        self.rounds.append(results)
        self.save()

    def summary(self, last: int = 3) -> str:
        """A few short lines for the LLM prompt."""
        # TODO: this only looks at the last few rounds. Trends over the whole game, per buyer persona,
        #       may tell you more (ผู้ซื้อแต่ละรายมีนิสัยต่างกัน)
        lines = []
        for rnd in self.rounds[-last:]:
            sent = {(o["rfq_id"], o["lot_id"]): o for o in self.sent.get(rnd["round_id"], [])}
            mine = []
            for o in rnd["my_offers"]:
                s = sent.get((o["rfq_id"], o["lot_id"]), {})
                mine.append(f"{s.get('buyer_type', '?')} x{s.get('markup', '?')} {o['status']}")
            by_type = defaultdict(lambda: [0, 0])
            for row in rnd["market_summary"]:
                by_type[row["buyer_type"]][0] += row["wanted_kg"]
                by_type[row["buyer_type"]][1] += row["bought_kg"]
            market = ", ".join(f"{t} bought {b * 100 // max(w, 1)}% of wanted" for t, (w, b) in by_type.items())
            lines.append(f"{rnd['round_id']}: my offers [{'; '.join(mine) or 'none'}]; market: {market}")
        return "\n".join(lines) or "none yet"
