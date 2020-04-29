import subprocess
import sys
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


def test_main(set_git_remote_url):
    set_git_remote_url('https://gitlab.com/mgedmin/example-project')
    glj.main()
