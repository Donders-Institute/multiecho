#!/usr/bin/env python3
"""Combine multi-echo echoes.

Tools to combine multiple echoes from an fMRI acquisition.
It expects input files saved as NIfTIs, preferably organised
according to the BIDS.

Currently three different combination algorithms are supported, implementing
the following weighting schemes:

1. PAID => TE * SNR
2. TE => TE
3. Simple Average => 1
"""
import argparse
import glob
import json
import os.path as op
from typing import List, Optional, Tuple, Union

import nibabel as nib
import numpy as np


def load_me_data(template: str,
                 tes: Optional[Tuple[float]]) -> List[Tuple[nib.Nifti1Image,
                                                            float]]:
    """Given a globlike template, load all echoes and their TEs.
    Return a list of tuples like:
    [(echo1, TE1), (echo2, TE2), ..., (echoN, TEN)]
    Here, echoN is a numpy array of loaded data.
    """
    datafiles = list(sorted(glob.glob(template)))
    print(f'Loading: {datafiles}')
    if tes is None:
        st = op.splitext
        json_template = [st(st(x)[0])[0] + '.json' for x in datafiles]
        tes = [json.load(open(f, 'r'))['EchoTime']
               for f in json_template]

    print(f'Echotimes: {tes}')
    return [(nib.load(x), y) for x, y in zip(datafiles, tes)]


def paid_weights(echoes: List[nib.Nifti1Image],
                 n_vols: int = 100) -> np.array:
    """Compute PAID weights from echoes described as a list of tuples,
    as loaded by load_me_data.

    w(tCNR) = TE * tSNR
    """
    def weight(echo: nib.Nifti1Image, te: float, n_vols: int = 100):
        data = echo.get_data()
        mean = data[..., -n_vols:].mean(axis=-1)
        std = data[..., -n_vols:].std(axis=-1)
        return te * mean / std

    weights = [weight(echo, te, n_vols) for echo, te in echoes]
    return np.stack(weights, axis=-1)


def combine(echoes: List[nib.Nifti1Image],
            weights: Optional[Union[List[np.array], List[float]]]):
    """General echo combination function using np.average.
    Echoes is the list of tuples loaded by load_me_data, and weights is
    either of the same as the echo datasets stacked, or a 1D vector.

    See me_combine for example usage.
    """
    data: np.array = np.stack([x[0].get_data() for x in echoes], axis=-1)
    # np.average will normalise the weights. No need to do that manually.
    return np.average(data, axis=-1, weights=weights)


def me_combine(template: str,
               echotimes: Optional[List[float]] = None,
               algorithm: str = 'average'):
    """General me_combine routine.
    TODO: (Eventually, if ever) Make this more general by accepting functions
    in place of strings for 'algorithm'.

    Currently supported algorithms:
    - average
    - paid
    - te
    """
    echoes: List[Tuple[np.array, float]] = load_me_data(template, echotimes)

    affine = echoes[0][0].affine
    header = echoes[0][0].header

    if algorithm == 'average':
        weights = None
    elif algorithm == 'paid':
        weights = paid_weights(echoes)
        # Make the weights have the appropriate number of volumes.
        weights = np.tile(weights[:, :, :, np.newaxis, :],
                          (1, 1, 1, echoes[0][0].shape[3], 1))
    elif algorithm == 'te':
        weights = [te for data, te in echoes]

    return nib.Nifti1Image(np.nan_to_num(combine(echoes, weights)),
                           affine, header)


def main():

    parser: argparse.ArgumentParser = _cli_parser()
    args: argparse.Namespace = parser.parse_args()

    combined: nib.Nifti1Image = me_combine(args.inputs, args.echotimes,
                                           algorithm=args.algorithm)
    combined.to_filename(args.outputname)


def _cli_parser():

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inputs', type=str,
                        help='Globlike pattern with path to echoes')
    parser.add_argument('--echotimes', nargs='*', default=None, type=float,
                        help='Echo Times for all echoes.')
    parser.add_argument('--outputname', type=str,
                        help='File output name.')
    parser.add_argument('--algorithm', default='paid',
                        choices=['paid', 'te', 'average'],
                        help='Combination algorithm. Default: paid')

    return parser


if __name__ == '__main__':
    main()
