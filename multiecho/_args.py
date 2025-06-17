"""Argument parsing for the mecombine tool"""

import argparse
import textwrap

doc = """Combine multi-echo echoes.

Tools to combine multiple echoes from an fMRI acquisition.
It expects input files saved as NIfTIs, preferably organised
according to the BIDS standard.

Currently three different combination algorithms are supported, implementing
the following weighting schemes:

1. PAID => TE * SNR
2. TE => TE
3. Simple Average => 1
"""

class CustomFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter):
        pass

def make_parser():
    parser = argparse.ArgumentParser(prog='mecombine',
                                     formatter_class=CustomFormatter,
                                     description=textwrap.dedent(doc),
                                     epilog="examples:\n"
                                            "  mecombine 'bids/sub-001/func/*_task-motor_*echo-*.nii.gz'\n"
                                            "  mecombine 'bids/sub-001/func/*_task-rest_*echo-*.nii.gz' -a PAID\n"
                                            "  mecombine 'bids/sub-001/func/*_acq-MBME_*run-01*.nii.gz' -w 11 22 33 -o sub-001_task-stroop_acq-mecombined_run-01_bold.nii.gz\n ")

    parser.add_argument('pattern', type=str, help='Globlike search pattern with path to select the echo images that need to be combined. Because of the search, be sure to check that not too many files are being read')
    parser.add_argument('-o','--outputname', type=str, default='', help="File output name. If not a fullpath name, then the output will be stored in the same folder as the input. If empty, the output filename will be the filename of the first echo appended with a '_combined' suffix")
    parser.add_argument('-a','--algorithm', default='TE', choices=['PAID', 'TE', 'average'], help='Combination algorithm. Default: TE')
    parser.add_argument('-w','--weights', nargs='*', default=None, type=float, help='Weights (e.g. = echo times) for all echoes')
    parser.add_argument('-s','--saveweights', action='store_true', help='If passed and algorithm is PAID, save weights')
    parser.add_argument('-v','--volumes', type=int, default=100, help='Number of volumes that is used to compute the weights if algorithm is PAID')

    return parser
