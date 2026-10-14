#!/usr/bin/env python3
"""Regression test for netgate.py and its place at the head of run.sh.

    python3 test_netgate.py

2026-10-12: the Monday run fired while the laptop slept, ran in 45-second dark
wakes, lost 12 sources and all three OSPO lists to DNS, and published anyway.
netgate.wait() must hold the run until a FULL wake with DNS - not DNS alone, since
some dark wakes had network - must measure its give-up on the WALL clock (a
sleeping Mac suspends the process), and run.sh must stop before harvesting when
it gives up. Offline: the clock, sleep, pmset and DNS are all faked.
"""
import os
import shutil
import socket
import subprocess
import sys
import tempfile

import netgate as g

failed, ran = [], []


def check(label, got, want):
    ran.append(label)
    if got != want:
        failed.append("%s: expected %r, got %r" % (label, want, got))


class Clock:
    def __init__(self):
        self.t, self.slept = 1_000_000.0, []

    def now(self):
        return self.t

    def sleep(self, s):
        if len(self.slept) > 10000:          # a wait with no working give-up fails, not hangs
            raise RuntimeError("runaway: more than 10,000 checks")
        self.slept.append(s)
        self.t += s


def run(states, max_wait=600, interval=60, jump=None):
    """states: list of (awake, dns) per check; the last repeats. jump: seconds the
    wall clock leaps during the first sleep (a Mac asleep while we wait)."""
    c, logs, i = Clock(), [], [0]

    def cur():
        return states[min(i[0], len(states) - 1)]

    def awake():
        return cur()[0]

    def dns():
        s = cur()[1]
        i[0] += 1
        return s

    def sleep(s):
        c.sleep(s)
        if jump and len(c.slept) == 1:
            c.t += jump
    try:
        ok, waited, reason = g.wait(awake, dns, c.now, sleep, max_wait, interval, logs.append)
    except RuntimeError as ex:
        return "runaway", None, str(ex), c.slept, logs
    return ok, waited, reason, c.slept, logs


# ---- the gate
ok, waited, reason, slept, logs = run([(True, True)])
check("ready at once: passes without sleeping", (ok, waited, slept), (True, 0.0, []))
check("...and says so in the log", logs, ["netgate: ready (full wake, DNS resolves)"])

ok, _, _, slept, logs = run([(False, True), (False, True), (True, True)])
check("a DARK wake with DNS is not ready (DNS alone passed some dark wakes)",
      (ok, len(slept)), (True, 2))
check("...and the log names the missing full wake", "full wake" in logs[0], True)

ok, _, _, slept, logs = run([(True, False), (True, True)])
check("awake without DNS waits for DNS", (ok, len(slept), "DNS" in logs[0]), (True, 1, True))

ok, waited, reason, slept, logs = run([(False, False)], max_wait=600, interval=60)
check("never ready: gives up once max_wait has passed, not before",
      (ok, waited, len(slept)), (False, 600.0, 10))
check("...naming both missing conditions", ("full wake" in reason, "DNS" in reason), (True, True))
check("...and logging GAVE UP", logs[-1].startswith("netgate: GAVE UP"), True)

ok, waited, _, slept, _ = run([(False, False)], max_wait=600, interval=60, jump=13 * 3600)
check("give-up runs on the WALL clock: a sleep longer than max_wait ends it at the next check",
      (ok, len(slept)), (False, 1))

ok, _, _, slept, logs = run([(False, True)] * 70 + [(True, True)], max_wait=7200, interval=60)
check("'waiting' is logged at the start and every NOTE_EVERY, not every check",
      sum(1 for m in logs if m.startswith("netgate: waiting")), 1 + (70 * 60) // g.NOTE_EVERY)
check("...and the ready line reports the minutes waited", logs[-1], "netgate: ready after waiting 70m")

# ---- full_wake(): the pmset readout
real_run = subprocess.run


def fake_pmset(out=None, exc=None):
    def f(*a, **k):
        if exc:
            raise exc
        return subprocess.CompletedProcess(a, 0, stdout=out, stderr="")
    return f


try:
    for out, want, label in (
            ("Current System Capabilities are: CPU Graphics Audio Network \nCurrent Power State: 4\n",
             True, "a full wake lists Graphics"),
            ("Current System Capabilities are: CPU Network \nCurrent Power State: 4\n",
             False, "a dark wake (no Graphics) is NOT awake"),
            ("something unexpected\n", True, "no Capabilities line: cannot tell, counts as awake")):
        g.subprocess.run = fake_pmset(out)
        check("full_wake: " + label, g.full_wake(), want)
    g.subprocess.run = fake_pmset(exc=FileNotFoundError("pmset"))
    check("full_wake: no pmset (not a Mac) counts as awake", g.full_wake(), True)
finally:
    g.subprocess.run = real_run

# ---- dns_ok(): ANY host resolving is enough - it is the network in question
real_gai = socket.getaddrinfo
try:
    def gai(ok_hosts):
        def f(host, *a, **k):
            if host in ok_hosts:
                return [("ok",)]
            raise socket.gaierror(8, "nodename nor servname provided, or not known")
        return f
    g.socket.getaddrinfo = gai({"api.cloudflare.com"})
    check("dns_ok: one host of several resolving is enough", g.dns_ok(), True)
    g.socket.getaddrinfo = gai(set())
    check("dns_ok: Errno 8 for every host is no DNS", g.dns_ok(), False)
finally:
    g.socket.getaddrinfo = real_gai

# ---- run.sh: a gate that gives up stops the run BEFORE anything else.
# Behavioural, not a grep: run a copy of run.sh beside a netgate.py that exits 3
# and a harvest.py that would leave a mark, and look at what happened.
here = os.path.dirname(os.path.abspath(__file__))
tmp = tempfile.mkdtemp()
try:
    shutil.copy(os.path.join(here, "run.sh"), tmp)
    open(os.path.join(tmp, "netgate.py"), "w").write("import sys; print('gate: no'); sys.exit(3)\n")
    open(os.path.join(tmp, "harvest.py"), "w").write("open('HARVESTED', 'w').write('x')\n")
    for args in ([], ["--no-harvest"]):
        p = subprocess.run(["bash", os.path.join(tmp, "run.sh")] + args, capture_output=True,
                           text=True, timeout=60)
        tag = " ".join(args) or "full run"
        check("run.sh (%s): a gate that gives up exits 1" % tag, p.returncode, 1)
        check("run.sh (%s): ...says NOT RUNNING" % tag, "NOT RUNNING" in p.stderr, True)
        check("run.sh (%s): ...and nothing ran - no harvest, no out/steps.tsv" % tag,
              (os.path.exists(os.path.join(tmp, "HARVESTED")),
               os.path.exists(os.path.join(tmp, "out", "steps.tsv"))), (False, False))
    # and a gate that passes is followed by the idle-sleep hold, tied to run.sh's pid
    src = open(os.path.join(here, "run.sh")).read()
    code = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("#"))
    gate, hold, harvest = (code.find('"$PY" -u netgate.py'), code.find("caffeinate -i -w $$"),
                           code.find('step "harvest"'))
    check("run.sh: gate, then caffeinate -i -w $$, then the first step (code, not comments)",
          -1 < gate < hold < harvest and code.find("step ") > gate, True)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

for f in failed:
    print("FAIL  " + f)
print("\n%d/%d checks passed" % (len(ran) - len(failed), len(ran)))
sys.exit(1 if failed else 0)
