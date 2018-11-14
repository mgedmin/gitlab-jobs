#!/usr/bin/env python3
"""
Show GitLab pipeline job durations.
"""

import argparse
import csv
from collections import defaultdict
from statistics import mean, median, stdev

# pip install python-gitlab
import gitlab


__version__ = '0.2'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--version', action='version',
        # *sigh* argparse converts the \n to a space anyway
        version="%(prog)s version {version},\n"
                "python-gitlab version {python_gitlab_version}".format(
                    version=__version__,
                    python_gitlab_version=gitlab.__version__,
                ),
    )
    parser.add_argument(
        '-g', '--gitlab',
        help='select configuration section in ~/.python-gitlab.cfg',
    )
    parser.add_argument(
        '-p', '--project', metavar='ID', required=True,
        help='select GitLab project (you can discover project IDs by running'
             ' gitlab project list --all)',
    )
    parser.add_argument(
        '-b', '--branch', '--ref', metavar='REF', default='master',
        help='select git branch',
    )
    parser.add_argument(
        '-l', '--limit', metavar='N', default=20, type=int,
        help='limit analysis to last N pipelines (max 100)',
    )
    parser.add_argument(
        '--csv', metavar='FILENAME',
        help='export raw data to CSV file',
    )
    args = parser.parse_args()

    gl = gitlab.Gitlab.from_config(args.gitlab)
    project = gl.projects.get(args.project)

    job_durations = defaultdict(list)

    print("Last {n} successful pipelines of {project} {ref}:".format(
        n=args.limit, ref=args.branch, project=project.name))
    pipelines = project.pipelines.list(
        scope='finished', status='success', ref=args.branch,
        per_page=args.limit)
    for pipeline in pipelines:
        print("  {id} (commit {sha})".format(**pipeline.attributes))
        for job in pipeline.jobs.list(scope='success', all=True):
            job_durations[job.name].append(job.duration)

    print("\nSummary:")
    maxlen = max(len(name) for name in job_durations)
    digits = 4.1
    unit = "m", 60.0
    for job_name, durations in sorted(job_durations.items()):
        print(
            "  {name:{maxlen}} "
            " min {min:{digits}f}{unit},"
            " max {max:{digits}f}{unit},"
            " avg {avg:{digits}f}{unit},"
            " median {median:{digits}f}{unit},"
            " stdev {stdev:{digits}f}{unit}"
            .format(
                name=job_name,
                maxlen=maxlen,
                digits=digits,
                unit=unit[0],
                min=min(durations) / unit[1],
                max=max(durations) / unit[1],
                avg=mean(durations) / unit[1],
                median=median(durations) / unit[1],
                stdev=stdev(durations) / unit[1] if len(durations) > 1 else 0,
            )
        )

    if args.csv:
        print("\nWriting {filename}...".format(filename=args.csv))
        with open(args.csv, 'w') as f:
            writer = csv.writer(f)
            for job_name, durations in sorted(job_durations.items()):
                writer.writerow([job_name] + durations)


if __name__ == '__main__':
    main()
