# One-off seed generators

**Not part of `run.sh`.** These re-seed hand-maintained data files from NYC's
software licence export, which is deliberately **not vendored** — it is NYC's to
publish and the export URL is the durable reference. `run.sh` must never reach
api.databook.nyc, so the pipeline stays offline and deterministic.

```bash
curl -s https://api.databook.nyc/oce/licenses/export -o /tmp/nyc.csv
python3 scripts/gen_proprietary.py /tmp/nyc.csv   # seeds proprietary.json + product_aliases.json
python3 scripts/gen_meta.py        /tmp/nyc.csv   # rebuilds proprietary.json with desc + function
```

Run from the repo root. **Review the diff** — `gen_meta.py` carries the
hand-written descriptions and hand-assigned functions inline, so re-running it
without merging your edits will drop them. See `DEMAND-SIDE-CATALOGUE.md`.
