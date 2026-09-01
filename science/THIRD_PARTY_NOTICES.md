# Third-party notices

The directory `vendor/pyworld3` contains Pyworld3 1.1 by Charles
Vanwynsberghe, downloaded from the Python Package Index. Pyworld3 implements
the World3 model described in *Dynamics of Growth in a Finite World* (1974).

Pyworld3 is governed by the CeCILL license. The complete license text is
included in `vendor/LICENSE-pyworld3.txt`. The project wrapper does not alter
the vendored equations.

The directory `vendor/world3_03` contains the official Vensim sample model
`World3_03_Scenarios.mdl`, downloaded from:

https://www.vensim.com/documentation/Models/Sample/WRLD3-03/World3_03_Scenarios.mdl

The file's SHA-256 digest at ingestion was
`42b22c734a71ee03abc31d80872234fbcd93d3d4fb9a277f606c6d677846731d`.
The source file is retained unchanged. At runtime, the adapter removes one
Vensim help-link metadata directive from a temporary copy because PySD does
not parse that directive; no equation or numerical parameter is altered.
