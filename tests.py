import subprocess
from unittest.mock import Mock

import pytest

import gitlab_jobs as gl


def test_get_project_name_from_git_url():
    # One test where we don't stub subprocess.check_output()
    assert gl.get_project_name_from_git_url() is None


def test_get_project_name_from_git_url__git_not_installed(monkeypatch):
    monkeypatch.setattr(subprocess, 'check_output',
                        Mock(side_effect=FileNotFoundError))
    assert gl.get_project_name_from_git_url() is None


def test_get_project_name_from_git_url__git_error(monkeypatch):
    # Could be this is not a git repo, could be there's no remote called
    # 'origin'.
    monkeypatch.setattr(
        subprocess, 'check_output',
        Mock(side_effect=subprocess.CalledProcessError(1, 'git')))
    assert gl.get_project_name_from_git_url() is None


def test_get_project_name_from_git_url__github_is_not_gitlab(monkeypatch):
    monkeypatch.setattr(
        subprocess, 'check_output',
        Mock(return_value='https://github.com/mgedmin/gitlab-jobs\n'))
    assert gl.get_project_name_from_git_url() is None


@pytest.mark.parametrize('url', [
    'https://gitlab.com/mygroup/myproject',
    'https://git.example.com/mygroup/myproject',
    'ssh://git@git.example.com:23/mygroup/myproject.git',
])
def test_get_project_name_from_git_url__gitlab(monkeypatch, url):
    monkeypatch.setattr(
        subprocess, 'check_output',
        Mock(return_value=url + '\n'))
    assert gl.get_project_name_from_git_url() == 'mygroup/myproject'
