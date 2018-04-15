from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

with open(path.join(here, 'VERSION.txt')) as version_file:
    version = version_file.read().strip()

NAME = 'pracnbastats'
DESCRIPTION = 'Scrape stats.nba.com.'
URL = 'https://github.com/practicallypredictable/pracnbastats'
EMAIL = 'practicallypredictable@practicallypredictable.com'
AUTHOR = 'Practically Predictable'
LICENSE = 'MIT'  # Change trove classifier below if using a different license

REQUIRED = [
    'numpy',
    'pandas',
    'tqdm',
]

setup(
    name=NAME,
    version=version,
    description=DESCRIPTION,
    long_description=long_description,
    author=AUTHOR,
    author_email=EMAIL,
    url=URL,
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    install_requires=REQUIRED,
    include_package_data=True,
    license=LICENSE,
    keywords='statistics sports analytics basketball NBA scrape',
    classifiers=[
        # Trove classifiers
        # Full list: https://pypi.python.org/pypi?%3Aaction=list_classifiers
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy'
    ],
)
