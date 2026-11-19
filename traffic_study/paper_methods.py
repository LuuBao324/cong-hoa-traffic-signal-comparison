"""Paper eligibility registry. A baseline is never counted as a 2023+ algorithm."""

PAPERS = {
    "switching_loss_mp": dict(
        year=2025,
        title="Max-Pressure Controller for Traffic Networks Considering the Phase Switching Loss",
        url="https://doi.org/10.3390/su17104492",
        section="Eq.5,7,8",
        family="pressure",
    ),
    "c_mp": dict(
        year=2025,
        title="C-MP: A decentralized adaptive-coordinated traffic signal control using the Max Pressure framework",
        url="https://doi.org/10.1016/j.trb.2025.103308",
        section="Eq.6–8",
        family="pressure",
    ),
    "td_mp_2023": dict(
        year=2023,
        title="Total-delay-based Max Pressure: A Max Pressure Algorithm Considering Delay Equity",
        url="https://doi.org/10.1177/03611981221147051",
        section="Eq.7, downstream delay over preceding decision window",
        family="pressure",
    ),
    "cv_mp_2025": dict(
        year=2025,
        title="CV-MP: Max-Pressure Control in Heterogeneously Distributed and Partially Connected Vehicle Environments",
        url="https://arxiv.org/abs/2505.05258",
        section="Eq.8–9, fully connected observation scenario",
        family="pressure",
        publication_type="preprint",
    ),
    "queue_responsive_2026": dict(
        year=2026,
        title="Queue-Responsive Adaptive Signal Control vs. Webster Optimization: A Multi-Criteria Simulation Assessment at a Signalized Intersection",
        url="https://doi.org/10.3390/futuretransp6020092",
        section="Section 2.4.3, Algorithm 1; queue-responsive branch ONLY",
        family="queue_responsive",
    ),
    "cn_mp_2024": dict(
        year=2024,
        title="A Modified Pressure Model for Max-Pressure Traffic Signal Control",
        url="https://doi.org/10.23919/ECC64448.2024.10590907",
        full_text="https://www.paperhost.org/proceedings/controls/ECC24/files/0414.pdf",
        section="CN-MP, Eq.4/6; Section IV first experiment",
        family="lane_normalized_pressure",
        variant="CN-MP",
    ),
    "wncn_mp_2024": dict(
        year=2024,
        title="A Modified Pressure Model for Max-Pressure Traffic Signal Control",
        url="https://doi.org/10.23919/ECC64448.2024.10590907",
        full_text="https://www.paperhost.org/proceedings/controls/ECC24/files/0414.pdf",
        section="WNCN-MP, Eq.4/7; Section IV first experiment",
        family="lane_normalized_pressure",
        variant="WNCN-MP",
    ),
    "wstar_ncn_mp_2024": dict(
        year=2024,
        title="A Modified Pressure Model for Max-Pressure Traffic Signal Control",
        url="https://doi.org/10.23919/ECC64448.2024.10590907",
        full_text="https://www.paperhost.org/proceedings/controls/ECC24/files/0414.pdf",
        section="W*NCN-MP, Eq.8/7; Section IV capacity-aware experiment",
        family="lane_normalized_pressure",
        variant="W*NCN-MP",
    ),
    "wstar_cn_mp_2024": dict(
        year=2024,
        title="A Modified Pressure Model for Max-Pressure Traffic Signal Control",
        url="https://doi.org/10.23919/ECC64448.2024.10590907",
        full_text="https://www.paperhost.org/proceedings/controls/ECC24/files/0414.pdf",
        section="W*CN-MP, Eq.8/6; Section IV capacity-aware experiment",
        family="lane_normalized_pressure",
        variant="W*CN-MP",
    ),
    "coordinated_auction_2024": dict(
        year=2024,
        title="Exploiting Traffic Light Coordination and Auctions for Intersection and Emergency Vehicle Management in a Smart City Mixed Scenario",
        url="https://doi.org/10.3390/s24072036",
        section="Section 3, Algorithms 1–3; coordinated auctions with bid propagation",
        family="auction",
    ),
}
for paper in PAPERS.values():
    paper["requires_training"] = False
    paper["uses_rl"] = False
    paper["algorithm_status"] = "published_nonlearning_model_with_documented_SUMO_adapter"
RESEARCH_METHODS = tuple(PAPERS)
METHODS = ("fixed_time",) + RESEARCH_METHODS


def validate_registry():
    if len(RESEARCH_METHODS) != 10:
        raise ValueError("Require ten nonlearning research methods")
    if any(p["requires_training"] or p["uses_rl"] for p in PAPERS.values()):
        raise ValueError("Training and RL are excluded from this experiment")
    if any(p["year"] < 2023 for p in PAPERS.values()):
        raise ValueError("Only papers from 2023 onward are eligible")


validate_registry()
