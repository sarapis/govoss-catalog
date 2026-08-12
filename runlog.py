#!/usr/bin/env python3
"""Append a structured record of this run to history.json.

Called last by run.sh. The status page is built from this file, so anything the
page needs to show has to be recorded here — and only things that actually
happened. No back-filling, no estimates.

Step outcomes come from out/steps.tsv, which run.sh writes as it goes (one
`name<TAB>exit` line per step). That is the only way to know a step FAILED:
reading the end state alone cannot distinguish "harvest failed and later steps
ran on stale data" from "harvest succeeded" — which is exactly the silent
partial run that once produced a full green log with a dead harvest inside it.
"""
import json, os, sys, time, collections

OUT = os.path.dirname(os.path.abspath(__file__))
HIST = f"{OUT}/history.json"
MAX_RUNS = 200


def load(path, default=None):
    try:
        return json.load(open(path))
    except Exception:
        return default


def main():
    started = sys.argv[1] if len(sys.argv) > 1 else None
    trigger = sys.argv[2] if len(sys.argv) > 2 else "manual"
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    hist = load(HIST, {"schema": 1, "runs": []}) or {"schema": 1, "runs": []}
    prev = hist["runs"][-1] if hist["runs"] else None

    catalog = load(f"{OUT}/catalog.json", []) or []
    live = load(f"{OUT}/liveness.json", {}) or {}
    lsum = live.get("summary", {})

    active = [r for r in catalog if not r.get("excluded")]
    excluded = [r for r in catalog if r.get("excluded")]

    # per-source counts come from the checkpoints, so a source that FAILED this
    # run shows its stale count rather than silently reading as zero
    sources = {}
    cache = f"{OUT}/cache"
    # written by harvest.py; absent on older runs and on a --from-cache rebuild
    timing = load(f"{cache}/_timing.json", {}) or {}
    if os.path.isdir(cache):
        for f in sorted(os.listdir(cache)):
            if f.startswith("src_") and f.endswith(".json"):
                key = f[4:-5]
                rows = load(f"{cache}/{f}", []) or []
                sources[key] = {
                    "records": len(rows),
                    "checkpoint_mtime": time.strftime(
                        "%Y-%m-%dT%H:%M:%SZ", time.gmtime(os.path.getmtime(f"{cache}/{f}"))),
                    "seconds": timing.get(key),
                }

    steps, failures = [], {}
    sp = f"{OUT}/out/steps.tsv"
    if os.path.exists(sp):
        for line in open(sp):
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 2:
                name, code = parts[0], parts[1]
                ok = code == "0"
                # third column is seconds, added when the status page started
                # reporting each step's share of the run. Older rows have two
                # columns, so this stays optional rather than assuming.
                secs = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else None
                steps.append({"step": name, "ok": ok,
                              "exit": int(code) if code.isdigit() else code,
                              "duration_s": secs})
                if not ok:
                    failures[name] = f"exit {code}"

    catalogues = collections.Counter(
        s for r in active for s in (r.get("sources") or [r.get("source")]) if s)

    translated = sum(1 for r in active if r.get("translated"))
    described = sum(1 for r in active if r.get("short_desc"))
    src_en = sum(1 for r in active if r.get("short_desc") and not r.get("translated"))

    rec = {
        "run_at": now,
        "started_at": started,
        "trigger": trigger,
        "duration_s": None,
        "ok": not failures,
        "steps": steps,
        "failures": failures,
        "entries": {
            "active": len(active),
            "filtered_out": len(excluded),
            "publiccode_tier": sum(1 for r in active if r.get("tier") == "publiccode"),
            "merged_away": sum(r.get("merged_count", 1) - 1 for r in active),
            "multi_country": sum(1 for r in active if len(r.get("countries") or []) > 1),
        },
        "sources": sources,
        "catalogues": dict(catalogues),
        "translation": {
            "described": described,
            "source_english": src_en,
            "machine_translated": translated,
            "coverage_pct": round(100 * (src_en + translated) / described, 1) if described else None,
        },
        "categorisation": {
            "classified": sum(1 for r in active if r.get("functions")),
            "inferred": sum(1 for r in active if r.get("functions_inferred") and r.get("functions")),
            "unclassified": sum(1 for r in active if not r.get("functions")),
        },
        "liveness": {
            "checked": lsum.get("checked"),
            "total": lsum.get("total"),
            "ok": lsum.get("ok"),
            "dead": lsum.get("dead"),
            "pending_dead": lsum.get("pending_dead"),
            "unknown": lsum.get("unknown"),
            "archived": lsum.get("archived"),
            "newly_dead": lsum.get("newly_dead") or [],
            "revived": lsum.get("revived") or [],
        },
        "filters": dict(collections.Counter(r.get("exclude_reason") for r in excluded)),
    }

    if started:
        try:
            a = time.mktime(time.strptime(started, "%Y-%m-%dT%H:%M:%SZ"))
            b = time.mktime(time.strptime(now, "%Y-%m-%dT%H:%M:%SZ"))
            rec["duration_s"] = int(b - a)
        except Exception:
            pass

    # deltas vs the previous recorded run — the changelog is built from these
    if prev:
        d = {"entries_active": rec["entries"]["active"] - prev["entries"]["active"]}
        ps = prev.get("sources") or {}
        per = {k: v["records"] - ps.get(k, {}).get("records", 0)
               for k, v in sources.items()
               if v["records"] != ps.get(k, {}).get("records")}
        if per:
            d["per_source"] = per
        for k in ("dead", "ok", "unknown"):
            pv, cv = (prev.get("liveness") or {}).get(k), rec["liveness"].get(k)
            if isinstance(pv, int) and isinstance(cv, int) and pv != cv:
                d[f"liveness_{k}"] = cv - pv
        rec["delta"] = d

    hist["runs"].append(rec)
    hist["runs"] = hist["runs"][-MAX_RUNS:]
    hist["updated_at"] = now
    json.dump(hist, open(HIST, "w"), indent=1, default=str)

    print(f"[runlog] recorded run {now} trigger={trigger} "
          f"ok={rec['ok']} active={rec['entries']['active']} "
          f"({len(hist['runs'])} runs in history)")
    if failures:
        print(f"[runlog] FAILURES: {failures}")
    if rec.get("delta"):
        print(f"[runlog] delta: {rec['delta']}")


if __name__ == "__main__":
    main()
