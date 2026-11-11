# Disk Scheduling Lab

A local Streamlit teaching application for visualizing disk-head movement and comparing FCFS, SSTF, SCAN, C-SCAN, LOOK, and C-LOOK.

## Run locally

From the project directory, install the dependencies and start Streamlit:

```powershell
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

The app starts with 200 cylinders (numbered 0-199), an initial head at 53, and the request queue `98, 183, 37, 122, 14, 124, 65, 67`. Change these inputs in the simulator or comparison page.

## Sections

- **Dashboard:** overview and navigation.
- **Disk Scheduling Simulator:** service order, interactive movement controls, path visualization, movement table, and CSV export.
- **Manual Head Movement:** independent head controls, seek history, undo, reset, and live graph.
- **Total Head Movement Calculator:** sequence statistics, detailed movement table, graph, and CSV export.
- **Algorithm Comparison:** movement totals and service orders for all six algorithms on the same queue.
- **Algorithm Explorer:** algorithm rules, direction behavior, and trade-offs.
- **About Project:** scope and run instructions.

SCAN and C-SCAN show the physical boundary as a travel leg. C-SCAN's edge-to-edge wrap contributes to total head movement but does not service intermediate requests. LOOK and C-LOOK stop or wrap at pending requests rather than visiting unused disk boundaries.

## Run the focused tests

```powershell
python -m unittest discover -s tests -v
```
