#!/usr/bin/env python3
# -*-coding:Utf-8 -*

import setuptools

with open("../README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="idr",
    version="1.0.0",
    packages=['idr'],
    install_requires=[
        'scipy>=1.3',
        'numpy>=1.16',
        'pynverse>=0.1',
        'matplotlib>=3.1'
    ],
    author="Laurent Modolo",
    author_email="laurent.modolo@ens-lyon.fr",
    description="Compute idr from m NarrowPeak files and a merged NarrowPeak",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/LBMC/idr",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: CEA CNRS Inria Logiciel Libre License, \
version 2.1 (CeCILL-2.1)",
        "Operating System :: OS Independent"
    ],
    test_suite='pytest',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': ['idr=idr.idr:main'],
    }
)
