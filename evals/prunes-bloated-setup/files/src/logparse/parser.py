"""Parse nginx access-log and syslog lines."""
import re
from datetime import datetime

NGINX = re.compile(
    r'(?P<ip>\S+) \S+ \S+ \[(?P<ts>[^\]]+)\] "(?P<method>\S+) (?P<path>\S+) \S+" (?P<status>\d{3}) (?P<size>\d+|-)'
)
SYSLOG = re.compile(r"(?P<ts>\w{3}\s+\d+ \d\d:\d\d:\d\d) (?P<host>\S+) (?P<proc>[^:\[]+)(\[(?P<pid>\d+)\])?: (?P<msg>.*)")


def parse_line(line: str) -> dict | None:
    line = line.strip()
    if not line:
        return None
    m = NGINX.match(line)
    if m:
        d = m.groupdict()
        d["kind"] = "nginx"
        d["status"] = int(d["status"])
        d["size"] = int(d["size"])  # bug: "-" means no body
        d["ts"] = datetime.strptime(d["ts"], "%d/%b/%Y:%H:%M:%S %z")
        return d
    m = SYSLOG.match(line)
    if m:
        d = m.groupdict()
        d["kind"] = "syslog"
        return d
    return None


def parse_file(path: str) -> list[dict]:
    out = []
    with open(path) as f:
        for line in f:
            rec = parse_line(line)
            if rec:
                out.append(rec)
    return out
