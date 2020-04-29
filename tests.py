import hashlib
import subprocess
import sys
import textwrap
from unittest.mock import Mock, MagicMock, call

import gitlab
import pytest

import gitlab_jobs as glj


@pytest.fixture(autouse=True)
def mock_gitlab(monkeypatch):
    gl = MagicMock()
    monkeypatch.setattr(gitlab, 'Gitlab', gl)
    return gl


@pytest.fixture(autouse=True)
def gitlab_project(mock_gitlab):
    project = mock_gitlab.from_config.return_value.projects.get.return_value
    project.id = 42
    project.name = 'example-project'
    return project


@pytest.fixture
def set_pipelines(gitlab_project):
    def set_pipelines(pipelines):
        gitlab_project.pipelines.list.return_value = pipelines
        gitlab_project.pipelines.get = {
            pipeline.id: pipeline for pipeline in pipelines
        }.get

    return set_pipelines


def Pipeline(
    id,
    sha=None,
    ref="master",
    status="success",
    created_at="2020-04-29T08:31:32.384Z",
    updated_at="2020-04-29T08:32:14.375Z",
    web_url="https://gitlab.com/mgedmin/example-project/pipelines/{}",
    before_sha=None,
    tag=None,
    yaml_errors=None,
    user_id=56,
    user_name="Marius Gedminas",
    user_username="mgedmin",
    user_state="active",
    user_avatar_url="https://example.com/avatar.png",
    user_web_url="https://gitlab.com/mgedmin",
    started_at="2020-04-29T08:31:36.070Z",
    finished_at="2020-04-29T08:32:14.360Z",
    committed_at=None,
    duration=38,  # seconds
    coverage=None,
    detailed_status_icon="status_success",
    detailed_status_text="passed",
    detailed_status_label="passed",
    detailed_status_group="success",
    detailed_status_tooltip="passed",
    detailed_status_has_details=True,
    detailed_status_details_path="/mgedmin/example-project/pipelines/{}",
    detailed_status_illustration=None,
    detailed_status_favicon="https://example.com/success.png",
    project_id=42,
):
    if sha is None:
        sha = hashlib.sha1(str(id).encode()).hexdigest()
    if before_sha is None:
        before_sha = hashlib.sha1(str(id - 1).encode()).hexdigest()
    attributes = dict(
        id=id,
        sha=sha,
        ref=ref,
        status=status,
        created_at=created_at,
        updated_at=updated_at,
        web_url=web_url.format(id),
        before_sha=before_sha,
        tag=tag,
        yaml_errors=yaml_errors,
        user=dict(
            id=user_id,
            name=user_name,
            username=user_username,
            state=user_state,
            avatar_url=user_avatar_url,
            web_url=user_web_url,
        ),
        started_at=started_at,
        finished_at=finished_at,
        committed_at=committed_at,
        duration=duration,
        coverage=coverage,
        detailed_status=dict(
            icon=detailed_status_icon,
            text=detailed_status_text,
            label=detailed_status_label,
            group=detailed_status_group,
            tooltip=detailed_status_tooltip,
            has_details=detailed_status_has_details,
            details_path=detailed_status_details_path.format(id),
            illustration=detailed_status_illustration,
            favicon=detailed_status_favicon,
        ),
        project_id=project_id,
    )
    pipeline = Mock(attributes=attributes, **attributes)
    pipeline.jobs.list.return_value = []
    return pipeline


@pytest.fixture(autouse=True)
def set_argv(monkeypatch):
    def set_argv(argv):
        monkeypatch.setattr(sys, 'argv', argv)

    set_argv(['gitlab-jobs'])
    return set_argv


@pytest.fixture(autouse=True)
def set_git_remote_url(request, monkeypatch):
    def set_git_remote_url(url='', error=None):
        monkeypatch.setattr(
            subprocess, 'check_output',
            Mock(return_value=url + '\n', side_effect=error))

    marker = request.node.get_closest_marker('allow_subprocess')
    if not marker:
        set_git_remote_url('')

    return set_git_remote_url


@pytest.mark.allow_subprocess
def test_get_project_name_from_git_url():
    # One test where we don't stub subprocess.check_output()
    assert glj.get_project_name_from_git_url() is None


def test_get_project_name_from_git_url__git_not_installed(set_git_remote_url):
    set_git_remote_url(error=FileNotFoundError)
    assert glj.get_project_name_from_git_url() is None


def test_get_project_name_from_git_url__git_error(set_git_remote_url):
    # Could be this is not a git repo, could be there's no remote called
    # 'origin'.
    set_git_remote_url(error=subprocess.CalledProcessError(1, 'git'))
    assert glj.get_project_name_from_git_url() is None


def test_get_project_name_from_git_url__github(set_git_remote_url):
    set_git_remote_url('https://github.com/mgedmin/gitlab-jobs')
    assert glj.get_project_name_from_git_url() is None


@pytest.mark.parametrize('url', [
    'https://gitlab.com/mygroup/myproject',
    'https://git.example.com/mygroup/myproject',
    'ssh://git@git.example.com:23/mygroup/myproject.git',
])
def test_get_project_name_from_git_url__gitlab(set_git_remote_url, url):
    set_git_remote_url(url)
    assert glj.get_project_name_from_git_url() == 'mygroup/myproject'


def test_get_pipelines():
    project = MagicMock()
    project.pipelines.list.return_value = pipelines = [Mock('pipeline')]
    args = glj.parser.parse_args([])
    assert len(list(glj.get_pipelines(project, args))) == len(pipelines)
    assert project.pipelines.list.call_args_list == [
        call(page=1, per_page=20, ref='master', scope='finished',
             status='success'),
    ]


def test_get_pipelines_many_pages():
    project = MagicMock()
    args = glj.parser.parse_args(['--limit', '234', '--all-pipelines'])
    list(glj.get_pipelines(project, args))
    assert project.pipelines.list.call_args_list == [
        call(page=1, per_page=100, ref='master'),
        call(page=2, per_page=100, ref='master'),
        call(page=3, per_page=34, ref='master'),
    ]


def test_get_pipelines_many_pages_no_leftover():
    project = MagicMock()
    args = glj.parser.parse_args(['--limit', '200', '--all-pipelines'])
    list(glj.get_pipelines(project, args))
    assert project.pipelines.list.call_args_list == [
        call(page=1, per_page=100, ref='master'),
        call(page=2, per_page=100, ref='master'),
    ]


def test_get_pipelines_many_pages_different_branch():
    project = MagicMock()
    args = glj.parser.parse_args(['--branch', 'foo', '--all-pipelines'])
    list(glj.get_pipelines(project, args))
    assert project.pipelines.list.call_args_list == [
        call(page=1, per_page=20, ref='foo'),
    ]


def test_get_jobs():
    pipeline = MagicMock()
    args = glj.parser.parse_args([])
    list(glj.get_jobs(pipeline, args))
    assert pipeline.jobs.list.call_args_list == [
        call(all=True, scope='success')
    ]


def test_main__help(set_argv):
    set_argv(['gitlab-jobs', '--help'])
    with pytest.raises(SystemExit):
        glj.main()


def test_main_no_project():
    with pytest.raises(SystemExit):
        glj.main()


def test_main_no_pipelines(set_git_remote_url, capsys):
    set_git_remote_url('https://gitlab.com/mgedmin/example-project')
    glj.main()
    assert capsys.readouterr().out == textwrap.dedent('''\
        Determined the GitLab project to be mgedmin/example-project
        Last 20 successful pipelines of example-project master:

        No finished pipelines found.
    ''')


def test_main_some_pipelines(set_pipelines, set_git_remote_url, capsys):
    set_git_remote_url('https://gitlab.com/mgedmin/example-project')
    set_pipelines([
        Pipeline(id=2, duration=None),
        Pipeline(id=1),
    ])
    glj.main()
    assert capsys.readouterr().out == textwrap.dedent('''\
        Determined the GitLab project to be mgedmin/example-project
        Last 20 successful pipelines of example-project master:
          2 (commit da4b9237bacccdf19c0760cab7aec4a8359010b0)
          1 (commit 356a192b7913b04c54574d18c28d46e6395428ab, duration 0.6m)

        Summary:
          overall  min  0.6m, max  0.6m, avg  0.6m, median  0.6m, stdev  0.0m
    ''')


def test_main_some_pipelines_all_branches(
    set_argv, set_pipelines, set_git_remote_url, capsys
):
    set_argv(['gitlab-jobs', '--all-branches'])
    set_git_remote_url('https://gitlab.com/mgedmin/example-project')
    set_pipelines([
        Pipeline(id=1, duration=None),
    ])
    glj.main()
    assert capsys.readouterr().out == textwrap.dedent('''\
        Determined the GitLab project to be mgedmin/example-project
        Last 20 successful pipelines of example-project:
          1 (commit 356a192b7913b04c54574d18c28d46e6395428ab on master)

        No finished pipelines found.
    ''')


def test_main_some_pipelines_verbose(
    set_argv, set_pipelines, set_git_remote_url, capsys
):
    set_argv(['gitlab-jobs', '-v'])
    set_git_remote_url('https://gitlab.com/mgedmin/example-project')
    set_pipelines([
        Pipeline(id=1, duration=None),
    ])
    glj.main()
    assert capsys.readouterr().out == textwrap.dedent('''\
        Determined the GitLab project to be mgedmin/example-project
        Last 20 successful pipelines of example-project master:
          1 (commit 356a192b7913b04c54574d18c28d46e6395428ab by Marius Gedminas)

        No finished pipelines found.
    ''')
