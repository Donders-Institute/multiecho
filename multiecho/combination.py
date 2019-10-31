#!/usr/bin/env python3
"""Combine multi-echo echoes.

Tools to combine multiple echoes from an fMRI acquisition.
It expects input files saved as NIfTIs, preferably organised
according to the BIDS standard.

Currently three different combination algorithms are supported, implementing
the following weighting schemes:

1. PAID => TE * SNR
2. TE => TE
3. Simple Average => 1
"""

import argparse
import textwrap
import glob
import json
import logging
import coloredlogs
import os.path as op
from typing import List, Optional, Tuple

import nibabel as nib
import numpy as np

LOGGER = logging.getLogger()


def load_me_data(datafiles: list, TEs: Optional[Tuple[float]]) -> List[Tuple[nib.Nifti1Image, float]]:
    """Load all echoes and their TEs.
    Return a list of tuples like:
    [(echo1, TE1), (echo2, TE2), ..., (echoN, TEN)]
    Here, echoN is a numpy array of loaded data.
    """

    if TEs is None:
        json_template = [op.splitext(op.splitext(datafile)[0])[0] + '.json' for datafile in datafiles]
        TEs = [json.load(open(f, 'r'))['EchoTime'] for f in json_template]

    LOGGER.info(f'Multi-Echo times: {TEs}')
    LOGGER.info(f'Loading ME-files: {datafiles}')

    return [(nib.load(datafile), TE) for datafile, TE in zip(datafiles, TEs)]


def paid_weights(echoes: List[nib.Nifti1Image], n_vols: int) -> np.array:
    """Compute PAID weights from echoes described as a list of tuples,
    as loaded by load_me_data.

    w(tCNR) = TE * tSNR
    """
    def weight(echo: nib.Nifti1Image, TE: float, n_vols: int):
        data = echo.get_data()
        mean = data[..., -n_vols:].mean(axis=-1)
        std  = data[..., -n_vols:].std(axis=-1)
        return TE * mean / std

    n_vols  = min(n_vols, echoes[0][0].shape[3])
    weights = [weight(echo, TE, n_vols) for echo, TE in echoes]

    return np.stack(weights, axis=-1)


def me_combine(pattern: str,
               outputname: str = '',
               algorithm: str = 'TE',
               weights: Optional[List[float]] = None,
               saveweights: bool = True,
               volumes: int = 100):
    """General me_combine routine.

    Currently supported algorithms:
    - average
    - PAID
    - TE
    """

    st = op.splitext

    # Set the logging level and format & add the streamhandler
    if not LOGGER.hasHandlers():
        LOGGER.setLevel(logging.INFO)
        fmt     = '%(asctime)s - %(name)s - %(levelname)s %(message)s'
        datefmt = '%Y-%m-%d %H:%M:%S'
        coloredlogs.install(level='DEBUG', fmt=fmt, datefmt=datefmt)

    # Parse the filenames
    datafiles      = sorted(glob.glob(pattern))
    datafile, ext2 = st(datafiles[0])
    datafile, ext1 = st(datafile)
    if not outputname:
        outputname = datafile + '_combined' + ext1 + ext2
    if outputname == op.basename(outputname):
        outputname = op.join(op.dirname(datafile), outputname)

    # Load the data
    me_data = load_me_data(datafiles, weights)

    # Compute the weights
    if algorithm == 'average':
        weights = None
    elif algorithm == 'PAID':
        weights = paid_weights(me_data, volumes)
        # Make the weights have the appropriate number of volumes.
        weights = np.tile(weights[:, :, :, np.newaxis, :],
                          (1, 1, 1, me_data[0][0].shape[3], 1))
    elif algorithm == 'TE':
        weights = [TE for echo, TE in me_data]
    else:
        LOGGER.error(f'Unknown algorithm: {algorithm}')

    # Combine the images
    echos    = np.stack([echo.get_data() for echo, TE in me_data], axis=-1)
    combined = np.average(echos, axis=-1, weights=weights)      # np.average normalizes the weights. No need to do that manually.
    affine   = me_data[0][0].affine
    header   = me_data[0][0].header
    combined = nib.Nifti1Image(np.nan_to_num(combined), affine, header)
    LOGGER.info(f'Saving combined image to: {outputname}')
    combined.to_filename(outputname)

    # Save the weights
    if saveweights and algorithm == 'PAID':
        fname = st(st(outputname)[0])[0] + '_weights' + ext1 + ext2
        nifti_weights = nib.Nifti1Image(np.squeeze(weights[..., 0, :]),
                                        combined.affine,
                                        combined.header)
        LOGGER.info(f'Saving PAID weights to: {fname}')
        nifti_weights.to_filename(fname)


def main():
    """Console script usage"""

    class CustomFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter):
        pass

    parser = argparse.ArgumentParser(formatter_class=CustomFormatter,
                                     description=textwrap.dedent(__doc__),
                                     epilog="examples:\n"
                                            "  mecombine '/project/number/bids/sub-001/func/*_task-motor_*echo-*.nii.gz'\n"
                                            "  mecombine '/project/number/bids/sub-001/func/*_task-rest_*echo-*.nii.gz' -a PAID\n"
                                            "  mecombine '/project/number/bids/sub-001/func/*_acq-MBME_*run-01*.nii.gz' -w 11 22 33 -o sub-001_task-stroop_acq-mecombined_run-01_bold.nii.gz\n ")
    parser.add_argument('pattern', type=str,
                        help='Globlike search pattern with path to select the echo images that need to be combined. Because of the search, be sure to check that not too many files are being read')
    parser.add_argument('-o','--outputname', type=str,
                        help="File output name. If not a fullpath name, then the output will be stored in the same folder as the input. If empty, the output filename will be the filename of the first echo appended with a '_combined' suffix")
    parser.add_argument('-w','--weights', nargs='*', default=None, type=float,
                        help='Weights (e.g. = echo times) for all echoes')
    parser.add_argument('-a','--algorithm', default='TE',
                        choices=['PAID', 'TE', 'average'],
                        help='Combination algorithm. Default: TE')
    parser.add_argument('-s','--saveweights', action='store_true',
                        help='If passed and algorithm is PAID, save weights')
    parser.add_argument('-v','--volumes', type=int, default=100,
                        help='Number of volumes that is used to compute the weights if algorithm is PAID')

    args = parser.parse_args()

    me_combine(pattern=args.pattern, outputname=args.outputname, algorithm=args.algorithm, weights=args.weights, saveweights=args.saveweights, volumes=args.volumes)


if __name__ == '__main__':
    main()
