#!/usr/bin/env python3
"""Wait until this Mac is awake AND has DNS before run.sh contacts anything.

    python3 netgate.py          # exit 0 when ready, 3 when it gave up

Why (2026-10-12): the Monday 07:00 run fired while the laptop slept on battery,
lid shut. launchd ran it inside 45-second "dark wakes" (macOS maintenance wakes,
no display, network only now and then), so it harvested in fragments until the
lid opened at 08:11: 12 sources and all three OSPO lists failed on DNS, and the
run still published, because a failed source exits 0 by design.

So BOTH must hold before anything starts:
  * FULL wake - `pmset -g systemstate` lists the Graphics capability, which a
    dark wake never has. DNS alone is not enough: some dark wakes HAD network
    (FI, SE, NL... succeeded inside them) and would have passed, then the next
    sleep cut the harvest off again. No pmset (not a Mac) counts as awake.
  * DNS - any one of HOSTS resolves (it is the network that is in question,
    not one host; run.sh needs GitHub to push and Cloudflare to deploy).

It polls each INTERVAL seconds and gives up after MAX_WAIT of WALL time: a
sleeping Mac suspends this process, time.sleep() does not count the sleep,
and the wait simply resumes on the next wake. Giving up exits 3 and run.sh
stops before harvesting, so nothing publishes and every checkpoint is kept;
the live /catalogs then flags the run as overdue on its own clock.
"""
import socket
import subprocess
import sys
import time

HOSTS = ("github.com", "api.cloudflare.com")
INTERVAL = 60            # seconds between checks
MAX_WAIT = 12 * 3600     # wall-clock seconds before giving up
NOTE_EVERY = 1800        # log a "still waiting" line this often


def full_wake():
    """True in a full wake, False in a dark wake, True when it cannot tell."""
    try:
        out = subprocess.run(["pmset", "-g", "systemstate"], capture_output=True,
                             text=True, timeout=10).stdout
    except Exception:
        return True
    for line in out.splitlines():
        if "Capabilities" in line:
            return "Graphics" in line.split()
    return True


def dns_ok(hosts=HOSTS):
    for h in hosts:
        try:
            socket.getaddrinfo(h, 443)
            return True
        except Exception:
            pass
    return False


def why_not(awake, dns):
    """'' when ready, else what is missing."""
    missing = ([] if awake else ["full wake (the Mac is asleep or dark-waking)"]) + \
              ([] if dns else ["DNS (none of %s resolves)" % ", ".join(HOSTS)])
    return " and ".join(missing)


def wait(awake_fn=full_wake, dns_fn=dns_ok, now=time.time, sleep=time.sleep,
         max_wait=MAX_WAIT, interval=INTERVAL, log=print):
    """-> (ready, waited_seconds, last_reason). Checks at once, then every
    `interval` until ready or `max_wait` of `now()` time has passed."""
    t0 = now()
    noted = None
    while True:
        reason = why_not(awake_fn(), dns_fn())
        waited = now() - t0
        if not reason:
            log("netgate: ready after waiting %dm" % (waited // 60) if waited >= 60
                else "netgate: ready (full wake, DNS resolves)")
            return True, waited, ""
        if waited >= max_wait:
            log("netgate: GAVE UP after %dh - still no %s" % (waited // 3600, reason))
            return False, waited, reason
        if noted is None or now() - noted >= NOTE_EVERY:
            log("netgate: waiting for %s (checks every %ds, gives up after %dh)"
                % (reason, interval, max_wait // 3600))
            noted = now()
        sleep(interval)


if __name__ == "__main__":
    ok, _, _ = wait(log=lambda m: print(m, flush=True))
    sys.exit(0 if ok else 3)
