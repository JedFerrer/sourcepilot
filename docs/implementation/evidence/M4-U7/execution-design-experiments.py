"""Isolated planning experiments, not application code or acceptance tests.

Run with the existing apps/api virtualenv. No provider or database access.
All slow helpers finish or are terminated/reaped before this program exits.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextvars import ContextVar
import json
import multiprocessing as mp
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
from unittest.mock import patch


def dns_stall(host, port, *args, **kwargs):
    time.sleep(0.6)
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", port))]


async def lookup():
    async with asyncio.timeout(0.05):
        await asyncio.get_running_loop().getaddrinfo("fixture.invalid", 443)


def runner_dns():
    started = time.monotonic()
    with patch("socket.getaddrinfo", dns_stall):
        try:
            with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
                runner.run(lookup())
        except TimeoutError:
            pass
    return {"budget_s": 0.05, "return_s": round(time.monotonic() - started, 4)}


def application_loop_dns():
    entered, finished = threading.Event(), threading.Event()

    def resolver(*args, **kwargs):
        entered.set()
        try:
            return dns_stall(*args, **kwargs)
        finally:
            finished.set()

    async def request():
        start = time.monotonic()
        try:
            await lookup()
        except TimeoutError:
            pass
        return {"request_return_s": round(time.monotonic() - start, 4),
                "helper_entered": entered.is_set(), "helper_finished_at_return": finished.is_set()}

    with patch("socket.getaddrinfo", resolver):
        with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
            result = runner.run(request())
            start = time.monotonic()
        result["application_shutdown_s"] = round(time.monotonic() - start, 4)
    result["helper_finished_after_shutdown"] = finished.is_set()
    return result


def sdk_platform():
    # Exercise installed SDK setup, not just asyncio.to_thread in isolation.
    import httpx
    from openai import AsyncOpenAI

    entered, finished = threading.Event(), threading.Event()
    requests = []

    def platform():
        entered.set()
        try:
            time.sleep(0.6)
            return "Other"
        finally:
            finished.set()

    async def request():
        http = httpx.AsyncClient(transport=httpx.MockTransport(
            lambda request: requests.append(True) or httpx.Response(500)))
        client = AsyncOpenAI(api_key="synthetic-only", max_retries=0, http_client=http)
        start = time.monotonic()
        try:
            async with asyncio.timeout(0.05):
                await client.responses.create(model="fixture", input="fixture", store=False)
        except TimeoutError:
            pass
        finally:
            await client.close()
        return {"request_return_s": round(time.monotonic() - start, 4),
                "helper_entered": entered.is_set(), "helper_finished_at_return": finished.is_set(),
                "client_closed": http.is_closed, "transport_calls": len(requests)}

    with patch("openai._base_client.get_platform", platform):
        with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
            result = runner.run(request())
            start = time.monotonic()
        result["application_shutdown_s"] = round(time.monotonic() - start, 4)
    return result


def tracked_helpers():
    # Candidate admission principle only, not wired into HTTPX/psycopg.
    async def exercise():
        live = set()
        events = []

        async def attempt(index):
            if len(live) >= 2:
                events.append([index, "capacity_rejected"])
                return
            future = asyncio.get_running_loop().run_in_executor(None, time.sleep, 0.3)
            live.add(future)
            future.add_done_callback(live.discard)
            try:
                async with asyncio.timeout(0.03):
                    await asyncio.shield(future)
            except TimeoutError:
                events.append([index, "timed_out"])

        await asyncio.gather(attempt(1), attempt(2))
        at_timeout = len(live)
        await attempt(3)
        await asyncio.gather(*live)
        await asyncio.sleep(0)
        return {"events": events, "live_after_timeout": at_timeout, "live_after_drain": len(live)}

    with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
        return runner.run(exercise())


def tracked_real_dns():
    """Track underlying futures, not their cancelled asyncio wrappers."""
    owner = ContextVar("experiment_owner", default=None)
    live = {}
    lock = threading.Lock()

    class Executor(ThreadPoolExecutor):
        def submit(self, function, /, *args, **kwargs):
            request = owner.get()
            future = super().submit(function, *args, **kwargs)
            if request is not None:
                with lock:
                    live.setdefault(request, set()).add(future)

                def done(completed):
                    with lock:
                        live[request].discard(completed)

                future.add_done_callback(done)
            return future

    async def exercise():
        asyncio.get_running_loop().set_default_executor(Executor(max_workers=2))
        for request in ("one", "two"):
            token = owner.set(request)
            try:
                await lookup()
            except TimeoutError:
                pass
            finally:
                owner.reset(token)
        with lock:
            at_timeout = {key: len(value) for key, value in live.items()}
        # Admission would retain both slots and reject a third request here.
        await asyncio.sleep(0.7)
        with lock:
            drained = {key: len(value) for key, value in live.items()}
        return {"underlying_futures_after_cancellation": at_timeout, "after_drain": drained}

    with patch("socket.getaddrinfo", dns_stall):
        with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
            return runner.run(exercise())


def cleanup_experiments():
    async def exercise(mode):
        events = []
        start = time.monotonic()
        end = start + (0 if mode == "exhausted" else 0.1)

        async def close():
            events.append("close_started")
            if mode == "failure":
                raise RuntimeError("synthetic")
            if mode == "cancelled":
                raise asyncio.CancelledError()
            if mode == "blocking":
                time.sleep(0.2)
            else:
                await asyncio.sleep(0.2)
            events.append("close_finished")

        async def dispose():
            events.append("dispose_started")
            await asyncio.sleep(0)
            events.append("dispose_finished")

        for name, action in [("close", close), ("dispose", dispose)]:
            seconds = max(0, min(0.04, end - time.monotonic()))
            try:
                async with asyncio.timeout(seconds):
                    await action()
            except (TimeoutError, RuntimeError, asyncio.CancelledError) as error:
                events.append(name + "_" + type(error).__name__)
        return {"events": events, "elapsed_s": round(time.monotonic() - start, 4)}

    with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
        return {mode: runner.run(exercise(mode))
                for mode in ("reserved", "failure", "cancelled", "exhausted", "blocking")}


def child(connection, mode):
    connection.send("ready")
    try:
        if mode == "dns":
            def blocked(*args, **kwargs):
                connection.send("dns_entered")
                time.sleep(2)
                return []
            with patch("socket.getaddrinfo", blocked):
                with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
                    async def run():
                        await asyncio.get_running_loop().getaddrinfo("fixture.invalid", 443)
                    runner.run(run())
        else:
            connection.send("close_entered")
            time.sleep(2)
        connection.send("late_result")
    finally:
        connection.send("graceful_finally")
        connection.close()


def process_experiment(mode):
    context = mp.get_context("spawn")
    parent, child_end = context.Pipe(duplex=False)
    process = context.Process(target=child, args=(child_end, mode))
    start = time.monotonic()
    process.start()
    child_end.close()
    events = []
    try:
        while len(events) < 2 and time.monotonic() - start < 1.0:
            if parent.poll(0.01):
                events.append(parent.recv())
        entered_at = time.monotonic() - start
        process.terminate()
        process.join(timeout=0.5)
        elapsed = time.monotonic() - start
        alive = process.is_alive()
        while True:
            try:
                if not parent.poll():
                    break
                events.append(parent.recv())
            except (EOFError, BrokenPipeError):
                break
        return {"events": events, "startup_and_enter_s": round(entered_at, 4),
                "startup_through_reap_s": round(elapsed, 4), "alive_after_join": alive,
                "exitcode": process.exitcode}
    finally:
        if process.is_alive():
            process.kill()
            process.join(timeout=2)
        assert not process.is_alive()
        process.close()
        parent.close()


def parent_death():
    with tempfile.TemporaryDirectory(prefix="sourcepilot-design-") as directory:
        marker = Path(directory) / "finished.txt"
        child_code = "import time,pathlib; time.sleep(.5); pathlib.Path(" + repr(str(marker)) + ").write_text('finished')"
        parent_code = ("import subprocess,sys,os; p=subprocess.Popen([sys.executable,'-c',"
                       + repr(child_code) + "],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); "
                       "print(p.pid,flush=True); os._exit(0)")
        parent = subprocess.Popen([sys.executable, "-c", parent_code], stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        stdout, _ = parent.communicate(timeout=3)
        pid = int(stdout.strip())
        start = time.monotonic()
        while not marker.exists() and time.monotonic() - start < 2:
            time.sleep(0.01)
        survived = marker.exists()
        # The child is deliberately finite. Reap/confirm Windows process exit.
        if sys.platform == "win32":
            import ctypes
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel.OpenProcess.restype = ctypes.c_void_p
            handle = kernel.OpenProcess(0x00100000 | 0x0001, False, pid)
            if handle:
                try:
                    if kernel.WaitForSingleObject(ctypes.c_void_p(handle), 2000) != 0:
                        kernel.TerminateProcess(ctypes.c_void_p(handle), 1)
                        kernel.WaitForSingleObject(ctypes.c_void_p(handle), 2000)
                finally:
                    kernel.CloseHandle(ctypes.c_void_p(handle))
        return {"parent_exitcode": parent.returncode, "child_completed_after_parent_exit": survived}


if __name__ == "__main__":
    results = {"platform": sys.platform, "python": sys.version.split()[0],
               "request_runner_dns": runner_dns(), "application_loop_dns": application_loop_dns(),
               "sdk_platform_on_application_loop_cold": sdk_platform(),
               "sdk_platform_on_application_loop_warm": sdk_platform(),
               "tracked_helper_admission": tracked_helpers(), "tracked_real_dns": tracked_real_dns(),
               "cleanup": cleanup_experiments(),
               "process_dns": process_experiment("dns"),
               "process_cleanup": process_experiment("cleanup"), "abrupt_parent_death": parent_death()}
    print(json.dumps(results, indent=2))
