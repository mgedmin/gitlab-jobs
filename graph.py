#!/usr/bin/env python3
"""
Graph GitLab pipeline job durations.
"""

import argparse
import csv
import math
import signal
import sys
from typing import List, Optional, Tuple

# apt install python3-matplotlib
import matplotlib.pyplot as plt


__version__ = '0.3.0'


JobInfo = Tuple[str, List[float]]


def load_csv(filename: str) -> List[JobInfo]:
    jobs = []
    with open(filename) as f:
        reader = csv.reader(f)
        for row in reader:
            if row:
                job_name = row[0]
                durations = list(map(float, row[1:]))
                jobs.append((job_name, durations))
    return jobs


def filter_jobs(
    jobs: List[JobInfo],
    *,
    select: Optional[List[str]] = None,
    exclude: Optional[List[str]] = None,
) -> List[JobInfo]:
    result = []
    for job, durations in jobs:
        if select and job not in select:
            continue
        if exclude and job in exclude:
            continue
        result.append((job, durations))
    return result


def disable_sigint_handling() -> None:
    # matplotlib uses tkinter which handles signals only when the window is
    # focused, making it awkward to abort the script with a ^C when you focus
    # the terminal where the script is running.
    signal.signal(signal.SIGINT, signal.SIG_DFL)


def plot_jobs(jobs: List[JobInfo], *, last: Optional[int] = None) -> None:
    fig, ax = plt.subplots()
    ax.set_title('Duration of build jobs (minutes)', color='#808080',
                 pad=8, fontdict=dict(fontsize=14))
    ax.set_xlabel('builds (newest on the right)', color='#404040',
                  labelpad=16)
    ax.set_frame_on(False)
    xmin = xmax = 1  # type: float
    ymin = ymax = 0
    for job, durations in jobs:
        if last:
            durations = durations[:last]
        xs = list(range(1, 1 + len(durations)))  # type: List[float]
        xmax = max(xmax, len(durations))
        ys = [duration / 60.0 for duration in durations[::-1]]
        ymax = max(ymax, math.ceil(max(ys)))
        xs[0] -= 0.5
        xs[-1] += 0.5
        ax.step(xs, ys, label=job, where='mid')
        ax.fill_between(xs, ys, step='mid', alpha=0.3)
    xmin -= 0.5
    xmax += 0.5
    ax.set_xlim(xmin=xmin, xmax=xmax)
    ax.set_ylim(ymin=ymin)
    ax.xaxis.set_major_locator(plt.MaxNLocator(nbins=20, integer=True))
    ax.set_axisbelow(True)
    ax.grid(axis='y', color='#cccccc')
    # there's no gridline drawn at y=0 so we draw one manually
    # and also make it darker
    ax.axhline(0, color='#808080')
    # the tick at y=0 is not aligned with the gridline at y=0, so we make the
    # ticks invisible
    ax.tick_params(color='#ffffff', labelcolor='#808080', labelbottom=False)
    ax.legend(frameon=False)
    plt.show()


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot job durations")
    parser.add_argument(
        "--version", action="version",
        version="%(prog)s version " + __version__,
    )
    parser.add_argument(
        "filename",
        help=(
            "CSV file to load; each row should have a job name followed by"
            " a series of durations in seconds (newest builds first)"
        ),
    )
    parser.add_argument(
        "-j", "--job", metavar='NAME', action='append', dest='jobs',
        help="One or more job names to plot (default: all of them)",
    )
    parser.add_argument(
        "-x", "--exclude-job", metavar='NAME', action='append',
        dest='exclude_jobs',
        help=(
            "One or more job names to exclude from the plot (e.g. -x overall)"
        ),
    )
    parser.add_argument(
        "-l", "--last", metavar='N', type=int,
        help="Limit the graph to the last N jobs (default: unlimited)",
    )
    args = parser.parse_args()

    jobs = load_csv(args.filename)

    filtered_jobs = filter_jobs(
        jobs, select=args.jobs, exclude=args.exclude_jobs)
    if jobs and not filtered_jobs:
        print(f"No jobs selected.  Job names in {args.filename}:")
        for job_name, durations in jobs:
            print(f"  {job_name}")
        sys.exit(1)

    disable_sigint_handling()

    plot_jobs(filtered_jobs, last=args.last)


if __name__ == "__main__":
    main()
