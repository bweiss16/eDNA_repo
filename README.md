# eDNA_repo
repository contains all software used to control the MS16 and MP eDNA sampling systems

DIRECT CONTROL VIA GUI
GUI4_MP_Sampler.py -> Used to control the MultiPuffer systems via a serial connection
GUI4_MS16_Sampler.py -> Used to control the older MS16 systems via a serial connection

See the "DeepSeee GUI Markdown" Doc for more informaiton on insalling and using the GUI
https://docs.google.com/document/d/1-A5Zt4VRrt7MCKxrU92M0y6Qt0FAggb5SYdGpuPCCp0/edit?usp=sharing

See the "Setting up a Mac Computer" doc if you are running the GUI on a Mac (and not a windows computer)
https://docs.google.com/document/d/194iIzvI8DH6kU3tzRXDZBjSLs4a2OADnd76ob0NMxqU/edit?usp=sharing

AUTONMOUS SAMPLNG WITH DAP
eDNA_driver_v2.0.py -> driver used within the DAP environemnt (Lander at URI managed my Chris Roman)
config.ini -> configuration file used with the eDNA_driver_v2.0.py to set pump timing
