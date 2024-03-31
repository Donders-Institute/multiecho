# Multi-echo combinations

[![PyPI version](https://badge.fury.io/py/multiecho.svg)](https://badge.fury.io/py/multiecho)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/multiecho.svg)

MRI data acquisitions can involve multiple volumes acquired at different echo times. Typically, subsequent processing pipelines assume data to be acquired at a single echo time. This repository provides a command line tool to combine multiple echoes from a multi-echo (BOLD f)MRI acquisition.
It currently provides three different echo avering algorithms:

| algorithm  | description                                                                                 |
|:-----------|:--------------------------------------------------------------------------------------------|
| 1. average | Echoes are weighted equally                                                                 |
| 2. PAID    | Echoes are weighted by their CNR, i.e. by their TE*tSNR contributions (BOLD fMRI data only) |
| 3. TE      | Echoes are weighted by their TEs                                                            |

For more information on multiecho acquisition and combination schemes, please refer to (for example):

- [Poser et al. (2006)](https://onlinelibrary.wiley.com/doi/full/10.1002/mrm.20900). *BOLD Contrast Sensitivity Enhancement and Artifact Reduction with Multiecho EPI: Parallel-Acquired Inhomogeneity- Desensitized fMRI.* Magn. Reson. Med. 55:6, pp. 1227–35.
- [Posse, Stefan (2012)](https://doi.org/10.1016/j.neuroimage.2011.10.057). *Multi-Echo Acquisition*. NeuroImage 62:2, pp. 665–671.

> `Multiecho` has been developed at the [Donders Institute](https://www.ru.nl/donders/) of the [Radboud University](https://www.ru.nl/english/).

## Installation

To install, simply run:

    pip install multiecho
 
This will give you the latest stable release of the software. To get the very latest (possibly unreleased) version of the software you can install the package directly from the Github source code repository:

    pip install git+https://github.com/Donders-Institute/multiecho

Alternatively, clone this repository and run the following on the root folder of the repository:

    pip install .

The tool supports Python 3.6+.

## Usage

Once installed, a command line tool called `mecombine` should be available in your PATH. Detailed usage information can be found by running `mecombine -h`:

    usage: mecombine [-h] [-o OUTPUTNAME] [-a {PAID,TE,average}]
                          [-w [WEIGHTS [WEIGHTS ...]]] [-s] [-v VOLUMES]
                          pattern
    
    Combine multi-echo echoes.
    
    Tools to combine multiple echoes from an fMRI acquisition.
    It expects input files saved as NIfTIs, preferably organised
    according to the BIDS standard.
    
    Currently three different combination algorithms are supported, implementing
    the following weighting schemes:
    
    1. PAID => TE * SNR
    2. TE => TE
    3. Simple Average => 1
    
    positional arguments:
      pattern               Globlike search pattern with path to select the echo
                            images that need to be combined. Because of the
                            search, be sure to check that not too many files are
                            being read
    
    optional arguments:
      -h, --help            show this help message and exit
      -o OUTPUTNAME, --outputname OUTPUTNAME
                            File output name. If not a fullpath name, then the
                            output will be stored in the same folder as the input.
                            If empty, the output filename will be the filename of
                            the first echo appended with a '_combined' suffix
                            (default: )
      -a {PAID,TE,average}, --algorithm {PAID,TE,average}
                            Combination algorithm. Default: TE (default: TE)
      -w [WEIGHTS [WEIGHTS ...]], --weights [WEIGHTS [WEIGHTS ...]]
                            Weights (e.g. = echo times) for all echoes (default:
                            None)
      -s, --saveweights     If passed and algorithm is PAID, save weights
                            (default: False)
      -v VOLUMES, --volumes VOLUMES
                            Number of volumes that is used to compute the weights
                            if algorithm is PAID (default: 100)
    
    examples:
      mecombine '/project/number/bids/sub-001/func/*_task-motor_*echo-*.nii.gz'
      mecombine '/project/number/bids/sub-001/func/*_task-rest_*echo-*.nii.gz' -a PAID
      mecombine '/project/number/bids/sub-001/func/*_acq-MBME_*run-01*.nii.gz' -w 11 22 33 -o sub-001_task-stroop_acq-mecombined_run-01_bold.nii.gz

## Caveats

Currently, the echo combination is resource hungry as we load all datasets into memory at once. We could iterate through the volumes and only keep the final combined series in memory at any given time.

You may receive a runtime warning (`invalid value encountered in true_divide`) when combining echoes with `PAID`. If your datasets have voxels with zeros, e.g., if they were masked, a division by 0 will lead to infinite weights. You may safely ignore the warning, but do check your data after the combination.

By default, PAID will compute the weights based on the last 100 volumes of the acquisition. Whether this is optimal or not is up to discussion. If you are testing out the combination on a small subset of volumes, say 5 or so, then the weights won't be stable and your image may look noisy.
