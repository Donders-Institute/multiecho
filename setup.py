from io import open

from setuptools import find_packages, setup

with open('multiecho/__init__.py', 'r') as f:
    for line in f:
        if line.startswith('__version__'):
            version = line.strip().split('=')[1].strip(' \'"')
            break
    else:
        version = '0.1'

with open('README.org', 'r', encoding='utf-8') as f:
    readme = f.read()

REQUIRES = ['nibabel', 'numpy']

setup(name              = 'multiecho',
      version           = version,
      description       = 'Combine multi-echoes from a multi-echo fMRI acquisition.',
      long_description  = readme,
      author            = 'Marcel Zwiers',
      author_email      = 'm.zwiers@donders.ru.nl',
      maintainer        = 'Marcel Zwiers',
      maintainer_email  = 'm.zwiers@donders.ru.nl',
      url               = 'https://github.com/Donders-Institute/multiecho',
      license           = 'MIT/Apache-2.0',
      keywords          = ['fmri', 'multi-echo'],
      classifiers       = ['Intended Audience :: Developers',
                           'License :: OSI Approved :: MIT License',
                           'License :: OSI Approved :: Apache Software License',
                           'Natural Language :: English',
                           'Operating System :: OS Independent',
                           'Programming Language :: Python :: 3.6',
                           'Programming Language :: Python :: 3.7',
                           'Programming Language :: Python :: Implementation :: CPython'],
      entry_points      = {'console_scripts': ['mecombine = multiecho.combination:main']},
      install_requires  = REQUIRES,
      tests_require     = ['coverage', 'pytest'],
      packages          = find_packages())
