"""Local analysis of recorded SUMO journeys and matched controller comparisons."""

from pathlib import Path
import json
import sys

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from traffic_study.dataset import pairwise_rows, valid_pair

BASE = ROOT / "tan_binh_2026"
CHECKPOINT = BASE / "dataset_cong_hoa/checkpoints/132_runs"
LABELS = {
    "fixed_time": "Fixed-time",
    "switching_loss_mp": "Switching-Loss MP",
    "c_mp": "C-MP",
    "td_mp_2023": "TD-MP",
    "cv_mp_2025": "CV-MP",
    "queue_responsive_2026": "Queue-responsive",
    "cn_mp_2024": "CN-MP",
    "wncn_mp_2024": "WNCN-MP",
    "wstar_ncn_mp_2024": "W*NCN-MP",
    "wstar_cn_mp_2024": "W*CN-MP",
    "coordinated_auction_2024": "Coordinated Auction",
}
POLICIES = ["All four tracked vehicles arrived", "Exclude affected tracked observations", "Zero network events"]
PAIR_COLUMNS = ["demand_scale", "seed", "probe_id", "vehicle_type", "route_variant", "method_a", "method_b", "paired_valid", "travel_time_a_s", "travel_time_b_s", "difference_a_minus_b_s", "improvement_a_vs_b_percent"]
EXPORT_COLUMNS = ["run_id", "method", "demand_scale", "seed", "probe_id", "vehicle_type", "route_variant", "completed", "censored", "analysis_eligible", "travel_time_s", "waiting_time_s", "depart_delay_s", "time_loss_s", "waiting_count", "route_length_m", "mean_speed_kmh"]


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else {}


def records(frame):
    return frame.astype(object).where(pd.notna(frame), None).to_dict("records")


def csv_bytes(frame):
    return frame.to_csv(index=False).encode("utf-8-sig")


def reset_filters():
    for key in ["vehicle", "route", "scales", "methods", "seeds", "policy", "pair_scale", "method_a", "method_b"]:
        st.session_state.pop(key, None)


@st.cache_data(show_spinner=False)
def load_data(folder_name, file_stamps):
    folder = Path(folder_name)
    data = pd.read_csv(folder / "dataset.csv")
    plan = read_json(folder / "plan.json")
    metadata = read_json(folder / "dataset_metadata.json")
    audit = read_json(folder / "acceptance.json")
    if metadata.get("plan", {}).get("signature") != plan.get("signature"):
        raise ValueError("The exported dataset and experiment plan have different signatures.")
    if data.duplicated(["run_id", "probe_id"]).any():
        raise ValueError("Duplicate run and tracked-vehicle records were found.")
    for column in ["completed", "censored", "valid_for_comparison", "all_four_arrived", "probe_collision", "probe_teleported"]:
        if column in data:
            data[column] = data[column].map(lambda value: str(value).lower() == "true")
    data["all_four_arrived"] = data.groupby("run_id")["completed"].transform("all")
    data["censored"] = ~data["completed"]
    for column in ["collisions", "teleports"]:
        if column not in data:
            data[column] = float("nan")
    return data, plan, metadata, audit


def eligible_mask(data, policy):
    eligible = data["all_four_arrived"] & data["completed"] & data["travel_time_s"].gt(0)
    if policy == POLICIES[1]:
        eligible = eligible & ~data["probe_collision"] & ~data["probe_teleported"]
    if policy == POLICIES[2]:
        eligible = eligible & data["collisions"].eq(0) & data["teleports"].eq(0)
    return eligible


@st.cache_data(show_spinner=False)
def fixed_time_comparisons(context, policy):
    frame = context.copy()
    frame["analysis_eligible"] = eligible_mask(frame, policy)
    frame["valid_for_comparison"] = frame["analysis_eligible"]
    rows = records(frame)
    reference = {(r["demand_scale"], r["seed"], r["probe_id"]): r for r in rows if r["method"] == "fixed_time"}
    gains, flags, differences = [], [], []
    for row in rows:
        baseline = reference.get((row["demand_scale"], row["seed"], row["probe_id"]))
        paired = valid_pair(row, baseline)
        flags.append(paired)
        gains.append(100 * (baseline["travel_time_s"] - row["travel_time_s"]) / baseline["travel_time_s"] if paired else None)
        differences.append(row["travel_time_s"] - baseline["travel_time_s"] if paired else None)
    frame["paired_valid"] = flags
    frame["improvement_vs_fixed_percent"] = gains
    frame["difference_vs_fixed_s"] = differences
    return frame


@st.cache_data(show_spinner=False)
def all_method_pairs(selected):
    frame = selected.copy()
    frame["valid_for_comparison"] = frame["analysis_eligible"]
    result = pd.DataFrame(pairwise_rows(records(frame)))
    if result.empty:
        return pd.DataFrame(columns=PAIR_COLUMNS)
    reverse_names = {}
    for first, second in [("method_a", "method_b"), ("travel_time_a_s", "travel_time_b_s"), ("collisions_a", "collisions_b"), ("teleports_a", "teleports_b"), ("probe_teleported_a", "probe_teleported_b")]:
        reverse_names[first], reverse_names[second] = second, first
    reverse = result.rename(columns=reverse_names)
    result = pd.concat([result, reverse], ignore_index=True)
    paired = result["paired_valid"]
    result["difference_a_minus_b_s"] = (result["travel_time_a_s"] - result["travel_time_b_s"]).where(paired)
    result["improvement_a_vs_b_percent"] = (100 * (result["travel_time_b_s"] - result["travel_time_a_s"]) / result["travel_time_b_s"]).where(paired)
    return result


def journey_summary(selected):
    keys = ["method", "demand_scale"]
    counts = selected.groupby(keys).agg(planned_seeds=("seed", "nunique"), completed_journeys=("completed", "sum"))
    eligible = selected.loc[selected["analysis_eligible"]]
    means = eligible.groupby(keys).agg(
        eligible_seeds=("seed", "nunique"), mean_travel_time_s=("travel_time_s", "mean"),
        std_travel_time_s=("travel_time_s", "std"), median_travel_time_s=("travel_time_s", "median"),
        mean_waiting_time_s=("waiting_time_s", "mean"), std_waiting_time_s=("waiting_time_s", "std"),
        mean_depart_delay_s=("depart_delay_s", "mean"))
    result = counts.join(means).reset_index()
    result["eligible_seeds"] = result["eligible_seeds"].fillna(0).astype(int)
    return result


def display_methods(frame):
    result = frame.copy()
    for column in ["method", "method_a", "method_b"]:
        if column in result:
            result[column] = result[column].map(lambda method: LABELS.get(method, method))
    return result.rename(columns={
        "method": "Method", "method_a": "Method A", "method_b": "Reference B",
        "demand_scale": "Demand scale", "seed": "Seed", "probe_id": "Tracked vehicle",
        "vehicle_type": "Vehicle type", "route_variant": "Path", "run_id": "Run",
        "planned_seeds": "Planned seeds", "eligible_seeds": "Eligible seeds",
        "paired_seeds": "Matched seeds", "completed_journeys": "Completed journeys",
        "mean_travel_time_s": "Mean travel time (s)", "std_travel_time_s": "Travel time SD (s)",
        "median_travel_time_s": "Median travel time (s)",
        "mean_waiting_time_s": "Mean waiting time (s)", "std_waiting_time_s": "Waiting time SD (s)",
        "mean_depart_delay_s": "Mean departure delay (s)",
        "mean_difference_vs_fixed_s": "Difference from fixed-time (s)",
        "mean_improvement_percent": "Mean improvement (%)", "paired_valid": "Eligible pair",
        "travel_time_a_s": "Travel time A (s)", "travel_time_b_s": "Travel time B (s)",
        "difference_a_minus_b_s": "A minus B (s)", "improvement_a_vs_b_percent": "Improvement over B (%)",
        "executed_runs": "Executed runs", "all_four_arrived": "All-four arrivals",
        "tracked_journeys": "Tracked journeys", "arrived_journeys": "Arrived journeys",
        "all_four_percent": "All-four completion (%)", "completed": "Arrived",
        "censored": "Unfinished", "analysis_eligible": "Analysis eligible",
        "travel_time_s": "Travel time (s)", "waiting_time_s": "Waiting time (s)",
        "depart_delay_s": "Departure delay (s)", "time_loss_s": "Time loss (s)",
        "waiting_count": "Waiting episodes", "route_length_m": "Travelled distance (m)",
        "mean_speed_kmh": "Mean speed (km/h)",
    })


def mean_chart(summary, metric, deviation):
    frame = summary.loc[summary["eligible_seeds"].gt(0)].copy()
    frame["Method"] = frame["method"].map(LABELS)
    frame["Demand scale"] = frame["demand_scale"].map(lambda value: f"{value:g}")
    frame["plot_error"] = frame[deviation].fillna(0)
    figure = px.bar(frame, x="Method", y=metric, color="Demand scale", barmode="group", error_y="plot_error",
        category_orders={"Method": list(LABELS.values())}, color_discrete_sequence=["#147D92", "#D38A30", "#5667AD"],
        custom_data=["eligible_seeds", deviation], labels={metric: "Seconds"}, template="plotly_white")
    figure.update_traces(hovertemplate="%{x}<br>Mean %{y:.2f} s<br>Eligible seeds %{customdata[0]}<br>Sample SD %{customdata[1]:.2f} s<extra>%{fullData.name}</extra>")
    figure.update_layout(height=480, margin=dict(t=15, b=95), legend_title_text="Demand scale", xaxis_title=None)
    return figure


def main():
    st.set_page_config(page_title="Cong Hoa | Journey Analysis", page_icon="🚦", layout="wide")
    st.markdown("""<style>
    .block-container {max-width:1560px;padding-top:2rem;padding-bottom:3rem}
    h1 {letter-spacing:-.035em} [data-testid="stMetricValue"] {font-size:2rem}
    [data-testid="stSidebar"] {border-right:1px solid #dce5e9}
    </style>""", unsafe_allow_html=True)
    st.title("Cong Hoa Journey Analysis")
    st.write("Compare recorded signal-control experiments under matched demand and seed conditions.")
    experiments = {}
    if (CHECKPOINT / "dataset.csv").exists():
        experiments["Cong Hoa · 132-run checkpoint"] = CHECKPOINT
    for folder in sorted(BASE.iterdir()):
        if folder.is_dir() and all((folder / name).exists() for name in ["dataset.csv", "dataset_metadata.json", "plan.json"]):
            experiments[folder.name] = folder
    with st.sidebar:
        source = st.selectbox("Dataset", list(experiments), on_change=reset_filters, key="source")
    folder = experiments[source]
    names = ["dataset.csv", "plan.json", "dataset_metadata.json", "acceptance.json"]
    stamps = tuple((name, (folder / name).stat().st_mtime_ns) for name in names if (folder / name).exists())
    try:
        data, plan, metadata, audit = load_data(str(folder), stamps)
    except (ValueError, OSError, KeyError) as error:
        st.error(str(error))
        st.stop()
    if data.empty:
        st.info("This experiment has no exported journey records.")
        st.stop()
    methods_available = [method for method in LABELS if method in set(data["method"])]
    methods_available += sorted(set(data["method"]) - set(methods_available))
    scales_available = sorted(data["demand_scale"].unique().tolist())
    seeds_available = sorted(data["seed"].unique().tolist())
    actual_runs = data["run_id"].nunique()
    st.caption(f"{actual_runs:,} saved runs · {len(data):,} journey records · {len(methods_available)} methods · {len(scales_available)} demand levels · {len(seeds_available)} seeds")
    if audit.get("accepted") is not True:
        st.warning("Exploratory results. The source acceptance audit has outstanding checks. Arrival-based inclusion can retain event-affected runs.")
    if audit.get("actual_runs", actual_runs) != actual_runs:
        st.info("The saved audit covers an earlier export. Current coverage below is calculated directly from the selected CSV.")
    with st.sidebar:
        st.header("Journey filters")
        vehicle = st.selectbox("Vehicle", sorted(data["vehicle_type"].unique()), format_func=str.title, key="vehicle")
        route = st.selectbox("Route", sorted(data["route_variant"].unique(), reverse=True), format_func=lambda value: value.title() + " path", key="route")
        scales = st.multiselect("Demand scales", scales_available, default=scales_available, key="scales")
        methods = st.multiselect("Methods", methods_available, default=methods_available, format_func=lambda value: LABELS.get(value, value), key="methods")
        with st.expander("Seeds and inclusion policy"):
            seeds = st.multiselect("Seeds", seeds_available, default=seeds_available, key="seeds")
            policies = POLICIES if {"probe_collision", "probe_teleported"}.issubset(data.columns) else [POLICIES[0], POLICIES[2]]
            policy = st.selectbox("Inclusion policy", policies, key="policy")
        if st.button("Refresh data", width="stretch"):
            st.cache_data.clear()
            st.rerun()
        st.caption("One vehicle and path group at a time. Four tracked vehicles in a run share one seed.")
    if not methods or not scales or not seeds:
        st.info("Select at least one method, demand scale and seed.")
        st.stop()
    context = data.loc[data["vehicle_type"].eq(vehicle) & data["route_variant"].eq(route)
        & data["demand_scale"].isin(scales) & data["seed"].isin(seeds)].copy()
    analysed = fixed_time_comparisons(context, policy)
    selected = analysed.loc[analysed["method"].isin(methods)].copy()
    if selected.empty:
        st.info("No records match these filters.")
        st.stop()
    eligible = selected.loc[selected["analysis_eligible"]]
    summary = journey_summary(selected)
    run_frame = selected.drop_duplicates("run_id")
    cols = st.columns(4)
    cols[0].metric("Selected runs", f"{selected.run_id.nunique():,}")
    cols[1].metric("Tracked journeys", f"{len(selected):,}")
    cols[2].metric("Arrived journeys", f"{int(selected.completed.sum()):,} / {len(selected):,}")
    cols[3].metric("Eligible observations", f"{len(eligible):,}")
    st.caption(f"Current view · {vehicle.title()} · {route.title()} path · {policy}")
    overview, journeys, comparisons, details = st.tabs(["Completion", "Journey time", "Pairwise comparison", "Data and provenance"])
    with overview:
        st.subheader("Completion across demand levels")
        completion = run_frame.groupby(["method", "demand_scale"]).agg(
            executed_runs=("run_id", "size"), all_four_arrived=("all_four_arrived", "sum"))
        completion = completion.join(selected.groupby(["method", "demand_scale"]).agg(
            tracked_journeys=("probe_id", "size"), arrived_journeys=("completed", "sum"))).reset_index()
        completion["all_four_percent"] = 100 * completion["all_four_arrived"] / completion["executed_runs"]
        completion["Method"] = completion["method"].map(LABELS)
        completion["Demand scale"] = completion["demand_scale"].map(lambda value: f"{value:g}")
        figure = px.bar(completion, x="Method", y="all_four_percent", color="Demand scale", barmode="group",
            category_orders={"Method": [LABELS.get(m, m) for m in methods]},
            custom_data=["all_four_arrived", "executed_runs"], color_discrete_sequence=["#147D92", "#D38A30", "#5667AD"],
            labels={"all_four_percent": "Runs completing all four journeys (%)"}, template="plotly_white")
        figure.update_traces(hovertemplate="%{x}<br>%{customdata[0]} / %{customdata[1]} runs<extra>%{fullData.name}</extra>")
        figure.update_layout(height=430, yaxis_range=[0, 105], xaxis_title=None, margin=dict(t=15, b=95))
        st.plotly_chart(figure, width="stretch")
        st.dataframe(display_methods(completion.drop(columns=["Method", "Demand scale"])).round(2), hide_index=True, width="stretch")
        st.download_button("Download completion table", csv_bytes(completion.drop(columns=["Method", "Demand scale"])), "completion.csv", "text/csv")
        st.caption("Completion is measured before filtering by the inclusion policy. All-four completion uses all tracked vehicles in each original run.")
    with journeys:
        measure = st.radio("Measure", ["Travel time", "Waiting time"], horizontal=True)
        metric, deviation = ("mean_travel_time_s", "std_travel_time_s") if measure == "Travel time" else ("mean_waiting_time_s", "std_waiting_time_s")
        st.caption("Bars show eligible seed means. Error bars show sample standard deviations. Groups with n = 0 remain in the table. A single observation has no estimated standard deviation.")
        if eligible.empty:
            st.info("No observations satisfy this inclusion policy. Completion records remain available.")
        else:
            st.plotly_chart(mean_chart(summary, metric, deviation), width="stretch")
        st.dataframe(display_methods(summary).round(2), hide_index=True, width="stretch")
        st.download_button("Download journey summary", csv_bytes(summary), "journey_summary.csv", "text/csv")
        if st.toggle("Show individual seed results") and not eligible.empty:
            raw_metric = "travel_time_s" if measure == "Travel time" else "waiting_time_s"
            distribution = eligible.copy()
            distribution["Method"] = distribution["method"].map(LABELS)
            distribution["Demand scale"] = distribution["demand_scale"].map(lambda value: f"{value:g}")
            figure = px.box(distribution, x="Method", y=raw_metric, color="Demand scale", points="all",
                hover_data=["seed"], category_orders={"Method": list(LABELS.values())}, template="plotly_white",
                labels={raw_metric: "Seconds"})
            figure.update_layout(height=470, xaxis_title=None)
            st.plotly_chart(figure, width="stretch")
        st.caption("Travel time runs from actual departure to arrival. Departure delay is separate. Waiting time is part of the journey. Demand levels remain separate in every summary.")
        st.subheader("Matched improvements over fixed-time")
        paired = selected.loc[selected["paired_valid"] & selected["method"].ne("fixed_time")]
        paired_table = paired.groupby(["method", "demand_scale"]).agg(
            paired_seeds=("seed", "nunique"), mean_difference_vs_fixed_s=("difference_vs_fixed_s", "mean"),
            mean_improvement_percent=("improvement_vs_fixed_percent", "mean")).reset_index()
        if paired_table.empty:
            st.info("No eligible fixed-time pairs exist for this selection.")
        else:
            st.dataframe(display_methods(paired_table).round(2), hide_index=True, width="stretch")
            st.download_button("Download fixed-time comparisons", csv_bytes(paired_table), "fixed_time_comparisons.csv", "text/csv")
        st.caption("Percentage improvement is calculated within each matched seed and then averaged. Positive values indicate a shorter journey. Fixed-time references are available from the selected dataset even when hidden by the method filter.")
    with comparisons:
        st.subheader("Every method against every other method")
        st.caption("Rows are method A and columns are reference B. Values show mean travel time A − B in seconds. Blue favours A and red favours B. Each cell includes the matched seed count.")
        if len(methods) < 2:
            st.info("Select at least two methods to compare.")
        else:
            pair_scale = st.selectbox("Comparison demand scale", scales, key="pair_scale")
            pairs = all_method_pairs(selected.loc[selected["demand_scale"].eq(pair_scale)])
            if pairs.empty:
                st.info("No method pairs are available at this demand level.")
            else:
                pair_summary = pairs.groupby(["method_a", "method_b"]).agg(
                    paired_seeds=("paired_valid", "sum"), mean_difference_s=("difference_a_minus_b_s", "mean"),
                    std_difference_s=("difference_a_minus_b_s", "std"),
                    mean_improvement_percent=("improvement_a_vs_b_percent", "mean")).reset_index()
                matrix = pair_summary.pivot(index="method_a", columns="method_b", values="mean_difference_s").reindex(index=methods, columns=methods)
                counts = pair_summary.pivot(index="method_a", columns="method_b", values="paired_seeds").reindex(index=methods, columns=methods)
                labels = [LABELS.get(m, m) for m in methods]
                text = []
                for i in range(len(methods)):
                    values = []
                    for j in range(len(methods)):
                        value = matrix.iloc[i, j]
                        values.append("—" if i == j else ("n=0" if pd.isna(value) else f"{value:.1f}<br>n={int(counts.iloc[i, j])}"))
                    text.append(values)
                maximum = matrix.abs().max().max()
                limit = max(float(maximum), 1) if pd.notna(maximum) else 1
                figure = go.Figure(go.Heatmap(z=matrix.to_numpy(), x=labels, y=labels, zmin=-limit, zmax=limit,
                    colorscale=[[0, "#2166AC"], [0.5, "#F7F7F7"], [1, "#B2182B"]],
                    text=text, texttemplate="%{text}", textfont=dict(size=11), xgap=1, ygap=1,
                    colorbar=dict(title="A − B (s)"), hovertemplate="A %{y}<br>B %{x}<br>%{text}<extra></extra>"))
                for i, label_a in enumerate(labels):
                    for j, label_b in enumerate(labels):
                        if pd.isna(matrix.iloc[i, j]):
                            figure.add_annotation(x=label_b, y=label_a, text=text[i][j],
                                showarrow=False, font=dict(size=11, color="#52616B"))
                figure.update_layout(height=max(500, 45 * len(methods) + 170), plot_bgcolor="#E8ECEF", margin=dict(t=20, b=130, l=180),
                    xaxis=dict(title="Reference method B", tickangle=-40), yaxis=dict(title="Method A", autorange="reversed"))
                st.plotly_chart(figure, width="stretch")
                st.caption("Grey off-diagonal cells have n = 0. Different pairs may use different seed subsets. Diagonal cells are self-comparisons. Values are descriptive paired means.")
                pair_summary.insert(0, "demand_scale", pair_scale)
                st.download_button("Download all pair summaries", csv_bytes(pair_summary), "all_method_pairs.csv", "text/csv")
                st.subheader("Inspect one matched comparison")
                first, second = st.columns(2)
                with first:
                    method_a = st.selectbox("Method A", methods, index=methods.index("c_mp") if "c_mp" in methods else 0,
                        format_func=lambda value: LABELS.get(value, value), key="method_a")
                alternatives = [method for method in methods if method != method_a]
                with second:
                    method_b = st.selectbox("Reference method B", alternatives,
                        index=alternatives.index("fixed_time") if "fixed_time" in alternatives else 0,
                        format_func=lambda value: LABELS.get(value, value), key="method_b")
                detail = pairs.loc[pairs["method_a"].eq(method_a) & pairs["method_b"].eq(method_b)].sort_values("seed")
                st.dataframe(display_methods(detail[[column for column in PAIR_COLUMNS if column in detail]]).round(2), hide_index=True, width="stretch")
                st.download_button("Download seed-level comparison", csv_bytes(detail), "matched_seed_comparison.csv", "text/csv")
    with details:
        st.subheader("Journey records")
        include_ineligible = st.checkbox("Include unfinished and excluded observations", value=True)
        rows = selected if include_ineligible else eligible
        columns = [column for column in EXPORT_COLUMNS if column in rows]
        st.dataframe(display_methods(rows[columns]).round(2), hide_index=True, width="stretch")
        st.download_button("Download selected journey records", csv_bytes(rows[columns]), "selected_journeys.csv", "text/csv")
        with st.expander("Simulation events and exposure"):
            event_runs = run_frame["collisions"].gt(0) | run_frame["teleports"].gt(0)
            st.write(f"Selected runs with events: {int(event_runs.sum())} / {len(run_frame)}")
            st.write(f"Recorded collisions: {int(run_frame.collisions.sum())} · Recorded teleports: {int(run_frame.teleports.sum())}")
            st.caption("Run-level counts are counted once per run. Simulation durations vary because runs may stop after tracked arrivals. Raw counts have unequal exposure periods.")
            event_columns = [column for column in ["run_id", "actual_end_s", "collisions", "teleports", "stop_reason"] if column in run_frame]
            st.dataframe(run_frame[event_columns], hide_index=True, width="stretch")
        with st.expander("Demand inputs and model settings"):
            settings = [column for column in ["demand_scale", "map_requested_vph", "corridor_related_requested_vph", "corridor_requested_vph_forward", "corridor_requested_vph_reverse", "demand_duration_s", "simulation_step_s", "vehicle_movement_model", "lane_change_model", "motorcycle_share", "car_share", "truck_share", "bus_share"] if column in selected]
            st.dataframe(selected[settings].drop_duplicates().sort_values("demand_scale"), hide_index=True, width="stretch")
            st.caption("Hourly values are requested simulation inputs. Realised flow at a road cross-section requires a detector measurement. Missing legacy settings remain unavailable.")
        with st.expander("Source and analysis provenance"):
            st.code(str(folder.relative_to(ROOT)), language=None)
            st.write("Inclusion policy", policy)
            st.write("Source audit accepted", audit.get("accepted", "Unavailable"))
            st.write("Recorded engine versions", ", ".join(data.engine_version.dropna().astype(str).unique()))
            hashes = [column for column in ["run_id", "seed", "input_sha256", "network_sha256"] if column in selected]
            st.dataframe(selected[hashes].drop_duplicates(), hide_index=True, width="stretch")
            st.download_button("Download provenance", csv_bytes(selected[hashes].drop_duplicates()), "provenance.csv", "text/csv")
            st.caption("Bibliographic sources are maintained in the research documentation. Pairing checks input hashes, engine version, vehicle identity and path.")


if __name__ == "__main__":
    main()
