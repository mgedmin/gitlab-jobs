#!/usr/bin/env python3
"""
Show GitLab pipeline job durations.
"""

import argparse
import csv
import json
import subprocess
from collections import defaultdict
from statistics import mean, median, stdev
from typing import Iterable, Optional
from urllib.parse import urlparse

import colorama
import gitlab


__version__ = '1.2.1'


def get_project_name_from_git_url() -> Optional[str]:
    try:
        url = subprocess.check_output(['git', 'remote', 'get-url', 'origin'],
                                      stderr=subprocess.DEVNULL,
                                      universal_newlines=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    if '://' not in url:
        return None
    if urlparse(url).hostname in ('', 'github.com'):
        return None
    name = '/'.join(url.rsplit('/', 2)[-2:]).rstrip()
    if name.endswith('.git'):
        name = name[:-len('.git')]
    print("Determined the GitLab project to be {name}".format(name=name))
    return name


def get_pipelines(
    project: 'gitlab.v4.objects.Project',
    args: argparse.Namespace,
) -> Iterable['gitlab.v4.objects.ProjectPipeline']:
    filter_args = {
        'ref': args.branch
    }
    if not args.all_pipelines:
        filter_args['scope'] = 'finished'
        filter_args['status'] = 'success'

    max_per_page = 100
    pages = (args.limit + max_per_page - 1) // max_per_page
    for page in range(1, pages + 1):
        per_page = max_per_page
        last_page_leftover = args.limit % max_per_page
        if page == pages and last_page_leftover != 0:
            per_page = last_page_leftover

        for pipeline in project.pipelines.list(page=page, per_page=per_page,
                                               **filter_args):
            yield pipeline


def get_jobs(pipeline, args):
    filter_args = {}
    if not args.all_pipelines:
        filter_args['scope'] = 'success'
    return pipeline.jobs.list(all=True, **filter_args)


def fmt_status(status: str) -> str:
    colors = {
        'success': colorama.Fore.GREEN,
        'failed': colorama.Fore.RED,
        'running': colorama.Fore.YELLOW,
        'pending': colorama.Fore.MAGENTA,
        'created': colorama.Fore.CYAN,
        'manual': colorama.Fore.BLUE,
        'canceled': colorama.Fore.MAGENTA,
    }
    if status not in colors:
        return status
    return colors[status] + status + colorama.Style.RESET_ALL


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
    '-v', '--verbose', action='store_true',
    help='print more information',
)
parser.add_argument(
    '-g', '--gitlab',
    help='select configuration section in ~/.python-gitlab.cfg',
)
parser.add_argument(
    '-p', '--project', metavar='ID',
    help='select GitLab project ("group/project" or the numeric ID)',
)
parser.add_argument(
    '-b', '--branch', '--ref', metavar='REF', default='master',
    help='select git branch',
)
parser.add_argument(
    '--all-branches', action='store_const', const=None, dest='branch',
    help='do not filter by git branch',
)
parser.add_argument(
    '--all-pipelines', action='store_true',
    help='include pipelines that were not successful',
)
parser.add_argument(
    '-l', '--limit', metavar='N', default=20, type=int,
    help='limit analysis to last N pipelines',
)
parser.add_argument(
    '--csv', metavar='FILENAME',
    help='export raw data to CSV file',
)
parser.add_argument(
    '--debug', action='store_true',
    help='print even more information, for debugging',
)


def main():
    colorama.init()

    args = parser.parse_args()

    if not args.project:
        args.project = get_project_name_from_git_url()

    if not args.project:
        parser.error('please specify gitlab project ID, e.g. -p mygroup/hello')

    gl = gitlab.Gitlab.from_config(args.gitlab)
    project = gl.projects.get(args.project)

    pipeline_durations = []
    job_durations = defaultdict(list)

    pipelines = 'pipelines' if args.all_pipelines else 'successful pipelines'
    if args.branch is None:
        template = "Last {n} {pipelines} of {project}:"
    else:
        template = "Last {n} {pipelines} of {project} {ref}:"
    print(template.format(
        n=args.limit, pipelines=pipelines, ref=args.branch,
        project=project.name))
    pipelines = get_pipelines(project, args)
    for pipeline in pipelines:
        template = "  {id} ({date}, commit {sha_short}"
        if args.verbose:
            template += " by {user[name]}"
        if args.branch is None:
            template += " on {ref}"
        # pipeline data returned in the list contains only a small subset
        # of information, so we need an extra HTTP GET to fetch duration
        # and user
        pipeline = project.pipelines.get(pipeline.id)
        attrs = dict(pipeline.attributes)
        if pipeline.duration is not None:
            template += ", duration {duration_min:.1f}m)"
            pipeline_durations.append(pipeline.duration)
            attrs['duration_min'] = pipeline.duration / 60.0
        else:
            template += ")"
        if pipeline.status != 'success':
            template += ' - {color_status}'
        attrs['sha_short'] = attrs['sha'][:8]
        attrs['date'] = attrs['created_at'][:len('YYYY-MM-DD')]
        attrs['color_status'] = fmt_status(pipeline.status)
        print(template.format_map(attrs))
        if args.debug:
            print("   ", json.dumps(pipeline.attributes))
        for job in get_jobs(pipeline, args):
            if job.duration is not None:
                job_durations[job.name].append(job.duration)
            if args.verbose and job.duration is not None:
                template = "    {name:30}  {duration_min:4.1f}m"
                if job.status != 'success':
                    template += ' - {color_status}'
                print(template.format(
                    duration_min=job.duration / 60.0,
                    color_status=fmt_status(job.status),
                    **job.attributes))
                if args.debug:
                    print("     ", json.dumps(job.attributes))

    if not pipeline_durations:
        print("\nNo finished pipelines found.")
        return

    print("\nSummary:")
    to_show = sorted(job_durations.items()) + [('overall', pipeline_durations)]
    maxlen = max(len(name) for name, durations in to_show)
    digits = 4.1
    unit = "m", 60.0
    for job_name, durations in to_show:
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
        with open(args.csv, 'w', newline='') as f:
            writer = csv.writer(f)
            for job_name, durations in sorted(job_durations.items()):
                writer.writerow([job_name] + durations)
            writer.writerow(['overall'] + pipeline_durations)


if __name__ == '__main__':
    main()
