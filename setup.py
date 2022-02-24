from pathlib import Path
from setuptools import find_packages, setup

# Read the version from file
with (Path(__file__).parent/'bidscoin'/'version.txt').open('r') as fid:
    version = fid.read().strip()

# Read the contents of the README file
with (Path(__file__).parent/'README.rst').open('r') as fid:
    readme = fid.read()

# Read the contents of the requirements file
with (Path(__file__).parent/'requirements.txt').open('r') as fid:
    requirements = fid.read().splitlines()

setup(name                          = 'multiecho',          # Required
      version                       = version,              # Required
      packages                      = find_packages(),      # Required
      install_requires              = requirements,
      tests_require                 = ['coverage', 'pytest'],
      entry_points                  = {'console_scripts': ['mecombine = multiecho.combination:main']},
      description                   = 'Combine multi-echoes from a multi-echo fMRI acquisition.',
      long_description              = readme,
      long_description_content_type = 'text/markdown',
      author                        = 'Daniel Gomez',
      author_email                  = 'd.gomez@donders.ru.nl',
      maintainer                    = 'Marcel Zwiers',
      maintainer_email              = 'm.zwiers@donders.ru.nl',
      url                           = 'https://github.com/Donders-Institute/multiecho',
      license                       = 'MIT/Apache-2.0',
      keywords                      = ['fmri', 'multi-echo', 'bids'],
      classifiers                   = ['Intended Audience :: Developers',
                                       'License :: OSI Approved :: MIT License',
                                       'License :: OSI Approved :: Apache Software License',
                                       'Natural Language :: English',
                                       'Operating System :: OS Independent',
                                       'Programming Language :: Python :: 3.6',
                                       'Programming Language :: Python :: 3.7',
                                       'Programming Language :: Python :: 3.8',
                                       'Programming Language :: Python :: 3.9',
                                       'Programming Language :: Python :: Implementation :: CPython'])
