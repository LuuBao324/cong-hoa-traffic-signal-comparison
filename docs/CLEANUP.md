# Submission cleanup

## Completed

The active implementation is grouped in `traffic_study`. Three command-line entry points remain at the project root. Streamlit is in `app`, operational utilities are in `scripts`, and regression checks are in `tests`. Python code has been formatted consistently. Code comments, generated reports and application labels use English.

The dataset exporter now writes `dataset.csv` as the main journey table. Derived comparison tables are `pairwise.csv` and `summary.csv`. Column descriptions are in `dataset_metadata.json`. Streamlit reads the main dataset. Duplicate journey exports were removed after their row counts were checked. The historical table was merged with its richer duplicate before removal, preserving 996 recorded journeys.

After the user confirmed the deletion scope, the obsolete HTML dashboard, the incorrect `tan_binh` workspace, one-off replay/safety/input-reuse/cohort scripts, unused legacy algorithm tests, and replaced overview documents were deleted. The superseded pilot, smoke, backend replay, early nonlearning and early paper experiment folders were also removed. The current dataset, two earlier 12-November verification sets, current lane-based verification, interactive scenarios and the previously retained 249-run historical trial serve the current project.

Retired G2P, fuzzy, smoothing, occupancy and QD controller branches were removed from the active implementation. The ten registered research methods and fixed-time reference remain in the registry. Dependencies used only for retired extraction and plotting code were removed from the simulation requirements.

## Experimental versions

The source network includes the repaired internal lane indexes. New scenarios use single-file lane-based motorcycle movement. The saved sublane experiment retains its original measurements and signatures. The code reorganisation and movement-model change require a new experiment folder for future measurements.

Street-name lookup strings and original survey data retain their original spelling because they identify network objects and field records. Raw historical outputs retain their recorded content.

The first broad deletion attempt was rejected by automatic approval review. The user then explicitly confirmed the scope, and the approved obsolete targets were deleted using checked workspace paths.
