# Repository contents and GitHub upload

## Included material

- Python source, command-line entry points and existing tests.
- Dashboard configuration and dependency lists.
- The current road network, its source OSM extract, original Wizard network and surveyed signal records.
- The selected 132-run checkpoint, with its recorded signatures and quality audit.
- Result JSON for all 132 runs across three demand scales and seeds 100–103.
- A complete frozen input example at demand scale 0.5, seed 100.
- The executed notebook, selected analysis outputs, methodology evidence and defense material.

Published directory names match the application and notebook paths. Recorded data retain their original locations. `.gitattributes` disables newline conversion to preserve recorded file hashes and source signatures.

## Local-only material

`.gitignore` excludes virtual environments, logs, temporary files, downloaded research-paper reading copies, historical cohorts, verification experiments and other generated scenarios. These folders can remain on the research computer while the Git repository contains the selected project material.

The original 249-run history and older sublane datasets remain local. The full `dataset_cong_hoa/inputs` collection, full-population tripinfo XML and detailed run logs also remain local, apart from the included example and compact result evidence. Keep the complete local workspace for access to those records.

The included result tables support notebook and dashboard analysis. Re-exporting every measurement from raw simulator logs or replaying all 132 runs requires the full original local experiment. Generating new inputs creates a new experiment with its own recorded signatures.

Source papers are identified by DOI or source URL in `traffic_study/paper_methods.py` and the implementation documentation. Map data © OpenStreetMap contributors, under the [Open Database License](https://opendatacommons.org/licenses/odbl/1-0/). The prepared network includes manual changes for this study.

## Upload from PowerShell

Create an empty GitHub repository in your account, then run these commands from the project root. Git is initialised locally on branch `main` during repository preparation. Review the status before creating the first commit.

```powershell
git status --short
git add .
git diff --cached --stat
git commit -m "Add Cong Hoa signal control study"
```

Connect your empty GitHub repository, replacing the example account and repository name with your own.

```powershell
git remote add origin https://github.com/YOUR_USERNAME/cong-hoa-traffic-study.git
git push -u origin main
```

GitHub authentication uses your configured Git credential manager. If a commit requests an author name or email, set your own Git identity before committing.

## Verify a fresh checkout

Follow the dashboard quick-start commands in the root README. The default view should show 132 selected runs before filtering. The dataset contains 528 journey records across three demand scales and four seeds. Its saved audit remains `accepted=false`.

For simulation and notebook work, install their dependency files in `.venv`, then run the existing unit tests and open `analysis/cong_hoa_analysis.ipynb`.
