#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "matplotlib",
# ]
# ///

"""Parse `wrk --latency` outputs and generate charts.

Expected inputs (default):
  results/bun_c<connections>.txt
  results/node_c<connections>.txt

Outputs:
  rps_vs_connections.png
  p99_latency_vs_connections.png

Usage:
  uv run plot_wrk.py

Tips:
- Generate inputs like:
    mkdir -p results
    for c in 10 25 50 100 200 400 800 1000; do
      wrk -t12 -c"$c" -d30s --latency "http://localhost:$BUN_PORT/no" | tee "results/bun_c${c}.txt"
    done
    for c in 10 25 50 100 200 400 800 1000; do
      wrk -t12 -c"$c" -d30s --latency "http://localhost:$NODE_PORT/no" | tee "results/node_c${c}.txt"
    done

- If you get lots of connect errors at high concurrency on macOS, you may need:
    ulimit -n 100000
"""

from __future__ import annotations

import argparse
import glob
import os
import re
from dataclasses import dataclass

import matplotlib.pyplot as plt


@dataclass(frozen=True)
class WrkResult:
    connections: int
    requests_per_sec: float
    avg_latency_ms: float
    p50_latency_ms: float
    p99_latency_ms: float
    connect_errors: int


_UNIT_RE = re.compile(r"^(?P<value>[0-9.]+)(?P<unit>us|ms|s)$")


def _to_ms(duration: str) -> float:
    duration = duration.strip()
    m = _UNIT_RE.match(duration)
    if not m:
        return float("nan")
    value = float(m.group("value"))
    unit = m.group("unit")
    if unit == "us":
        return value / 1000.0
    if unit == "ms":
        return value
    if unit == "s":
        return value * 1000.0
    return float("nan")


def _extract_connections(path: str) -> int:
    m = re.search(r"_c(\d+)\.txt$", os.path.basename(path))
    if not m:
        raise ValueError(f"Cannot infer connections from filename: {path}")
    return int(m.group(1))


def parse_wrk_output(path: str) -> WrkResult:
    text = open(path, "r", encoding="utf-8", errors="ignore").read()
    connections = _extract_connections(path)

    m_rps = re.search(r"Requests/sec:\s+([0-9.]+)", text)
    if not m_rps:
        raise ValueError(f"Missing 'Requests/sec' in {path}")
    requests_per_sec = float(m_rps.group(1))

    # Example row:
    #   Latency     1.62ms   81.75us   5.61ms   92.17%
    m_avg = re.search(r"^\s*Latency\s+([0-9.]+(?:us|ms|s))\b", text, re.M)
    if not m_avg:
        raise ValueError(f"Missing latency table row in {path}")
    avg_latency_ms = _to_ms(m_avg.group(1))

    # Latency distribution:
    #      50%    1.61ms
    #      99%    1.78ms
    def dist(percent: int) -> float:
        m = re.search(rf"^\s*{percent}%\s+([0-9.]+(?:us|ms|s))\s*$", text, re.M)
        return _to_ms(m.group(1)) if m else float("nan")

    p50_latency_ms = dist(50)
    p99_latency_ms = dist(99)

    m_sock = re.search(
        r"Socket errors:\s+connect\s+(\d+),\s+read\s+(\d+),\s+write\s+(\d+),\s+timeout\s+(\d+)",
        text,
    )
    connect_errors = int(m_sock.group(1)) if m_sock else 0

    return WrkResult(
        connections=connections,
        requests_per_sec=requests_per_sec,
        avg_latency_ms=avg_latency_ms,
        p50_latency_ms=p50_latency_ms,
        p99_latency_ms=p99_latency_ms,
        connect_errors=connect_errors,
    )


def load_series(results_dir: str, prefix: str) -> list[WrkResult]:
    pattern = os.path.join(results_dir, f"{prefix}_c*.txt")
    paths = glob.glob(pattern)
    rows: list[WrkResult] = []
    for path in paths:
        try:
            rows.append(parse_wrk_output(path))
        except Exception as e:
            raise RuntimeError(f"Failed parsing {path}: {e}") from e
    return sorted(rows, key=lambda r: r.connections)


def _plot_metric(
    series: dict[str, list[WrkResult]],
    metric: str,
    ylabel: str,
    out_path: str,
    xlog: bool,
    title: str | None = None,
) -> None:
    plt.figure()

    for label, rows in series.items():
        if not rows:
            continue
        xs = [r.connections for r in rows]
        ys = [getattr(r, metric) for r in rows]
        plt.plot(xs, ys, marker="o", label=label)

    plt.xlabel("Connections (-c)")
    plt.ylabel(ylabel)

    if title:
        plt.title(title)

    if xlog:
        plt.xscale("log")

    plt.grid(True, which="both", linestyle="--", linewidth=0.5)
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)


def main() -> int:
    parser = argparse.ArgumentParser(description="Plot wrk results for bun vs node")
    parser.add_argument(
        "--results-dir", default="results", help="Directory with wrk outputs"
    )
    parser.add_argument(
        "--bun-prefix", default="bun", help="Filename prefix for bun results"
    )
    parser.add_argument(
        "--node-prefix", default="node", help="Filename prefix for node results"
    )
    parser.add_argument(
        "--no-xlog", action="store_true", help="Disable log scale for x axis"
    )

    args = parser.parse_args()

    bun = load_series(args.results_dir, args.bun_prefix)
    node = load_series(args.results_dir, args.node_prefix)

    if not bun and not node:
        raise SystemExit(
            f"No results found in '{args.results_dir}'. Expected files like '{args.bun_prefix}_c1000.txt'."
        )

    series = {"bun": bun, "node": node}
    xlog = not args.no_xlog

    _plot_metric(
        series,
        "requests_per_sec",
        "Requests/sec",
        "rps_vs_connections.png",
        xlog=xlog,
        title="Requests/sec (higher is better)",
    )
    _plot_metric(
        series,
        "p99_latency_ms",
        "p99 latency (ms)",
        "p99_latency_vs_connections.png",
        xlog=xlog,
        title="p99 latency (lower is better)",
    )

    # Optional: connect errors (useful to detect client-side saturation)
    if any(r.connect_errors for r in bun) or any(r.connect_errors for r in node):
        _plot_metric(
            series,
            "connect_errors",
            "Connect errors",
            "connect_errors_vs_connections.png",
            xlog=xlog,
        )

    print("Wrote rps_vs_connections.png and p99_latency_vs_connections.png")
    if os.path.exists("connect_errors_vs_connections.png"):
        print("Wrote connect_errors_vs_connections.png")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
