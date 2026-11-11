"""Interactive Streamlit dashboard for disk scheduling and seek movement."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from disk_scheduler import (
    ALGORITHMS,
    DIRECTIONAL_ALGORITHMS,
    calculate_sequence,
    parse_integer_list,
    simulate,
)


DEFAULT_CYLINDERS = 200
DEFAULT_HEAD = 53
DEFAULT_QUEUE = "98, 183, 37, 122, 14, 124, 65, 67"
NAVIGATION = (
    "Dashboard",
    "Disk Scheduling Simulator",
    "Manual Head Movement",
    "Total Head Movement Calculator",
    "Algorithm Comparison",
    "Algorithm Explorer",
    "About Project",
)

ALGORITHM_GUIDES = {
    "FCFS": {
        "name": "First Come, First Serve",
        "summary": "Services requests in their arrival order.",
        "strength": "Simple, fair by arrival order, and easy to explain.",
        "tradeoff": "A distant request can make the head pass nearby work.",
        "direction": "No direction setting is needed.",
    },
    "SSTF": {
        "name": "Shortest Seek Time First",
        "summary": "Services the closest pending request at each step.",
        "strength": "Often reduces movement compared with FCFS.",
        "tradeoff": "Requests far from a busy area can wait a long time.",
        "direction": "Chooses the nearest request, so no direction setting is needed.",
    },
    "SCAN": {
        "name": "SCAN (Elevator)",
        "summary": "Services requests in one direction, reaches that disk boundary, then reverses.",
        "strength": "Provides a regular sweep and avoids SSTF's local preference.",
        "tradeoff": "A boundary sweep can add movement before the reversal.",
        "direction": "Select whether the first sweep moves toward cylinder 0 or the last cylinder.",
    },
    "C-SCAN": {
        "name": "Circular SCAN",
        "summary": "Sweeps in one direction, reaches its boundary, then wraps to the opposite boundary.",
        "strength": "Requests are serviced in one consistent sweep direction.",
        "tradeoff": "The boundary-to-boundary wrap adds movement but does not service requests along the wrap.",
        "direction": "Select the sweep direction; a wrap is shown separately from request service.",
    },
    "LOOK": {
        "name": "LOOK",
        "summary": "Like SCAN, but reverses at the last pending request rather than the physical boundary.",
        "strength": "Keeps the sweep behavior while avoiding unnecessary boundary travel.",
        "tradeoff": "Requests may wait for the next sweep.",
        "direction": "Select which side of the head is serviced first.",
    },
    "C-LOOK": {
        "name": "Circular LOOK",
        "summary": "Services requests in one direction, then wraps directly to the farthest pending request on the other side.",
        "strength": "Avoids physical-boundary travel while keeping a one-way service sweep.",
        "tradeoff": "The direct wrap still contributes to total head movement.",
        "direction": "Select the first sweep; a wrap does not service intermediate cylinders.",
    },
}


def apply_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --ink: #17233c;
            --muted: #64748b;
            --line: #e4eaf3;
            --blue: #315db5;
            --blue-deep: #244a96;
            --surface: #ffffff;
        }
        .stApp {
            background:
                radial-gradient(ellipse at 75% -12%, rgba(86, 132, 212, .10), transparent 38%),
                #f4f7fb;
            color: var(--ink);
            font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }
        [data-testid="stMainBlockContainer"] {
            max-width: 1440px;
            padding: 4rem clamp(1rem, 3vw, 2.5rem) 3rem;
        }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #101b30 0%, #172b4c 100%);
            border-right: 1px solid rgba(218, 231, 251, .12);
        }
        [data-testid="stSidebar"] * { color: #edf3ff; }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #aebdd4; }
        [data-testid="stSidebar"] [role="radiogroup"] { gap: .25rem; }
        [data-testid="stSidebar"] [data-testid="stRadioOption"] {
            border-radius: 10px;
            padding: .35rem .5rem;
            transition: background-color .18s ease, color .18s ease;
        }
        [data-testid="stSidebar"] [data-testid="stRadioOption"]:hover,
        [data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] {
            background: rgba(130, 173, 239, .16);
        }
        [data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] {
            box-shadow: inset 3px 0 #83b3ff;
        }
        [data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] > div > div:first-child {
            background: #83b3ff !important;
            border-color: #83b3ff !important;
        }
        .hero {
            padding: clamp(1.35rem, 2.8vw, 2rem);
            border: 1px solid rgba(255, 255, 255, .18);
            border-radius: 20px;
            margin: .2rem 0 1.25rem;
            color: #f8fbff;
            background:
                radial-gradient(circle at 92% 8%, rgba(140, 193, 255, .34), transparent 30%),
                linear-gradient(120deg, #172b50 0%, #315db5 72%, #4386d9 100%);
            box-shadow: 0 16px 38px rgba(37, 72, 133, .16);
        }
        .hero h1 {
            max-width: 900px;
            font-size: clamp(1.9rem, 3vw, 2.5rem);
            line-height: 1.12;
            letter-spacing: -.035em;
            margin: 0 0 .55rem;
            color: white;
        }
        .hero p { margin: 0; color: #e2edff; max-width: 760px; line-height: 1.6; }
        .eyebrow {
            color: #a9d0ff;
            font-size: .72rem;
            font-weight: 750;
            letter-spacing: .14em;
            text-transform: uppercase;
            margin-bottom: .6rem;
        }
        .info-card {
            background: var(--surface);
            border: 1px solid var(--line);
            border-top: 3px solid #6c93d6;
            border-radius: 15px;
            padding: 1.15rem 1.2rem;
            height: 100%;
            box-shadow: 0 5px 18px rgba(19, 38, 71, .045);
            transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease;
        }
        .info-card:hover {
            transform: translateY(-3px);
            border-color: #c9d8ee;
            box-shadow: 0 12px 25px rgba(25, 55, 103, .10);
        }
        .info-card h3 { margin: 0 0 .45rem; font-size: 1rem; color: #1b2c4b; }
        .info-card p { margin: 0; color: var(--muted); font-size: .92rem; line-height: 1.55; }
        [data-testid="stMetric"] {
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: 13px;
            padding: .9rem 1rem;
            box-shadow: 0 4px 14px rgba(19, 38, 71, .035);
        }
        [data-testid="stMetricLabel"] { color: var(--muted); }
        [data-testid="stMetricValue"] { color: var(--ink); font-weight: 720; }
        div[data-testid="stForm"] {
            background: rgba(255, 255, 255, .94);
            border: 1px solid var(--line);
            border-radius: 16px;
            padding: clamp(1rem, 2vw, 1.4rem);
            box-shadow: 0 7px 22px rgba(19, 38, 71, .045);
        }
        .stTextInput input, .stNumberInput input, [data-baseweb="select"] > div {
            border-radius: 10px;
        }
        .stButton > button, .stDownloadButton > button {
            min-height: 2.65rem;
            border-radius: 10px;
            font-weight: 650;
            transition: transform .15s ease, box-shadow .15s ease, background-color .15s ease;
        }
        [data-testid^="stBaseButton-primary"] {
            color: #fff !important;
            background: linear-gradient(135deg, #3568c5, #284f9e) !important;
            border: 1px solid #315db5 !important;
            box-shadow: 0 5px 12px rgba(49, 93, 181, .19);
        }
        [data-testid^="stBaseButton-primary"]:hover {
            background: linear-gradient(135deg, #2f5fb7, #203f82) !important;
            box-shadow: 0 8px 17px rgba(49, 93, 181, .26);
            transform: translateY(-1px);
        }
        .stButton > button:focus-visible, .stDownloadButton > button:focus-visible {
            outline: 3px solid rgba(77, 132, 224, .45);
            outline-offset: 2px;
        }
        div[data-testid="stDataFrame"] {
            max-width: 100%;
            overflow-x: auto;
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: 13px;
            box-shadow: 0 4px 15px rgba(19, 38, 71, .035);
        }
        [data-testid="stPlotlyChart"] { max-width: 100%; }
        hr { border-color: var(--line); }

        @media (max-width: 768px) {
            [data-testid="stMainBlockContainer"] { padding: 4rem .85rem 2rem; }
            .hero { border-radius: 16px; margin-bottom: 1rem; }
            .hero h1 { font-size: clamp(1.7rem, 7vw, 2.2rem); }
            .hero p { font-size: .94rem; }
            [data-testid="stHorizontalBlock"] { gap: .85rem; }
            .info-card { margin-bottom: .75rem; }
            [data-testid="stMetric"] { padding: .75rem .85rem; }
            [data-testid="stMetricValue"] { font-size: clamp(1.2rem, 5vw, 1.7rem); }
            [data-testid="stDataFrame"], [data-testid="stPlotlyChart"] { width: 100%; }
        }
        @media (max-width: 480px) {
            [data-testid="stMainBlockContainer"] { padding-right: .7rem; padding-left: .7rem; }
            .hero { padding: 1.1rem; }
            .info-card { min-height: 0; padding: 1rem; }
            .stButton > button, .stDownloadButton > button { width: 100%; }
            .stMarkdown p { overflow-wrap: anywhere; line-height: 1.55; }
        }
        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after {
                scroll-behavior: auto !important;
                transition-duration: .01ms !important;
                animation-duration: .01ms !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str) -> None:
    st.markdown(
        f'<div class="hero"><div class="eyebrow">OS disk scheduling lab</div>'
        f"<h1>{title}</h1><p>{subtitle}</p></div>",
        unsafe_allow_html=True,
    )


def movement_figure(
    path: list[int],
    movements: list[dict[str, object]],
    cylinders: int,
    title: str,
    request_queue: list[int] | None = None,
    current_step: int | None = None,
) -> go.Figure:
    figure = go.Figure()
    steps = list(range(len(path)))
    service_count = 0
    labels = ["START"]
    hover = [["Initial head", None, path[0], None]] if path else []
    point_colors = ["#2563eb"] if path else []

    for movement in movements:
        kind = str(movement["kind"])
        serviced = bool(movement["serviced"])
        if serviced:
            service_count += 1
        if kind == "Circular wrap":
            labels.append(f"WRAP +{movement['distance']}")
            point_colors.append("#e69b19")
        elif kind == "Disk boundary":
            labels.append(f"END +{movement['distance']}")
            point_colors.append("#e69b19")
        else:
            labels.append(
                f"#{service_count} +{movement['distance']}" if serviced else f"+{movement['distance']}"
            )
            point_colors.append("#18a779" if serviced else "#8091aa")
        hover.append(
            [
                kind,
                movement["start"],
                movement["end"],
                f"{movement['distance']} cylinders",
            ]
        )

    if path:
        figure.add_trace(
            go.Scatter(
                x=steps,
                y=path,
                mode="lines+markers+text",
                name="Planned head path",
                line={"color": "#c5cfdd", "width": 2, "dash": "dot"},
                marker={"size": 8, "color": point_colors, "line": {"color": "white", "width": 1}},
                text=labels,
                textposition="top center",
                textfont={"size": 10, "color": "#52627c"},
                customdata=hover,
                hovertemplate=(
                    "Step %{x}<br>Cylinder %{y}<br>%{customdata[0]}"
                    "<br>From %{customdata[1]} to %{customdata[2]}"
                    "<br>Movement: %{customdata[3]}<extra></extra>"
                ),
            )
        )
        if current_step is not None:
            visible = max(1, min(len(path), current_step + 1))
            figure.add_trace(
                go.Scatter(
                    x=steps[:visible],
                    y=path[:visible],
                    mode="lines",
                    name="Travelled so far",
                    line={"color": "#315db5", "width": 4},
                    hoverinfo="skip",
                )
            )
            head_index = visible - 1
            figure.add_trace(
                go.Scatter(
                    x=[head_index],
                    y=[path[head_index]],
                    mode="markers+text",
                    name="Current head",
                    marker={"size": 15, "symbol": "star", "color": "#315db5"},
                    text=["HEAD"],
                    textposition="bottom center",
                    hovertemplate=f"Current head<br>Cylinder {path[head_index]}<extra></extra>",
                )
            )

        for index, movement in enumerate(movements):
            if movement["start"] == movement["end"]:
                continue
            traveled = current_step is not None and index < current_step
            figure.add_annotation(
                x=index + 1,
                y=movement["end"],
                ax=index,
                ay=movement["start"],
                xref="x",
                yref="y",
                axref="x",
                ayref="y",
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=2 if traveled else 1,
                arrowcolor="#315db5" if traveled else "#9aa9bd",
            )

    if request_queue:
        request_x = [-0.75 + (index % 4) * 0.07 for index in range(len(request_queue))]
        figure.add_trace(
            go.Scatter(
                x=request_x,
                y=request_queue,
                mode="markers+text",
                name="Request queue",
                marker={"size": 9, "color": "#b9c7dc", "line": {"color": "white", "width": 1}},
                text=[f"R{index + 1}" for index in range(len(request_queue))],
                textposition="middle left",
                customdata=list(enumerate(request_queue, start=1)),
                hovertemplate="Request %{customdata[0]}<br>Cylinder %{customdata[1]}<extra></extra>",
            )
        )

    figure.update_layout(
        title={"text": title, "x": 0.02, "xanchor": "left"},
        template="plotly_white",
        height=440,
        margin={"l": 22, "r": 20, "t": 58, "b": 45},
        paper_bgcolor="white",
        plot_bgcolor="white",
        hovermode="closest",
        legend={"orientation": "h", "y": -0.2},
        xaxis={
            "title": "Movement step (requests shown in the left lane)",
            "range": [-1.25, max(1, len(path) - 0.2)],
            "tickmode": "array",
            "tickvals": steps,
            "ticktext": [str(step) for step in steps],
            "gridcolor": "#edf1f7",
            "zeroline": False,
        },
        yaxis={
            "title": f"Cylinder (0-{cylinders - 1})",
            "range": [-1, max(2, cylinders)],
            "gridcolor": "#edf1f7",
            "zeroline": False,
        },
    )
    return figure


def _simulation_form(prefix: str, include_algorithm: bool) -> tuple[bool, int, int, str, str, str]:
    with st.form(f"{prefix}_form"):
        st.subheader("Disk and request queue")
        first, second = st.columns(2)
        with first:
            cylinders = st.number_input(
                "Total cylinders",
                min_value=1,
                max_value=10_000,
                value=DEFAULT_CYLINDERS,
                step=1,
                key=f"{prefix}_cylinders",
                help="Cylinder numbers range from 0 to total cylinders minus 1.",
            )
            head = st.number_input(
                "Initial head position",
                min_value=0,
                max_value=9_999,
                value=DEFAULT_HEAD,
                step=1,
                key=f"{prefix}_head",
            )
        with second:
            request_text = st.text_input(
                "Request queue (commas or spaces)",
                value=DEFAULT_QUEUE,
                key=f"{prefix}_requests",
            )
            if include_algorithm:
                algorithm = st.selectbox(
                    "Scheduling algorithm",
                    ALGORITHMS,
                    key=f"{prefix}_algorithm",
                )
            else:
                algorithm = "ALL"
            direction = st.selectbox(
                "Initial sweep direction",
                ("right", "left"),
                key=f"{prefix}_direction",
                help="Used by SCAN, C-SCAN, LOOK, and C-LOOK; ignored by FCFS and SSTF.",
            ) if not include_algorithm or algorithm in DIRECTIONAL_ALGORITHMS else "right"
            if include_algorithm and algorithm not in DIRECTIONAL_ALGORITHMS:
                st.caption("Sweep direction is used by SCAN, C-SCAN, LOOK, and C-LOOK.")
        submitted = st.form_submit_button(
            "Generate schedule" if include_algorithm else "Compare all algorithms",
            type="primary",
            width="stretch",
        )
    return submitted, int(cylinders), int(head), request_text, algorithm, direction


def page_dashboard() -> None:
    page_header(
        "Disk Scheduling Simulator",
        "Explore how operating systems order I/O requests and how each decision moves the disk head.",
    )
    st.markdown(
        "Use the navigation on the left to run an algorithm, move the head by hand, or compare seek distances."
    )
    cards = st.columns(3)
    for column, title, description in zip(
        cards,
        ("Six scheduling strategies", "Step-by-step motion", "One shared disk model"),
        (
            "Compare FCFS, SSTF, SCAN, C-SCAN, LOOK, and C-LOOK on the same queue.",
            "Follow every serviced request, disk boundary, and circular wrap in an interactive graph.",
            "Start with 200 cylinders, head at 53, and the classic eight-request example.",
        ),
    ):
        with column:
            st.markdown(
                f'<div class="info-card"><h3>{title}</h3><p>{description}</p></div>',
                unsafe_allow_html=True,
            )

    st.subheader("How to use the lab")
    st.markdown(
        """
        1. Open **Disk Scheduling Simulator** and choose an algorithm, queue, and sweep direction.
        2. Step through its service order and inspect each leg in the movement table.
        3. Open **Algorithm Comparison** to compare all six strategies on the same inputs.
        4. Try **Manual Head Movement** or the **Total Head Movement Calculator** independently.
        """
    )
    st.info(
        "**Head movement** is the sum of the absolute cylinder-to-cylinder distances. "
        "A boundary visit or circular wrap moves the head but is not itself a serviced request."
    )


def page_simulator() -> None:
    page_header(
        "Disk Scheduling Simulator",
        "Choose a scheduling policy and step through its complete head path.",
    )
    st.caption("The default queue is 98, 183, 37, 122, 14, 124, 65, 67; cylinder range is 0-199.")
    submitted, cylinders, head, request_text, algorithm, direction = _simulation_form(
        "simulator", include_algorithm=True
    )

    if submitted:
        try:
            requests = parse_integer_list(request_text, "Request queue")
            result = simulate(algorithm, cylinders, head, requests, direction)
            st.session_state["sim_schedule"] = result.as_dict()
            st.session_state["sim_requests"] = requests
            st.session_state["sim_cylinders"] = cylinders
            st.session_state["sim_index"] = 0
            st.session_state["sim_playing"] = False
            st.session_state["sim_speed"] = "1x"
        except ValueError as error:
            st.session_state.pop("sim_schedule", None)
            st.error(str(error))

    schedule = st.session_state.get("sim_schedule")
    if schedule is None:
        st.info("Enter the disk details above, then generate a schedule to begin.")
        return

    st.divider()
    st.subheader(f"{schedule['algorithm']} service plan")
    service_order = schedule["service_order"]
    service_text = " -> ".join(map(str, service_order)) if service_order else "No pending requests"
    st.markdown(f"**Service order:** {schedule['initial_head']} -> {service_text}")
    metric_columns = st.columns(3)
    metric_columns[0].metric("Total head movement", f"{schedule['total_movement']} cylinders")
    metric_columns[1].metric("Requests serviced", len(service_order))
    metric_columns[2].metric("Movement legs", len(schedule["movements"]))

    controls = st.columns(5)
    if controls[0].button("Start simulation", width="stretch"):
        if schedule["movements"]:
            if st.session_state.get("sim_index", 0) >= len(schedule["movements"]):
                st.session_state["sim_index"] = 0
            st.session_state["sim_playing"] = True
        else:
            st.session_state["sim_playing"] = False
    if controls[1].button("Pause", width="stretch"):
        st.session_state["sim_playing"] = False
    if controls[2].button("Previous step", width="stretch"):
        st.session_state["sim_playing"] = False
        st.session_state["sim_index"] = max(0, st.session_state.get("sim_index", 0) - 1)
    if controls[3].button("Next step", width="stretch"):
        st.session_state["sim_playing"] = False
        st.session_state["sim_index"] = min(
            len(schedule["movements"]), st.session_state.get("sim_index", 0) + 1
        )
    if controls[4].button("Reset simulation", width="stretch"):
        st.session_state["sim_playing"] = False
        st.session_state["sim_index"] = 0

    speed_column, status_column = st.columns([1, 3])
    with speed_column:
        speed = st.select_slider(
            "Simulation speed",
            options=("0.5x", "1x", "1.5x", "2x"),
            key="sim_speed",
        )
    with status_column:
        current_step = st.session_state.get("sim_index", 0)
        st.caption(
            f"{'Playing' if st.session_state.get('sim_playing') else 'Paused'} · "
            f"step {current_step} of {len(schedule['movements'])}"
        )

    interval = 1.0 / float(speed.removesuffix("x"))
    chart_container = st.container()

    @st.fragment(run_every=interval if st.session_state.get("sim_playing") else None)
    def render_live_chart() -> None:
        if st.session_state.get("sim_playing"):
            total_steps = len(schedule["movements"])
            next_step = st.session_state.get("sim_index", 0) + 1
            st.session_state["sim_index"] = min(total_steps, next_step)
            if next_step >= total_steps:
                st.session_state["sim_playing"] = False
                st.rerun()

        figure = movement_figure(
            schedule["path"],
            schedule["movements"],
            st.session_state["sim_cylinders"],
            f"{schedule['algorithm']} head movement",
            st.session_state["sim_requests"],
            st.session_state.get("sim_index", 0),
        )
        chart_container.plotly_chart(figure, width="stretch")

    render_live_chart()

    movements = schedule["movements"]
    if movements:
        movement_frame = pd.DataFrame(movements)
        movement_frame.insert(0, "Step", range(1, len(movement_frame) + 1))
        movement_frame = movement_frame.rename(
            columns={
                "start": "From",
                "end": "To",
                "distance": "Distance",
                "kind": "Movement type",
                "serviced": "Services request",
            }
        )
        st.subheader("Movement-by-movement breakdown")
        st.dataframe(movement_frame, hide_index=True, width="stretch")
        st.download_button(
            "Download movement table (CSV)",
            movement_frame.to_csv(index=False).encode("utf-8"),
            file_name=f"{schedule['algorithm'].lower().replace('-', '_')}_movements.csv",
            mime="text/csv",
        )
    else:
        st.success("All requests are already at the initial head position; no travel is required.")

    st.caption(
        "Disk boundaries and circular wraps appear as separate travel legs. A wrap crosses empty "
        "cylinders; only legs marked as servicing a request count as a service."
    )


def page_manual() -> None:
    page_header(
        "Manual Head Movement",
        "Move the head one cylinder position at a time and build a seek-distance history.",
    )
    st.markdown("**Seek distance = |Next position - Current position|**")
    left, right = st.columns(2)
    with left:
        cylinders = int(
            st.number_input(
                "Total cylinders",
                min_value=1,
                max_value=10_000,
                value=DEFAULT_CYLINDERS,
                key="manual_cylinders",
            )
        )
    with right:
        initial = int(
            st.number_input(
                "Initial head position",
                min_value=0,
                max_value=9_999,
                value=DEFAULT_HEAD,
                key="manual_initial",
            )
        )

    if "manual_active_cylinders" not in st.session_state:
        st.session_state["manual_active_cylinders"] = cylinders
        st.session_state["manual_current"] = min(initial, cylinders - 1)
        st.session_state["manual_origin"] = min(initial, cylinders - 1)
        st.session_state["manual_history"] = []
    elif st.session_state["manual_active_cylinders"] != cylinders:
        st.session_state["manual_active_cylinders"] = cylinders
        st.session_state["manual_current"] = min(initial, cylinders - 1)
        st.session_state["manual_origin"] = min(initial, cylinders - 1)
        st.session_state["manual_history"] = []
        st.info("The disk size changed, so the movement history was cleared.")

    current = int(st.session_state["manual_current"])
    if initial >= cylinders:
        st.error(f"Initial head position must be between 0 and {cylinders - 1}.")
    else:
        set_column, move_column, undo_column, reset_column = st.columns([1, 1, 1, 1])
        if set_column.button("Apply starting position", width="stretch"):
            st.session_state["manual_current"] = initial
            st.session_state["manual_origin"] = initial
            st.session_state["manual_active_cylinders"] = cylinders
            st.session_state["manual_history"] = []
            st.rerun()

        with move_column:
            next_position = int(
                st.number_input(
                    "Next cylinder",
                    min_value=0,
                    max_value=9_999,
                    value=min(current, cylinders - 1),
                    key="manual_next",
                )
            )
        add_clicked = st.button("Add movement", type="primary", width="stretch")
        if add_clicked:
            if next_position >= cylinders:
                st.error(f"Next position must be between 0 and {cylinders - 1}.")
            else:
                distance = abs(next_position - current)
                st.session_state["manual_history"].append(
                    {
                        "start": current,
                        "end": next_position,
                        "distance": distance,
                        "kind": "Manual movement",
                        "serviced": False,
                    }
                )
                st.session_state["manual_current"] = next_position
                st.rerun()

        if undo_column.button("Undo last movement", width="stretch"):
            history = st.session_state["manual_history"]
            if history:
                previous = history.pop()
                st.session_state["manual_current"] = previous["start"]
                st.rerun()
        if reset_column.button("Reset history", width="stretch"):
            st.session_state["manual_current"] = initial
            st.session_state["manual_origin"] = initial
            st.session_state["manual_history"] = []
            st.rerun()

    history = st.session_state["manual_history"]
    total = sum(movement["distance"] for movement in history)
    average = total / len(history) if history else 0
    metrics = st.columns(4)
    metrics[0].metric("Current head", current if initial >= cylinders else st.session_state["manual_current"])
    metrics[1].metric("Total head movement", f"{total} cylinders")
    metrics[2].metric("Average per move", f"{average:.1f} cylinders")
    metrics[3].metric("Movements", len(history))

    path = [st.session_state["manual_origin"]] + [movement["end"] for movement in history]
    st.plotly_chart(
        movement_figure(
            path,
            history,
            cylinders,
            "Manual movement history",
            current_step=len(history),
        ),
        width="stretch",
    )
    if history:
        frame = pd.DataFrame(history)
        frame.insert(0, "Step", range(1, len(frame) + 1))
        frame = frame.rename(
            columns={"start": "From", "end": "To", "distance": "Seek distance"}
        )[["Step", "From", "To", "Seek distance"]]
        st.dataframe(frame, hide_index=True, width="stretch")
    else:
        st.info("No manual movements yet. Choose a next cylinder and add a movement.")


def page_calculator() -> None:
    page_header(
        "Total Head Movement Calculator",
        "Enter any sequence of visited cylinders to calculate each seek and the overall movement.",
    )
    with st.form("calculator_form"):
        cylinders = int(
            st.number_input(
                "Total cylinders",
                min_value=1,
                max_value=10_000,
                value=DEFAULT_CYLINDERS,
                key="calculator_cylinders",
            )
        )
        sequence_text = st.text_input(
            "Complete head-position sequence",
            value="53, 98, 183, 37, 122",
            help="Use commas or spaces; include the initial position followed by each visited cylinder.",
            key="calculator_sequence",
        )
        submitted = st.form_submit_button("Calculate movement", type="primary")

    if submitted:
        try:
            sequence = parse_integer_list(sequence_text, "Position sequence")
            if any(position < 0 or position >= cylinders for position in sequence):
                raise ValueError(f"Every position must be between 0 and {cylinders - 1}.")
            st.session_state["calculator_result"] = {
                "sequence": sequence,
                "movements": calculate_sequence(sequence),
                "cylinders": cylinders,
            }
        except ValueError as error:
            st.session_state.pop("calculator_result", None)
            st.error(str(error))

    result = st.session_state.get("calculator_result")
    if result is None:
        st.info("The example sequence is ready. Click Calculate movement to see the breakdown.")
        return

    sequence = result["sequence"]
    movements = result["movements"]
    distances = [movement["distance"] for movement in movements]
    total = sum(distances)
    average = total / len(distances) if distances else 0
    metrics = st.columns(4)
    metrics[0].metric("Total movement", f"{total} cylinders")
    metrics[1].metric("Average movement", f"{average:.1f} cylinders")
    metrics[2].metric("Maximum movement", f"{max(distances, default=0)} cylinders")
    metrics[3].metric("Number of movements", len(distances))

    st.markdown("**Complete sequence:** " + " -> ".join(map(str, sequence)))
    if movements:
        frame = pd.DataFrame(movements).rename(
            columns={"step": "Step", "start": "From", "end": "To", "distance": "Distance"}
        )
        frame["Calculation"] = frame.apply(
            lambda row: f"{row['From']} -> {row['To']} = {row['Distance']}",
            axis=1,
        )
        frame = frame[["Step", "Calculation", "From", "To", "Distance"]]
        st.subheader("Detailed movement calculation")
        st.dataframe(frame, hide_index=True, width="stretch")
        st.download_button(
            "Download calculation (CSV)",
            frame.to_csv(index=False).encode("utf-8"),
            file_name="head_movement_calculation.csv",
            mime="text/csv",
        )
    else:
        st.success("The sequence contains one position, so it requires zero movements.")

    path = list(sequence)
    graph_movements = [
        {
            "start": movement["start"],
            "end": movement["end"],
            "distance": movement["distance"],
            "kind": "Movement",
            "serviced": True,
        }
        for movement in movements
    ]
    st.plotly_chart(
        movement_figure(
            path,
            graph_movements,
            result["cylinders"],
            "Sequence movement graph",
            current_step=len(graph_movements),
        ),
        width="stretch",
    )
    st.caption("Example: 53 -> 98 = |98 - 53| = 45 cylinders.")


def page_comparison() -> None:
    page_header(
        "Algorithm Comparison",
        "Run every scheduling strategy against one queue and compare total movement and service order.",
    )
    submitted, cylinders, head, request_text, _, direction = _simulation_form(
        "comparison", include_algorithm=False
    )
    if submitted:
        try:
            requests = parse_integer_list(request_text, "Request queue")
            results = [
                simulate(algorithm, cylinders, head, requests, direction)
                for algorithm in ALGORITHMS
            ]
            st.session_state["comparison_results"] = [
                {
                    "Algorithm": result.algorithm,
                    "Total movement": result.total_movement,
                    "Service order": " -> ".join(map(str, result.service_order))
                    or "No pending requests",
                    "Path": list(result.path),
                    "Movements": [
                        movement.__dict__ for movement in result.movements
                    ],
                }
                for result in results
            ]
            st.session_state["comparison_disk_cylinders"] = cylinders
            st.session_state["comparison_queue_values"] = requests
        except ValueError as error:
            st.session_state.pop("comparison_results", None)
            st.error(str(error))

    results = st.session_state.get("comparison_results")
    if results is None:
        st.info("Enter a request queue and compare all six algorithms.")
        return

    table = pd.DataFrame(
        [
            {
                "Algorithm": result["Algorithm"],
                "Total movement (cylinders)": result["Total movement"],
                "Service order": result["Service order"],
            }
            for result in results
        ]
    ).sort_values("Total movement (cylinders)", kind="stable")
    st.subheader("Movement and service-order comparison")
    st.dataframe(table, hide_index=True, width="stretch")

    chart = go.Figure(
        go.Bar(
            x=table["Algorithm"],
            y=table["Total movement (cylinders)"],
            marker={
                "color": table["Total movement (cylinders)"],
                "colorscale": [[0, "#18a779"], [0.55, "#4386d9"], [1, "#e69b19"]],
                "showscale": False,
            },
            text=table["Total movement (cylinders)"],
            textposition="outside",
            hovertemplate="%{x}<br>%{y} cylinders<extra></extra>",
        )
    )
    chart.update_layout(
        title="Total head movement by algorithm",
        template="plotly_white",
        height=380,
        yaxis_title="Cylinder movement",
        xaxis_title="Scheduling algorithm",
        margin={"l": 20, "r": 20, "t": 65, "b": 30},
    )
    st.plotly_chart(chart, width="stretch")

    st.subheader("Inspect an individual path")
    selected = st.selectbox("Algorithm path", ALGORITHMS, key="comparison_path")
    selected_result = next(result for result in results if result["Algorithm"] == selected)
    st.plotly_chart(
        movement_figure(
            selected_result["Path"],
            selected_result["Movements"],
            st.session_state["comparison_disk_cylinders"],
            f"{selected} head movement",
            st.session_state["comparison_queue_values"],
            current_step=len(selected_result["Movements"]),
        ),
        width="stretch",
    )


def page_explorer() -> None:
    page_header(
        "Algorithm Explorer",
        "Learn the decision rule, the trade-offs, and what to look for in each movement graph.",
    )
    for algorithm in ALGORITHMS:
        guide = ALGORITHM_GUIDES[algorithm]
        with st.expander(f"{algorithm} - {guide['name']}", expanded=algorithm == "SCAN"):
            st.markdown(guide["summary"])
            st.markdown(f"**Direction:** {guide['direction']}")
            st.markdown(f"**Strength:** {guide['strength']}")
            st.markdown(f"**Trade-off:** {guide['tradeoff']}")
            if algorithm in ("SCAN", "C-SCAN"):
                st.info(
                    "The disk edge is a movement point, not automatically a request. "
                    "The circular wrap is counted in movement even though no requests are serviced on it."
                )
            elif algorithm in ("LOOK", "C-LOOK"):
                st.info(
                    "LOOK-family algorithms turn or wrap at pending requests, so they avoid unnecessary travel to disk edges."
                )

    st.subheader("At a glance")
    overview = pd.DataFrame(
        [
            ["FCFS", "Arrival order", "No", "Can pass close requests"],
            ["SSTF", "Nearest pending request", "No", "A distant request can wait"],
            ["SCAN", "Directional sweep and boundary reversal", "Yes", "Includes a disk-edge visit"],
            ["C-SCAN", "One-way sweep and boundary wrap", "Yes", "Wrap is travel, not service"],
            ["LOOK", "Directional sweep to last request", "Yes", "No unnecessary edge visit"],
            ["C-LOOK", "One-way sweep and request-to-request wrap", "Yes", "Wrap distance still counts"],
        ],
        columns=["Algorithm", "Decision rule", "Direction?", "Key observation"],
    )
    st.dataframe(overview, hide_index=True, width="stretch")


def page_about() -> None:
    page_header(
        "About the Project",
        "A local, interactive teaching tool for visualizing operating-system disk I/O scheduling.",
    )
    st.subheader("Project objective")
    st.write(
        "This application demonstrates how a disk scheduler orders pending cylinder requests "
        "and how those choices affect disk-head movement. It is designed as a learning aid for "
        "an Operating Systems course."
    )
    st.subheader("Topics covered")
    st.markdown(
        """
        - FCFS, SSTF, SCAN, C-SCAN, LOOK, and C-LOOK scheduling.
        - Request service order, individual seek distances, total movement, and sweep direction.
        - Disk-boundary travel versus request service, including circular wrap travel.
        - Manual head control, sequence calculation, and side-by-side comparison.
        """
    )
    st.subheader("How to run locally")
    st.code(
        "python -m pip install -r requirements.txt\n"
        "python -m streamlit run app.py",
        language="bash",
    )
    st.caption(
        "This simulator reports cylinder movement, not rotational latency, transfer time, "
        "or a complete physical-disk timing model."
    )


def main() -> None:
    st.set_page_config(
        page_title="Disk Scheduling Lab",
        page_icon="💿",
        layout="wide",
        initial_sidebar_state="auto",
    )
    apply_styles()
    with st.sidebar:
        st.markdown("## DISK LAB")
        st.caption("Operating Systems · Interactive simulator")
        selected_page = st.radio("Navigate", NAVIGATION, label_visibility="collapsed")
        st.divider()
        st.caption("Cylinder numbering starts at 0.")

    page_functions = {
        "Dashboard": page_dashboard,
        "Disk Scheduling Simulator": page_simulator,
        "Manual Head Movement": page_manual,
        "Total Head Movement Calculator": page_calculator,
        "Algorithm Comparison": page_comparison,
        "Algorithm Explorer": page_explorer,
        "About Project": page_about,
    }
    page_functions[selected_page]()


if __name__ == "__main__":
    main()
