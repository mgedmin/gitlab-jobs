#!/usr/bin/env python
import ast
import os
import re

from setuptools import setup


here = os.path.dirname(__file__)
with open(os.path.join(here, 'README.rst')) as f:
    long_description = f.read()

metadata = {}
with open(os.path.join(here, 'gitlab_jobs.py')) as f:
    rx = re.compile('(__version__|__author__|__url__|__licence__) = (.*)')
    for line in f:
        m = rx.match(line)
        if m:
            metadata[m.group(1)] = ast.literal_eval(m.group(2))
version = metadata['__version__']

setup(
    name='gitlab-jobs',
    version=version,
    author='Marius Gedminas',
    author_email='marius@gedmin.as',
    url='https://github.com/mgedmin/gitlab-jobs',
    description='history of GitLab CI job running times',
    long_description=long_description,
    keywords='',
    classifiers=[
        "Development Status :: 4 - Beta",
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
    ],
    license='GPL',
    python_requires=">=3.5",

    py_modules=['gitlab_jobs'],
    zip_safe=False,
    install_requires=['python-gitlab'],
    entry_points={
        'console_scripts': [
            'gitlab-jobs = gitlab_jobs:main',
        ],
    },
)
