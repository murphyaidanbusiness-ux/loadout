from logparse import parse_line


def test_nginx_basic():
    rec = parse_line('1.2.3.4 - - [10/Oct/2026:13:55:36 +0000] "GET /a HTTP/1.1" 200 512')
    assert rec["kind"] == "nginx" and rec["status"] == 200 and rec["size"] == 512


def test_nginx_no_body():
    rec = parse_line('1.2.3.4 - - [10/Oct/2026:13:55:36 +0000] "HEAD /a HTTP/1.1" 304 -')
    assert rec["size"] == 0


def test_syslog():
    rec = parse_line("Oct 10 13:55:36 web1 sshd[812]: Accepted publickey for deploy")
    assert rec["kind"] == "syslog" and rec["pid"] == "812"


def test_blank():
    assert parse_line("   ") is None
