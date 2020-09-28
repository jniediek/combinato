# Combinato Spike Sorting

## Introduction
_Combinato Spike Sorting_ is a software for spike extraction, automatic spike sorting, manual improvement of sorting, artifact rejection, and visualization of continuous recordings and spikes. It offers a toolchain that transforms raw data into single/multi-unit spike trains. The software is largely modular, thus useful also if you are interested in just extraction or just sorting of spikes.

Combinato Spike Sorting works very well with large raw data files (tested with 100-channel, 15-hour recordings, i.e. > 300 GB of raw data). Most parts make use of multiprocessing and scale well with tens of CPUs.

Combinato is a collection of a few command-line tools and two GUIs, written in Python and depending on a few standard modules. It is being developed mostly for Linux, but it works on Windows and OS X, too.

The documentation of Combinato is maintained as a [Wiki](../../wiki). 

## Installing Combinato
- [Installation on Linux](../../wiki/Installation-on-Linux) (recommended)
- [Installation on Windows](../../wiki/Installation-on-Windows)
- [Installation on OS X](../../wiki/Installation-on-OSX)

## Tutorial
Please walk through our instructive Tutorial.
- [Part I](../../wiki/Tutorial-Synthetic-Data)
- [Part II](../../wiki/Tutorial-Synthetic-Data-II)
- [Part III](../../wiki/Tutorial-Real-Data)

## More Information
- [FAQ](../../wiki/FAQ)
- [Details](../../wiki/Details)

## Citing Combinato 

When using Combinato in your work, please cite [this paper](http://journals.plos.org/plosone/article?id=10.1371/journal.pone.0166598):

Johannes Niediek, Jan Boström, Christian E. Elger, Florian Mormann. „Reliable Analysis of Single-Unit Recordings from the Human Brain under Noisy Conditions: Tracking Neurons over Hours“. PLOS ONE 11 (12): e0166598. 2016. [doi:10.1371/journal.pone.0166598](doi:10.1371/journal.pone.0166598).

## Contact
Please feel free to use the GitHub infrastructure for questions, bug reports, feature requests, etc.

Johannes Niediek, 2016-2020, `jonied@posteo.de`.
