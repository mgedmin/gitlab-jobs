import subprocess
from typing import Optional, Iterable
from unittest.mock import Mock, MagicMock, call

import pytest

import gitlab_jobs as glj


def test_get_project_name_from_git_url():
    # One test where we don't stub subprocess.check_output()
    assert glj.get_project_name_from_git_url() is None


def test_get_project_name_from_git_url__git_not_installed(monkeypatch):
    monkeypatch.setattr(subprocess, 'check_output',
                        Mock(side_effect=FileNotFoundError))
    assert glj.get_project_name_from_git_url() is None


def test_get_project_name_from_git_url__git_error(monkeypatch):
    # Could be this is not a git repo, could be there's no remote called
    # 'origin'.
    monkeypatch.setattr(
        subprocess, 'check_output',
        Mock(side_effect=subprocess.CalledProcessError(1, 'git')))
    assert glj.get_project_name_from_git_url() is None


def test_get_project_name_from_git_url__github_is_not_gitlab(monkeypatch):
    monkeypatch.setattr(
        subprocess, 'check_output',
        Mock(return_value='https://github.com/mgedmin/gitlab-jobs\n'))
    assert glj.get_project_name_from_git_url() is None


@pytest.mark.parametrize('url', [
    'https://gitlab.com/mygroup/myproject',
    'https://git.example.com/mygroup/myproject',
    'ssh://git@git.example.com:23/mygroup/myproject.git',
])
def test_get_project_name_from_git_url__gitlab(monkeypatch, url):
    monkeypatch.setattr(
        subprocess, 'check_output',
        Mock(return_value=url + '\n'))
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
