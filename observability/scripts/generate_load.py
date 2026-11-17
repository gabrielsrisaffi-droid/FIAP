"""Synthetic HTTP load; the service creates root spans by default. No AWS required."""

import argparse
import collections
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

parser = argparse.ArgumentParser()
parser.add_argument("--url", default="http://127.0.0.1:8004/evaluate")
parser.add_argument("--flag", default="phase4-demo")
parser.add_argument("--seconds", type=int, default=240)
parser.add_argument("--rate", type=float, default=2)
parser.add_argument("--allow-errors", action="store_true", help="Use during controlled fault injection")
parser.add_argument("--remote-parent", action="store_true",
                    help="Propagation probe only: inject an unexported W3C parent (incomplete trace)")
args = parser.parse_args()
if args.seconds <= 0 or not 0 < args.rate <= 20:
    parser.error("Use seconds > 0 and 0 < rate <= 20")
if urllib.parse.urlparse(args.url).scheme not in ("http", "https"):
    parser.error("An HTTP(S) URL is required")
counts = collections.Counter()
deadline = time.monotonic() + args.seconds
while time.monotonic() < deadline:
    started = time.monotonic()
    # An invented traceparent references a parent span that is never exported.
    # Leave it absent for APM demonstrations so the server starts a complete trace.
    trace_id = uuid.uuid4().hex if args.remote_parent else "server-generated"
    headers = {"traceparent": f"00-{trace_id}-{uuid.uuid4().hex[:16]}-01"} if args.remote_parent else {}
    query = urllib.parse.urlencode({"flag_name": args.flag, "user_id": "synthetic-" + uuid.uuid4().hex[:8]})
    request = urllib.request.Request(args.url + "?" + query, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            status = response.status
    except urllib.error.HTTPError as error:
        status = error.code
    except urllib.error.URLError:
        status = "connection-error"
    counts[str(status)] += 1
    total = sum(counts.values())
    if total <= 3 or total % 20 == 0:
        print(f"request={total} status={status} trace_id={trace_id} totals={dict(counts)}", flush=True)
    time.sleep(max(0, 1 / args.rate - (time.monotonic() - started)))
print(dict(counts))
if not args.allow_errors and any(status != "200" for status in counts):
    raise SystemExit(1)
