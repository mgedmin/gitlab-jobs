import gitlab_jobs as gl


def test_get_project_name_from_git_url():
    assert gl.get_project_name_from_git_url() is None
