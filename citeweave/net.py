"""Bounded HTTPS transport, cross-process arXiv pacing, retry telemetry."""
from contextlib import contextmanager
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError
import http.client
import os
import socket
import time


class TransferError(Exception):
    def __init__(self, reason, status=None):
        self.reason, self.status = reason, status
        super().__init__(reason)


def allowed_url(url):
    u = urlsplit(url)
    if u.scheme != "https" or u.hostname not in {"arxiv.org", "export.arxiv.org", "www.arxiv.org"} or u.username or u.password or u.port not in (None,443):
        raise TransferError("unapproved_url")


class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        allowed_url(newurl)
        return super().redirect_request(req,fp,code,msg,headers,newurl)


@contextmanager
def file_lock(path):
    """Released by the OS on crash, including on Windows."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as f:
        f.seek(0,2)
        if f.tell() == 0:
            f.write(b"0"); f.flush()
        f.seek(0)
        if os.name == "nt":
            import msvcrt
            # LK_LOCK has a bounded built-in wait. Propagate failure rather than run unlocked.
            msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            f.seek(0)
            if os.name == "nt":
                msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
            else:
                fcntl.flock(f.fileno(),fcntl.LOCK_UN)


class ArxivGate:
    def __init__(self, directory=None, interval=3.1):
        self.directory = Path(directory or Path.home()/".citeweave"/"arxiv")
        self.interval = interval

    @contextmanager
    def enter(self):
        start = time.monotonic()
        with file_lock(self.directory/"request.lock"):
            stamp = self.directory/"next-request.txt"
            try:
                delay = max(0,float(stamp.read_text())-time.time())
            except (OSError,ValueError):
                delay = 0
            if delay > 60:
                raise TransferError("rate_gate_clock_skew")
            if delay: time.sleep(delay)
            try:
                yield time.monotonic()-start
            finally:
                # Conservative: leave three seconds after completion, including failures.
                stamp.write_text(str(time.time()+self.interval),encoding="ascii")


class Client:
    def __init__(self, emit, contact="", gate=None, opener=None, sleep=time.sleep):
        self.emit = emit
        self.gate = gate or ArxivGate()
        self.opener = opener or build_opener(SafeRedirect())
        self.sleep = sleep
        self.user_agent = "CiteWeave-local-prototype/0.1.0a1" + (f" ({contact})" if contact else "")
        self.bytes_received = 0
        self.total_limit = None

    def fetch(self, url, destination, max_bytes, stage):
        allowed_url(url)
        path = Path(destination)
        path.parent.mkdir(parents=True,exist_ok=True)
        endpoint = urlsplit(url).hostname  # Never log query strings, headers or profile text.
        for attempt in range(1,4):
            status = None
            count = 0
            reason = None
            retry = False
            delay = 2**attempt
            started = time.monotonic()
            request_start = None
            try:
                with self.gate.enter() as waited:
                    self.emit("rate_wait",stage=stage,duration_s=waited)
                    request_start = time.monotonic()
                    try:
                        with self.opener.open(Request(url,headers={"User-Agent":self.user_agent}),timeout=20) as response:
                            status = response.status
                            allowed_url(response.geturl())
                            if status != 200: raise TransferError("unexpected_http_status",status)
                            advertised = response.headers.get("Content-Length")
                            if advertised and int(advertised)>max_bytes:
                                raise TransferError("size_limit",status)
                            with path.open("wb") as f:
                                while True:
                                    if time.monotonic()-request_start>60:
                                        raise TransferError("transfer_deadline",status)
                                    block=response.read(64*1024)
                                    if not block: break
                                    count+=len(block)
                                    self.bytes_received+=len(block)
                                    if count>max_bytes: raise TransferError("size_limit",status)
                                    if self.total_limit is not None and self.bytes_received>self.total_limit:
                                        raise TransferError("run_byte_limit",status)
                                    f.write(block)
                                f.flush(); os.fsync(f.fileno())
                            if advertised and count != int(advertised):
                                raise TransferError("truncated_response",status)
                        self.emit("request",stage=stage,host=endpoint,attempt=attempt,status=status,
                                  outcome="success",bytes=count,duration_s=time.monotonic()-request_start)
                        return count
                    except HTTPError as e:
                        status=e.code
                        retry=status in {408,429,500,502,503,504}
                        reason="rate_limited" if status==429 else "http_error"
                        ra=e.headers.get("Retry-After")
                        if ra:
                            try: delay=max(delay,float(ra))
                            except ValueError:
                                try: delay=max(delay,(parsedate_to_datetime(ra)-datetime.now(timezone.utc)).total_seconds())
                                except (TypeError,ValueError): retry=False
                        e.close()
                    except (URLError,TimeoutError,socket.timeout,http.client.HTTPException,ConnectionError):
                        retry=True; reason="network_error"
                    except TransferError as e:
                        reason=e.reason; status=e.status
                        retry=reason in {"truncated_response","transfer_deadline"}
            except TransferError as e:
                reason=e.reason
            except ValueError:
                reason="invalid_response_headers"
            path.unlink(missing_ok=True)
            self.emit("request",stage=stage,host=endpoint,attempt=attempt,status=status,outcome="failed",
                      reason=reason,bytes=count,duration_s=time.monotonic()-(request_start or started))
            if not retry or attempt==3 or delay>60:
                raise TransferError(reason or "transfer_failed",status)
            self.emit("retry_wait",stage=stage,duration_s=delay)
            self.sleep(delay)
        raise TransferError("transfer_failed")
