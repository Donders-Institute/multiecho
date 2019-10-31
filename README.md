# Multi-echo Combinations

This repository provides a command line tool to combine multiple echoes from a multi-echo BOLD fMRI acquisition.
It currently provides three different echo avering algorithms:

|algorithm  | description |
|:--------- |:----------- |
|1. average | Echoes are weighted equally
|2. PAID    | Echoes are weighted by their CNR, i.e. by their TE*tSNR contributions
|3. TE      | Echoes are weighted by their TEs

For more information on multiecho acquisition and combination schemes, please refer to (for example):

- [Poser et al. (2006)](https://onlinelibrary.wiley.com/doi/full/10.1002/mrm.20900). *BOLD Contrast Sensitivity Enhancement and Artifact Reduction with Multiecho EPI: Parallel-Acquired Inhomogeneity- Desensitized fMRI.* Magn. Reson. Med. 55:6, pp. 1227–35.
- [Posse, Stefan (2012)](https://doi.org/10.1016/j.neuroimage.2011.10.057). *Multi-Echo Acquisition*. NeuroImage 62:2, pp. 665–671.

## Installation

To install, simply run:

    pip install multiecho
 
This will give you the latest stable release of the software. To get the very latest version of the software you can install the package directly from the github source code repository:

    pip install git+https://github.com/Donders-Institute/multiecho

Alternatively, to get the latest (possibly unreleased) code, clone this repository and run the following on the root folder of the repository:

    pip install .

The tool only supports Python 3.6+.

## Usage

Once installed, a command line tool called mecombine will be available in your PATH. Detailed usage information can be found by running:

    mecombine --help

In short, `mecombine` is being designed to work with the Brain Imaging Data Structure (BIDS). Recommended usage is:

    mecombine '/project/number/experiment-datasets/sub-01/func/*task-A_*echo-*.nii.gz' --outputname 'echoes_combined' --saveweights

Which, if your folder is BIDS compliant, should work out of the box. Because `mecombine` accepts a *glob-like* pattern, be sure to check that not too many files are being read.

## Caveats

Currently inneficient as we load all datasets into memory. We could iterate through the volumes and only keep the final combined series in memory at any given time.

You may receive a runtime warning when combining echoes with `PAID`. If your datasets have voxels with zeros, e.g., if they were masked, a division by 0 will lead to infinite weights. You may safely ignore the warning, but do check your data after the combination.

By default PAID will compute the weights based on the last 100 volumes of the acquisition. Whether this is optimal or not is up to discussion. If you are testing out the combination on a small subset of volumes, say 5 or so, then the weights won't be stable and your image may look noisy.
