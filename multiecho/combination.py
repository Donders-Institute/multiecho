#!/usr/bin/env python3
import json
import logging
import shutil
from rich.logging import RichHandler
from pathlib import Path
from typing import List, Optional, Tuple, Union
import nibabel as nib
import numpy as np

LOGGER = logging.getLogger(__name__)


def load_me_data(pattern: Path, TEs: Optional[Tuple[float]]) -> Tuple[List[Tuple[nib.Nifti1Image, float]], list]:
    """
    Load all echoes and their TEs.
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

    return [(nib.load(datafile), TEs[n]) for n, datafile in enumerate(datafiles)], list(datafiles)


def paid_weights(echoes: List[Tuple[nib.Nifti1Image, float]], n_vols: int) -> np.array:
    """
    Compute PAID weights from echoes described as a list of tuples, as loaded by load_me_data.

    w(tCNR) = TE * tSNR
    """
    def weight(echo: nib.Nifti1Image, TE: float):
        data = echo.get_fdata(caching='unchanged')
        mean = data[..., -n_vols:].mean(axis=-1)
        std  = data[..., -n_vols:].std(axis=-1)
        return TE * mean / std

    n_vols  = min(n_vols, echoes[0][0].shape[3])
    weights = [weight(echo, TE) for echo, TE in echoes]

    return np.stack(weights, axis=-1)


def me_combine(pattern: Union[str,Path], outputname: Union[str,Path]='', algorithm: str='TE', weights: Optional[List[float]]=None,
               saveweights: bool=True, volumes: int=100) -> int:
    """
    General me_combine routine.
    Truncates incomplete acquisitions (e.g. when the scanner was stopped manually)

    Currently supported algorithms:
    - average
    - PAID
    - TE

    Returns an errorcode: 0 = ok, 1 = inconsistent acquisition, 2 = no multi-echo images found
    """

    outputname = Path(outputname)

    # Set the logging level and format & add a rich console handler
    if not LOGGER.hasHandlers():
        LOGGER.setLevel(logging.INFO)
        LOGGER.addHandler(RichHandler(show_time=False, show_level=True, show_path=False, rich_tracebacks=True, markup=True, level='INFO'))

    # Load the data
    me_data, datafiles = load_me_data(Path(pattern), weights)
    if not datafiles:
        LOGGER.warning(f"No multi-echo images found in: {pattern}")
        return 2

    # Parse the filenames
    datafile = datafiles[0]
    datastem = datafile.with_suffix('').stem
    dataext  = ''.join(datafile.suffixes)
    if not outputname.name:
        outputname = (datafile.parent/(datastem + '_combined')).with_suffix(dataext)
    if not outputname.parent.name:
        outputname = datafile.parent/outputname

    # Truncate incomplete acquisitions (e.g. when the scanner was stopped manually)
    if me_data[0][0].ndim > 3:
        dim4 = [echo.shape[3] for echo, TE in me_data]
        if len(set(dim4)) > 1:
            LOGGER.warning(f"Not all echos were acquired, found: {dim4} volumes")
            if sum(np.diff(dim4)==-1) == 1 and sum(np.diff(dim4)==0) == len(dim4)-2:      # i.e. Only 1 step of size -1 in dim4
                dim4 = [min(dim4)] * len(dim4)
                LOGGER.warning(f"Truncating echos to: {dim4} volumes")
            else:
                LOGGER.error(f"Inconsistent echo images, skipping {pattern} -> {outputname}")
                return 1
        echos = np.stack([echo.get_fdata(caching='unchanged')[:, :, :, 0:dim4[0]] for echo, TE in me_data], axis=-1)

    else:
        echos = np.stack([echo.get_fdata(caching='unchanged') for echo, TE in me_data], axis=-1)

    # Compute the weights
    if algorithm == 'average':
        weights = None
    elif algorithm == 'PAID':
        if me_data[0][0].ndim < 4:
            LOGGER.error(f"PAID requires 4D data, {datafile} has size: {me_data[0][0].shape}\nSkipping: {pattern} -> {outputname}")
            return 1
        weights = paid_weights(me_data, volumes)
        # Make the weights have the appropriate number of volumes.
        weights = np.tile(weights[:, :, :, np.newaxis, :], (1, 1, 1, echos.shape[3], 1))
    elif algorithm == 'TE':
        weights = [TE for echo, TE in me_data]
    else:
        LOGGER.error(f'Unknown algorithm: {algorithm}')

    # Combine the images
    combined = np.average(echos, axis=-1, weights=weights)      # np.average normalizes the weights. No need to do that manually.
    affine   = me_data[0][0].affine
    header   = me_data[0][0].header
    combined = nib.Nifti1Image(np.nan_to_num(combined), affine, header)
    LOGGER.info(f'Saving combined image to: {outputname}')
    if outputname.is_file():
        LOGGER.warning(f'{outputname} already exists, overwriting its content')
    combined.to_filename(outputname)

    # Add a combined-echo json sidecar-file
    outputjson = outputname.with_suffix('').with_suffix('.json')
    datajsons  = [datafile.with_suffix('').with_suffix('.json') for datafile in datafiles]
    if datajsons[0].is_file():
        LOGGER.info(f"Adding a json sidecar-file: {datajsons[0]} -> {outputjson}")
        shutil.copyfile(datajsons[0], outputjson)
        with outputjson.open('r') as json_fid:
            data = json.load(json_fid)
        data['EchoNumber'] = 1
        if algorithm == 'PAID':
            data['EchoTime'] = np.average([TE for echo, TE in me_data], weights=np.nanmean(weights[...,0,:], axis=(0,1,2)))  # This seems to be the best we can do (the BIDS validator indicates there has to be a nr here, an empty value generates a warning)
        else:
            data['EchoTime'] = np.average([TE for echo, TE in me_data], weights=weights)  # This seems to be the best we can do (the BIDS validator indicates there has to be a nr here, an empty value generates a warning)
        with outputjson.open('w') as json_fid:
            json.dump(data, json_fid, indent=4)

    # Save the weights
    if saveweights and algorithm == 'PAID':
        fname         = (datafile.parent/(datastem + '_combined_weights')).with_suffix(dataext)
        nifti_weights = nib.Nifti1Image(weights[...,0,:], combined.affine, combined.header)
        LOGGER.info(f'Saving PAID weights to: {fname}')
        if fname.is_file():
            LOGGER.warning(f'{fname} already exists, overwriting its content')
        nifti_weights.to_filename(fname)

    return 0


def main():
    """Console script usage"""

    from . import _args

    args = _args.make_parser().parse_args()

    me_combine(pattern=args.pattern, outputname=args.outputname, algorithm=args.algorithm, weights=args.weights, saveweights=args.saveweights, volumes=args.volumes)


if __name__ == '__main__':
    main()
