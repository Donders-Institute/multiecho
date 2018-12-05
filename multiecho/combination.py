#!/usr/bin/env python3
"""Combine multi-echo echoes.
Currently inneficient as we load all datasets into memory. We could iterate
through the volumes and only keep the final combined series in memory at any
given time, but that's for later.

Example usage:

echoes =
load_me_data('/project/datasets/sub-01/ses-01/func/*mbme*.nii.gz')
paid_data = me_combine(echoes, algorithm='paid')

TODO: Where could things go wrong and what measures have to be implemented to
avoid them? 1. Template not correctly specified may fail to load all data or
load more data than necessary. Sprinkle assertions that the number of echoes
combined match the input number of echoes given by the user.
"""
import argparse
import glob
import json
import os.path as op
from typing import List, Optional, Tuple, Union

import nibabel as nib
import numpy as np


def load_me_data(template: str,
                 echotimes: Optional[Tuple[float]]) -> List[Tuple[np.array,
                                                                  float]]:
    """Given a globlike template, load all echoes and their TEs.
    Return a list of tuples like:
    [(echo1, TE1), (echo2, TE2), ..., (echoN, TEN)]
    Here, echoN is a numpy array of loaded data.
    """
    datafiles = list(sorted(glob.glob(template)))
    print(f'Loading: {datafiles}')
    if echotimes is not None:
        st = op.splitext
        json_template = [st(st(x)[0])[0] + '.json' for x in datafiles]
        echotimes = [json.load(open(f, 'r'))['EchoTime']
                     for f in json_template]

    print(f'Echotimes: {echotimes}')
    return [(nib.load(x).get_data(), y) for x, y in zip(datafiles, echotimes)]


def paid_weights(echoes: List[np.array], n_vols: int = 100) -> np.array:
    """Compute PAID weights from echoes described as a list of tuples,
    as loaded by load_me_data.

    w(tCNR) = TE * tSNR
    """
    def weight(echo: np.array, te: float, n_vols: int = 100):
        mean = echo[..., :n_vols].mean(axis=-1)
        std = echo[..., :n_vols].std(axis=-1)
        return te * mean / std
    return np.stack([weight(echo, te, n_vols) for echo, te in echoes], axis=-1)


def combine(echoes: List[np.array],
            weights: Optional[Union[List[np.array], List[float]]]):
    """General echo combination function using np.average.
    Echoes is the list of tuples loaded by load_me_data, and weights is
    either of the same as the echo datasets stacked, or a 1D vector.

    See me_combine for example usage.
    """
    data: np.array = np.stack([x[0] for x in echoes], axis=-1)
    return np.average(data, axis=-1, weights=weights)


def me_combine(template: str, algorithm: str = 'average'):
    """General me_combine routine.
    TODO: (Eventually, if ever) Make this more general by accepting functions
    in place of strings for 'algorithm'.

    Currently supported algorithms:
    - average
    - paid
    - te
    """
    echoes: List[Tuple[np.array, float]] = load_me_data(template)

    affine = echoes[0][0].affine
    header = echoes[0][0].header

    if algorithm == 'average':
        weights = None
    elif algorithm == 'paid':
        weights = paid_weights(echoes)
        weights = np.tile(weights, (1, 1, 1, echoes[0][0].shape[3], 1))
    elif algorithm == 'te':
        weights = [te for data, te in echoes]

    return nib.Nifti1Image(combine(echoes, weights), affine, header)


def main():

    parser: argparse.ArgumentParser = _cli_parser()
    args: argparse.Namespace = parser.parse_args()

    combined: nib.Nifti1Image = me_combine(args.inputs, args.echotimes)
    combined.to_filename(args.outputname)


def _cli_parser():

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inputs', type=str,
                        help='Globlike pattern with path to echoes')
    parser.add_argument('--echotimes', nargs='*', default=None,
                        help='Echo Times for all echoes.')
    parser.add_argument('--outputname', type=str,
                        help='Optional file output name.')

    return parser


if __name__ == '__main__':
    main()
