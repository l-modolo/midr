#!/usr/bin/python3

"""Compute the Irreproducible Discovery Rate (IDR) from NarrowPeaks files

This section of the project provides facilitites to handle NarrowPeaks files
and compute IDR on the choosen value in the NarrowPeaks columns
"""

from os import path, access, R_OK, W_OK, makedirs
from pathlib import PurePath
from typing import List, Any
from typing import Callable
import numpy as np
import pandas as pd


def narrowpeaks_cols() -> list:
    """
    Return list of narrowpeak column names
    :return: a list of string
    """
    return ['chr', 'start', 'stop', 'name', 'score', 'strand',
            'signalValue', 'pValue', 'qValue', 'peak']


def narrowpeaks_score() -> str:
    """
    Return the score column of narrowpeak files
    :return:
    """
    return 'signalValue'


def narrowpeaks_sort_cols() -> list:
    """
    Return a list of column to sort and merge peaks on
    :return: a list of string
    """
    return ['chr', 'start', 'stop', 'strand', 'peak']


def readbed(bed_path: PurePath,
            bed_cols: list = None) -> pd.DataFrame:
    """
    Read a bed file from a PurePath object
    :type bed_cols: list of str
    :param bed_path: PurePath of the bedfile
    :param bed_cols: list of columns names
    :return: a pd.DataFrame corresponding to the bed file
    """
    assert path.isfile(str(bed_path)), "File {str(bed_path)} doesn't exist"
    assert access(str(bed_path), R_OK), "File {str(bed_path)} isn't readable"

    def move_peak(x):
       x['peak'] += x['start']
       return x
    return pd.read_csv(
        bed_path,
        sep='\t',
        header=None,
        names=bed_cols
    ).apply(
        func=move_peak,
        axis=1
    )


def sort_bed(bed_file: pd.DataFrame,
             sort_cols: list) -> pd.DataFrame:
    """
    Sort bed files according to sort_cols columns
    :param bed_file: bed file loaded as a pd.DataFrame
    :param sort_cols: list of columns to sort the pd.DataFrame on
    :return: None the array is sorted as is
    >>> sort_bed(bed_file=pd.DataFrame({
    ... 'chr': ['b','b', 'a', 'a', 'a', 'a'],
    ... 'start': [100000, 20, 10, 100, 1000, 5],
    ... 'stop': [100100, 40, 15, 150, 2000, 8],
    ... 'strand': ['.', '.', '.', '.', '.', '.'],
    ... 'peak': [100050, 30, 12, 125, 1500, 6]
    ... }),
    ... sort_cols = narrowpeaks_sort_cols()
    ... )
      chr   start    stop strand    peak
    5   a       5       8      .       6
    2   a      10      15      .      12
    3   a     100     150      .     125
    4   a    1000    2000      .    1500
    1   b      20      40      .      30
    0   b  100000  100100      .  100050
    """
    return bed_file.sort_values(by=sort_cols)


def readbeds(bed_paths: list,
             bed_cols: list,
             sort_cols: list) -> list:
    """
    Read a list of bed files from a PurePath list
    :type bed_paths: list of PurePath objects
    :param bed_paths: list of PurePath
    :param bed_cols: list of bedfiles columns
    :param sort_cols: list of columns to sort the pd.DataFrame on
    :return: list of pd.DataFrame
    """
    bed_files = list()
    for bed_path in bed_paths:
        bed_files.append(
            sort_bed(
                bed_file=readbed(
                    bed_path=bed_path,
                    bed_cols=bed_cols),
                sort_cols=sort_cols
            )
        )
    return bed_files


def readfiles(file_names: list,
              size: int = 100,
              merge_function=sum,
              file_cols: list = None,
              score_cols: str = None,
              pos_cols: list = None) -> list:
    """
    Reads a list of bed filenames and return a list of pd.DataFrame
    :rtype: list[pd.DataFrame]
    :param file_names: list of bed files to read
    :param size: int expand peaks of size size
    :param merge_function: function to apply to the score column when
    removing duplicates
    :param file_cols: list of bed file columns
    :param score_cols: column name of the score to use
    :param pos_cols: list of position column name to sort and merge on
    :return: list[pd.DataFrame] containing the file csv columns
    """
    bed_paths = list()
    for file_name in file_names:
        bed_paths.append(PurePath(file_name))
    return merge_beds(
        bed_files=readbeds(
            bed_paths=bed_paths,
            bed_cols=file_cols,
            sort_cols=pos_cols,
        ),
        size=size,
        merge_function=merge_function,
        score_col=score_cols,
        pos_cols=pos_cols,
        file_cols=file_cols
    )


def writefiles(bed_files: list,
               file_names: list,
               idr: np.array,
               outdir: str = "results/"):
    """
    Write output of IDR computation
    :param bed_files: list of bed files (pd.DataFrame)
    :param file_names: list of files names (str)
    :param idr: np.array with local IDR score (columns correspond to bed files)
    :param outdir: output directory
    :return: nothing
    """
    for bed, file_name in zip(bed_files, file_names[1:]):
        output_name = PurePath(outdir).joinpath(
            "idr_" + PurePath(str(file_name)).name
        )
        bed.assign(idr=idr).to_csv(
            output_name, sep='\t',
            encoding='utf-8',
            header=False,
            index=False
        )


def pos_overlap(pos_ref: pd.Series, pos: pd.Series) -> bool:
    """
    Return True if two bed position overlap with each other
    :param pos_ref bed line in the reference bed file,
    :param pos bed line in the considered bed file
    :return: bool, True if pos overlap and false otherwise

    >>> pos_overlap(pos_ref = pd.Series({'chr': 'a', 'start': 100, 'stop': 120,
    ... 'strand': "."}),
    ... pos = pd.Series({'chr': 'a', 'start': 100, 'stop': 120, 'strand': "."}))
    True
    >>> pos_overlap(
    ... pos_ref = pd.Series({'chr': 'a', 'start': 100, 'stop':
    ... 120, 'strand': "."}),
    ... pos = pd.Series({'chr': 'a', 'start': 110, 'stop': 130, 'strand': "."}))
    True
    >>> pos_overlap(pos_ref = pd.Series({'chr': 'a', 'start': 100, 'stop':
    ... 120, 'strand': "."}),
    ... pos = pd.Series({'chr': 'b', 'start': 100, 'stop': 120, 'strand': "."}))
    False
    >>> pos_overlap(pos_ref = pd.Series({'chr': 'a', 'start': 100, 'stop':
    ... 120, 'strand': "."}),
    ... pos = pd.Series({'chr': 'b', 'start': 130, 'stop': 150, 'strand': "."}))
    False
    >>> pos_overlap(pos_ref = pd.Series({'chr': 'a', 'start': 130, 'stop':
    ... 150, 'strand': "."}),
    ... pos = pd.Series({'chr': 'b', 'start': 100, 'stop': 120, 'strand': "."}))
    False
    """
    for pos_col in ['chr', 'strand']:
        assert isinstance(pos_ref[pos_col], str), \
            "pos_overlapp: {pos_col} = {pos_ref[pos_col]} isn't a str"
        assert isinstance(pos[pos_col], str), \
            "pos_overlapp: {pos_col} = {pos[pos_col]} isn't a str"
        if pos_ref[pos_col] != pos[pos_col]:
            return False
    # pos before pos_ref
    if pos_ref['start'] > pos['stop']:
        return False
    # pos after pos_ref
    if pos_ref['stop'] < pos['start']:
        return False
    return True


def best_peak(ref_peak: pd.Series, peaks: pd.DataFrame,
              start_pos: int = 0,
              score_col: str = None) -> int:
    """
    Return the index of the closest peak to peak_ref in peaks in case of
    equality return the one with the highest score
    :param ref_peak: the reference peak (line of a narrowpeak file)
    :param peaks: a list of peaks (lines of a narrowpeak file)
    :param start_pos: int starting position of peaks
    :param score_col: str name of the score column
    :return: int index of the closest peak in peaks

    >>> best_peak(ref_peak=pd.Series({'peak': 100, 'signalValue': 20}),
    ... peaks=pd.DataFrame({'peak': [90, 110, 105],
    ... 'signalValue': [5, 10, 20]}),
    ... score_col=narrowpeaks_score())
    2
    >>> best_peak(ref_peak=pd.Series({'peak': 100, 'signalValue': 20}),
    ... peaks=pd.DataFrame({'peak': [90, 105, 105],
    ... 'signalValue': [5, 20, 10]}),
    ... score_col=narrowpeaks_score())
    1
    >>> test_peak = pd.DataFrame({'peak': [90, 105, 105, 90, 105, 105],
    ... 'signalValue': [5, 20, 10, 5, 20, 10]})
    >>> best_peak(ref_peak=pd.Series({'peak': 100, 'signalValue': 20}),
    ... peaks=test_peak.iloc[3:6, :],
    ... score_col=narrowpeaks_score())
    1
    """
    if peaks.shape[0] == 1:
        return start_pos
    peaks = peaks.reset_index()
    pos = abs(peaks.peak - ref_peak.peak).idxmin()
    if peaks.peak.where(peaks.iloc[pos].peak == peaks.peak).size == 1:
        return pos + start_pos
    else:
        return peaks[score_col] \
                   .where(
            peaks.iloc[pos].peak == peaks.peak).idxmax() + start_pos


def merge_peak(ref_peak: pd.Series, peak: pd.Series,
               pos_cols: list = None) -> pd.Series:
    """
    Return merged peaks between position of ref_peak and everythings else
    from peak
    :param ref_peak: line of ref_peaks narrowpeak
    :param peak: line of peak narrowpeak
    :param pos_cols: list list of columns name for position information
    :return: line of narrowpeak

    >>> merge_peak(
    ... ref_peak=pd.Series({'chr': 'a', 'start': 100, 'stop': 120,
    ... 'strand': ".", 'peak': 100, 'score': 20}),
    ... peak=pd.Series({'chr': 'a', 'start': 200, 'stop': 220,
    ... 'strand': ".", 'peak': 140, 'score': 45}),
    ... pos_cols=narrowpeaks_sort_cols()
    ... )
    chr         a
    start     100
    stop      120
    strand      .
    peak      100
    score      45
    dtype: object
    """
    merged_peak = peak.copy()
    for pos_col in pos_cols:
        merged_peak[pos_col] = ref_peak[pos_col]
    return merged_peak


def collapse_peaks(peaks: pd.DataFrame,
                   merge_function=sum,
                   score_col: str = None,
                   file_cols: list = None) -> pd.DataFrame:
    """
    Copy peaks values from peaks into the corresponding position in merged_peaks
    Peaks not found in peaks have a score of nan
    :param file_cols:
    :param peaks: pd.DataFrame of the peaks we want to merge
    :param merge_function: function to apply to the score column when
    removing duplicates
    :param score_col: str with the name of the score column
    :return: pd.DataFrame of the merged peaks

    >>> collapse_peaks(
    ... peaks=pd.DataFrame({
    ... 'chr': ['a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a'],
    ... 'start': [100, 100, 1000, 4000, 4000, 4000, 100000, 200000, 200000,
    ... 200000],
    ... 'stop': [500, 500, 3000, 10000, 10000, 10000, 110000, 230000, 230000,
    ... 230000],
    ... 'strand': [".", ".", ".", ".", ".", ".", ".", ".", ".", "."],
    ... 'peak': [250, 200, 2000, 5000, 6000, 7000, 100000, 205000, 215000,
    ... 220000],
    ... 'signalValue': [20, 15, 100, 15, 30, 14, 30, 200, 300, 400]}),
    ... score_col=narrowpeaks_score(),
    ... file_cols=narrowpeaks_cols()
    ... )
      chr   start    stop strand           peak  signalValue
    0   a     100     500      .     225.000000           35
    1   a    1000    3000      .    2000.000000          100
    2   a    4000   10000      .    6000.000000           59
    3   a  100000  110000      .  100000.000000           30
    4   a  200000  230000      .  213333.333333          900
    """
    def first(x):
        """
        return first line of x
        :param x:
        :return:
        """
        return x.iloc[0:1]
    peaks_cols = peaks.columns.values.tolist()
    agg_dict = {'peak': np.mean, score_col: merge_function}
    for file_col in file_cols:
        if file_col in peaks_cols and file_col not in agg_dict.keys():
            agg_dict[file_col] = first
    peaks = peaks.groupby(
        ['chr', 'start', 'stop']
    ).agg(
        agg_dict
    ).reset_index(drop=True)
    peaks.columns = agg_dict.keys()
    return peaks[peaks_cols]


def expand_peaks(peaks: pd.DataFrame, size: int = 100) -> pd.DataFrame:
    """
    enlarge peaks of size
    :param peaks: pd.DataFrame
    :param size: int
    :return: pd.DataFrame
    >>> expand_peaks(
    ... peaks=pd.DataFrame({
    ... 'chr': ['a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a'],
    ... 'start': [100, 100, 1000, 4000, 4000, 4000, 100000, 200000, 200000,
    ... 200000],
    ... 'stop': [500, 500, 3000, 10000, 10000, 10000, 110000, 230000, 230000,
    ... 230000],
    ... 'strand': [".", ".", ".", ".", ".", ".", ".", ".", ".", "."],
    ... 'peak': [250, 200, 2000, 5000, 6000, 7000, 100000, 205000, 215000,
    ... 220000],
    ... 'signalValue': [20, 15, 100, 15, 30, 14, 30, 200, 300, 400]})
    ... )
      chr   start    stop strand    peak  signalValue
    0   a       0     600      .     250           20
    1   a       0     600      .     200           15
    2   a     900    3100      .    2000          100
    3   a    3900   10100      .    5000           15
    4   a    3900   10100      .    6000           30
    5   a    3900   10100      .    7000           14
    6   a   99900  110100      .  100000           30
    7   a  199900  230100      .  205000          200
    8   a  199900  230100      .  215000          300
    9   a  199900  230100      .  220000          400
    """
    def expand(x, add_size=size):
        """
        function to exand one peak
        :param x:
        :param add_size:
        :return:
        """
        x['start'] = max([x['start'] - size, 0])
        x['stop'] += add_size
        return x
    return peaks.apply(
        func=lambda x: expand(x),
        axis=1
    )


def merge_peaks(ref_peaks: pd.DataFrame,
                peaks: pd.DataFrame,
                size: int = 100,
                merge_function=sum,
                score_col: str = None,
                file_cols: list = None,
                pos_cols: list = None) -> pd.DataFrame:
    """
    Copy peaks values from peaks into the corresponding position in merged_peaks
    Peaks not found in peaks have a score of nan
    :param file_cols:
    :param ref_peaks: pd.DataFrame which is a copy of ref_peaks
    :param peaks: pd.DataFrame of the peaks we want to merge
    :param size: int expand peaks of size size
    :param merge_function: function to apply to the score column when
    removing duplicates
    :param score_col: str with the name of the score column
    :param pos_cols: list list of columns name for position information
    :return: pd.DataFrame of the merged peaks

    >>> merge_peaks(
    ... ref_peaks=pd.DataFrame({
    ... 'chr': ['a', 'a', 'a', 'a', 'a', 'a'],
    ... 'start': [50, 100, 1000, 4000, 100000, 200000],
    ... 'stop': [60, 500, 3000, 10000, 110000, 230000],
    ... 'strand': [".", ".", ".", ".", ".", "."],
    ... 'peak': [55, 250, 2000, 7000, 100000, 215000],
    ... 'signalValue': [10.0, 20.0, 100.0, 15.0, 30.0, 200.0]}),
    ... peaks=pd.DataFrame({
    ... 'chr': ['a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a'],
    ... 'start': [100, 100, 1000, 4000, 4000, 4000, 100000, 200000, 200000,
    ... 200000],
    ... 'stop': [500, 500, 3000, 10000, 10000, 10000, 110000, 230000, 230000,
    ... 230000],
    ... 'strand': [".", ".", ".", ".", ".", ".", ".", ".", ".", "."],
    ... 'peak': [250, 200, 2000, 5000, 6000, 7000, 100000, 205000, 215000,
    ... 220000],
    ... 'signalValue': [20.0, 15.0, 100.0, 15.0, 30.0, 14.0, 30.0, 200.0,
    ... 300.0, 400.0]}),
    ... score_col=narrowpeaks_score(),
    ... file_cols=narrowpeaks_cols(),
    ... pos_cols=narrowpeaks_sort_cols()
    ... )
      chr   start    stop strand    peak  signalValue
    0   a      50      60      .      55         15.0
    1   a     100     500      .     250         20.0
    2   a    1000    3000      .    2000        100.0
    3   a    4000   10000      .    7000         14.0
    4   a  100000  110000      .  100000         30.0
    5   a  200000  230000      .  215000        300.0
    >>> merge_peaks(
    ... ref_peaks=pd.DataFrame({
    ... 'chr': ['a', 'a', 'a', 'a', 'a', 'a', 'a'],
    ... 'start': [100, 100, 1000, 4000, 100000, 200000, 200000],
    ... 'stop': [500, 500, 3000, 10000, 110000, 230000, 230000],
    ... 'strand': [".", ".", ".", ".", ".", ".", "."],
    ... 'peak': [250, 270, 2000, 7000, 100000, 213000, 215000],
    ... 'signalValue': [20.0, 30.0, 100.0, 15.0, 30.0, 150.0, 200.0]}),
    ... peaks=pd.DataFrame({
    ... 'chr': ['a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a'],
    ... 'start': [100, 100, 1000, 4000, 4000, 4000, 100000, 200000, 200000,
    ... 200000],
    ... 'stop': [500, 500, 3000, 10000, 10000, 10000, 110000, 230000, 230000,
    ... 230000],
    ... 'strand': [".", ".", ".", ".", ".", ".", ".", ".", ".", "."],
    ... 'peak': [250, 280, 2000, 5000, 6000, 7000, 100000, 205000, 215000,
    ... 220000],
    ... 'signalValue': [20.0, 15.0, 100.0, 15.0, 30.0, 14.0, 30.0, 200.0,
    ... 300.0, 400.0]}),
    ... score_col=narrowpeaks_score(),
    ... file_cols=narrowpeaks_cols(),
    ... pos_cols=narrowpeaks_sort_cols()
    ... )
      chr   start    stop strand    peak  signalValue
    0   a     100     500      .     260         20.0
    1   a    1000    3000      .    2000        100.0
    2   a    4000   10000      .    7000         14.0
    3   a  100000  110000      .  100000         30.0
    4   a  200000  230000      .  214000        300.0
    """
    merged_peaks = collapse_peaks(
        peaks=ref_peaks.copy(),
        merge_function=merge_function,
        score_col=score_col,
        file_cols=file_cols
    )
    peaks = expand_peaks(
        peaks=peaks,
        size=size
    )
    merged_peaks[merged_peaks.columns.difference(pos_cols)] = np.NaN

    def min_dist(merged_peak, peaks_list, score_name):
        scores = peaks_list[
            (merged_peak['peak'] >= peaks_list['start']) &
            (merged_peak['peak'] <= peaks_list['stop']) &
            (merged_peak['chr'] == peaks_list['chr'])
        ].copy()
        if scores.empty:
            return np.NaN
        else:
            scores['dist'] = scores.apply(
                func=lambda x: abs(x['peak'] - merged_peak['peak']),
                axis=1
            )

            scores = scores.loc[scores['dist'].idxmin()]
            return scores[score_col]
    merged_peaks[score_col] = merged_peaks.apply(
        func=lambda x: min_dist(
            merged_peak=x,
            peaks_list=peaks,
            score_name=score_col
        ),
        axis=1
    )
    return merged_peaks


def merge_beds(bed_files: list,
               merge_function=sum,
               size=100,
               file_cols: list = None,
               score_col: str = None,
               pos_cols: list = None) -> list:
    """
    Merge a list of bed according to position in a reference in the list
    :param file_cols:
    :param bed_files: list of pd.DataFrame representing bed files
    :param ref_pos: position of the reference bed in the bed_files list
    :param merge_function: function to apply to the score column when
    removing duplicates
    :param size: int expand peaks of size size
    :param score_col: str with the name of the score column
    :param pos_cols: list list of columns name for position information
    :return: a list of bed files (pd.DataFrame)
    >>> merge_beds(
    ... bed_files=[
    ... pd.DataFrame({
    ... 'chr': ['a', 'a', 'a', 'a', 'a', 'a', 'a'],
    ... 'start': [100, 100, 1000, 4000, 100000, 200000, 200000],
    ... 'stop': [500, 500, 3000, 10000, 110000, 230000, 230000],
    ... 'strand': [".", ".", ".", ".", ".", ".", "."],
    ... 'peak': [250, 270, 2000, 7000, 100000, 213000, 215000],
    ... 'signalValue': [20.0, 30.0, 100.0, 15.0, 30.0, 150.0, 200.0]}),
    ... pd.DataFrame({
    ... 'chr': ['a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a'],
    ... 'start': [100, 100, 4000, 4000, 4000, 100000, 200000, 200000,
    ... 200000],
    ... 'stop': [500, 500, 10000, 10000, 10000, 110000, 230000, 230000,
    ... 230000],
    ... 'strand': [".", ".", ".", ".", ".", ".", ".", ".", "."],
    ... 'peak': [250, 280, 5000, 6000, 7000, 100000, 205000, 215000,
    ... 220000],
    ... 'signalValue': [20.0, 15.0, 15.0, 30.0, 14.0, 30.0, 200.0, 300.0,
    ... 400.0]}),
    ... pd.DataFrame({
    ... 'chr': ['a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a'],
    ... 'start': [100, 100, 1000, 4000, 4000, 4000, 100000, 200000, 200000,
    ... 200000],
    ... 'stop': [500, 500, 3000, 10000, 10000, 10000, 110000, 230000, 230000,
    ... 230000],
    ... 'strand': [".", ".", ".", ".", ".", ".", ".", ".", ".", "."],
    ... 'peak': [250, 280, 2000, 5000, 6000, 7000, 100000, 205000, 215000,
    ... 220000],
    ... 'signalValue': [21.0, 16.0, 101.0, 16.0, 31.0, 15.0, 31.0, 201.0,
    ... 301.0, 401.0]})
    ... ],
    ... score_col=narrowpeaks_score(),
    ... file_cols=narrowpeaks_cols(),
    ... pos_cols=narrowpeaks_sort_cols()
    ... )
    [  chr   start    stop strand    peak  signalValue
    0   a     100     500      .     260         20.0
    2   a    4000   10000      .    7000         14.0
    3   a  100000  110000      .  100000         30.0
    4   a  200000  230000      .  214000        300.0,   chr   start    stop \
strand    peak  signalValue
    0   a     100     500      .     260         21.0
    2   a    4000   10000      .    7000         15.0
    3   a  100000  110000      .  100000         31.0
    4   a  200000  230000      .  214000        301.0]
    """
    merged_files = []
    nan_pos = []
    for bed in bed_files[1:]:
        merged_files.append(
            merge_peaks(
                ref_peaks=bed_files[0],
                peaks=bed,
                merge_function=merge_function,
                size=size,
                file_cols=file_cols,
                score_col=score_col,
                pos_cols=pos_cols
            )
        )
        nan_pos += list(
            merged_files[-1].index[
                merged_files[-1][score_col].apply(np.isnan)
            ].to_numpy()
        )
    nan_pos = set(nan_pos)
    for merged in range(len(merged_files)):
        merged_files[merged] = merged_files[merged].drop(nan_pos)
    return merged_files


def narrowpeaks2array(np_list: list,
                      score_cols: str = None) -> np.array:
    """
    convert a list of pd.DataFrame representing bed files to an np.array of
    their score column
    :type np_list: list[pd.DataFrame]
    :type score_cols: str colname of the score column
    :param np_list: list of pd.DataFrame representing bed files
    :return np.array whose columns are the score columns of the bed files

    >>> narrowpeaks2array(np_list=[
    ... pd.DataFrame({'peak': [90, 105, 105], 'signalValue': [5, 20, 10]}),
    ... pd.DataFrame({'peak': [90, 105, 105], 'signalValue': [5, 21, 11]}),
    ... pd.DataFrame({'peak': [90, 105, 105], 'signalValue': [5, 22, 12]})],
    ... score_cols=narrowpeaks_score()
    ... )
    array([[ 5,  5,  5],
           [20, 21, 22],
           [10, 11, 12]])
    """
    scores = list()
    for np_file in np_list:
        scores.append(np.array(np_file[score_cols].to_numpy()))
    scores = np.stack(scores, axis=-1)
    return scores


def process_bed(file_names: list,
                outdir: str,
                idr_func: Callable[[np.array], np.array],
                size: int = 100,
                merge_function=sum,
                threshold: float = 0.0001,
                file_cols: list = None,
                score_cols: str = None,
                pos_cols: list = None):
    """
    Process a list of bed files names with the first names the merged bed files
    :param threshold:
    :param file_names: list of files path
    :param outdir: output directory
    :param idr_func: idr function to apply
    :param size: int expand peaks of size size
    :param merge_function: function to apply to the score column when
    removing duplicates
    :param file_cols: list of bed file columns
    :param score_cols: column name of the score to use
    :param pos_cols: list of position column name to sort and merge on
    :return: nothing
    """
    if file_cols is None:
        file_cols = narrowpeaks_cols()
    assert access(PurePath(outdir).parent, W_OK), \
        "Folder {} isn't writable".format(outdir)
    if not path.isdir(outdir):
        makedirs(outdir)
    bed_files = readfiles(
        file_names=file_names,
        size=size,
        merge_function=merge_function,
        file_cols=file_cols,
        score_cols=score_cols,
        pos_cols=pos_cols,
    )
    theta, local_idr = idr_func(
        narrowpeaks2array(
            np_list=bed_files,
            score_cols=score_cols
        ),
        threshold=threshold,
        log_name=PurePath(outdir).joinpath(
            "idr_" + PurePath(str(file_names[0])).name
        )
    )
    pd.Series(theta).to_csv(
        PurePath(outdir).joinpath(
            "idr_" + PurePath(str(file_names[0])).name + "_theta.csv"
        ),
        sep='\t',
        encoding='utf-8',
        header=True,
        index=False
    )
    writefiles(
        bed_files=bed_files,
        file_names=file_names,
        idr=local_idr,
        outdir=outdir
    )


if __name__ == "__main__":
    import doctest
    doctest.testmod()
