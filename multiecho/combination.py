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
import json
import logging
import coloredlogs
from pathlib import Path
from typing import List, Optional, Tuple

import nibabel as nib
import numpy as np


def load_me_data(pattern: Path, TEs: Optional[Tuple[float]]) -> Tuple[List[Tuple[nib.Nifti1Image, float]], list]:
    """Load all echoes and their TEs.
    Return a list of tuples like:
    [(echo1, TE1), (echo2, TE2), ..., (echoN, TEN)]
    Here, echoN is a numpy array of loaded data.
    """

    datafiles = sorted(pattern.parent.glob(pattern.name))

    if not TEs:
        jsonfiles = [datafile.with_suffix('').with_suffix('.json') for datafile in datafiles]
        TEs       = [json.load(jsonfile.open('r'))['EchoTime']     for jsonfile in jsonfiles]

    # Sort by TE
    s         = np.argsort(TEs)
    TEs       = np.array(TEs)[s]
    datafiles = np.array(datafiles)[s]

    LOGGER.info(f'Multi-Echo times: {TEs}')
    LOGGER.info(f'Loading ME-files: {[str(datafile) for datafile in datafiles]}')

    return [(nib.load(str(datafile)), TEs[n]) for n, datafile in enumerate(datafiles)], datafiles


def paid_weights(echoes: List[Tuple[nib.Nifti1Image, float]], n_vols: int) -> np.array:
    """Compute PAID weights from echoes described as a list of tuples,
    as loaded by load_me_data.

    w(tCNR) = TE * tSNR
    """
    def weight(echo: nib.Nifti1Image, TE: float):
        data = echo.get_data()
        mean = data[..., -n_vols:].mean(axis=-1)
        std  = data[..., -n_vols:].std(axis=-1)
        return TE * mean / std

    n_vols  = min(n_vols, echoes[0][0].shape[3])
    weights = [weight(echo, TE) for echo, TE in echoes]

    return np.stack(weights, axis=-1)


def me_combine(pattern: str,
               outputname: str = '',
               algorithm: str = 'TE',
               weights: Optional[List[float]] = None,
               saveweights: bool = True,
               volumes: int = 100,
               logger: str = __name__) -> int:
    """General me_combine routine.
    Truncates incomplete acquisitions (e.g. when the scanner was stopped manually)
    Returns an errorcode: 0 = ok, 1 = inconsistent acquisition

    Currently supported algorithms:
    - average
    - PAID
    - TE
    """

    global LOGGER
    LOGGER = logging.getLogger(logger)

    outputname = Path(outputname)

    # Set the logging level and format & add the streamhandler
    if not LOGGER.hasHandlers():
        LOGGER.setLevel(logging.INFO)
        fmt     = '%(asctime)s - %(name)s - %(levelname)s %(message)s'
        datefmt = '%Y-%m-%d %H:%M:%S'
        coloredlogs.install(level=LOGGER.level, fmt=fmt, datefmt=datefmt)

    # Load the data
    me_data, datafiles = load_me_data(Path(pattern), weights)

    # Parse the filenames
    datafile = datafiles[0]
    datastem = datafile.with_suffix('').stem
    dataext  = ''.join(datafile.suffixes)
    if not outputname.name:
        outputname = (datafile.parent/(datastem + '_combined')).with_suffix(dataext)
    if not outputname.parent.name:
        outputname = datafile.parent/outputname

    # Compute the weights
    if algorithm == 'average':
        weights = None
    elif algorithm == 'PAID':
        if me_data[0][0].ndim < 4:
            LOGGER.error(f"PAID requires 4D data, {datafile} has size: {me_data[0][0].shape()}")
        weights = paid_weights(me_data, volumes)
        # Make the weights have the appropriate number of volumes.
        weights = np.tile(weights[:, :, :, np.newaxis, :],
                          (1, 1, 1, me_data[0][0].shape[3], 1))
    elif algorithm == 'TE':
        weights = [TE for echo, TE in me_data]
    else:
        LOGGER.error(f'Unknown algorithm: {algorithm}')

    # Truncate incomplete acquisitions (e.g. when the scanner was stopped manually)
    if me_data[0][0].ndim > 3:
        dim4 = [echo.shape[3] for echo, TE in me_data]
        if len(set(dim4)) > 1:
            LOGGER.warning(f"Not all echos were acquired: {dim4}")
            if sum(np.diff(dim4)==-1) == 1 and sum(np.diff(dim4)==0) == len(dim4)-2:      # i.e. Only 1 step of size -1 in dim4
                dim4 = [min(dim4)] * len(dim4)
                LOGGER.warning(f"Truncating echos to: {dim4}")
            else:
                LOGGER.error(f"Inconsistent echo images, skipping {pattern} -> {outputname}")
                return 1
        echos = np.stack([echo.get_data()[:, :, :, 0:dim4[0]] for echo, TE in me_data], axis=-1)

    else:
        echos = np.stack([echo.get_data() for echo, TE in me_data], axis=-1)

    # Combine the images
    combined = np.average(echos, axis=-1, weights=weights)      # np.average normalizes the weights. No need to do that manually.
    affine   = me_data[0][0].affine
    header   = me_data[0][0].header
    combined = nib.Nifti1Image(np.nan_to_num(combined), affine, header)
    LOGGER.info(f'Saving combined image to: {outputname}')
    if outputname.is_file():
        LOGGER.warning(f'{outputname} already exists, overwriting its content')
    combined.to_filename(str(outputname))

    # Save the weights
    if saveweights and algorithm == 'PAID':
        fname         = (datafile.parent/(datastem + '_combined_weights')).with_suffix(dataext)
        nifti_weights = nib.Nifti1Image(np.squeeze(weights[..., 0, :]),
                                        combined.affine,
                                        combined.header)
        LOGGER.info(f'Saving PAID weights to: {fname}')
        if fname.is_file():
            LOGGER.warning(f'{fname} already exists, overwriting its content')
        nifti_weights.to_filename(str(fname))

    return 0


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
    parser.add_argument('-o','--outputname', type=str, default='',
                        help="File output name. If not a fullpath name, then the output will be stored in the same folder as the input. If empty, the output filename will be the filename of the first echo appended with a '_combined' suffix")
    parser.add_argument('-a','--algorithm', default='TE', choices=['PAID', 'TE', 'average'],
                        help='Combination algorithm. Default: TE')
    parser.add_argument('-w','--weights', nargs='*', default=None, type=float,
                        help='Weights (e.g. = echo times) for all echoes')
    parser.add_argument('-s','--saveweights', action='store_true',
                        help='If passed and algorithm is PAID, save weights')
    parser.add_argument('-v','--volumes', type=int, default=100,
                        help='Number of volumes that is used to compute the weights if algorithm is PAID')

    args = parser.parse_args()

    me_combine(pattern=args.pattern, outputname=args.outputname, algorithm=args.algorithm, weights=args.weights, saveweights=args.saveweights, volumes=args.volumes)


if __name__ == '__main__':
    main()
