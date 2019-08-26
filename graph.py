#!/usr/bin/env python3
"""
Graph GitLab pipeline job durations.
"""

import argparse
import csv
import math
import signal

# apt install python3-matplotlib
import matplotlib as mpl
import matplotlib.pyplot as plt


__version__ = '0.1.0'


def load_csv(filename):
    jobs = []
    with open(filename) as f:
        reader = csv.reader(f)
        for row in reader:
            if row:
                job_name = row[0]
                durations = list(map(float, row[1:]))
                jobs.append((job_name, durations))
    return jobs


def disable_sigint_handling():
    # matplotlib uses tkiter which handles signals only when the window is
    # focused, making it awkward to abort the script with a ^C when you focus
    # the terminal where the script is running.
    signal.signal(signal.SIGINT, signal.SIG_DFL)


def plot_jobs(jobs, select, exclude):
    mpl.style.use('seaborn')
    plt.title('Duration of build jobs')
    plt.ylabel('minutes')
    plt.xlabel('builds (newest on the right)')
    xmin = xmax = 1
    ymin = ymax = 0
    for job, durations in jobs:
        if select and job not in select:
            continue
        if exclude and job in exclude:
            continue
        xs = list(range(1, 1 + len(durations)))
        xmax = max(xmax, len(durations))
        ys = [duration / 60.0 for duration in durations[::-1]]
        ymax = max(ymax, math.ceil(max(ys)))
        plt.plot(xs, ys, label=job)
    plt.xticks(range(xmin, xmax + 1))
    plt.axis([xmin, xmax, ymin, ymax])
    plt.legend()
    plt.show()


def main():
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
    args = parser.parse_args()

    jobs = load_csv(args.filename)

    disable_sigint_handling()

    plot_jobs(jobs, select=args.jobs, exclude=args.exclude_jobs)


if __name__ == "__main__":
    main()
