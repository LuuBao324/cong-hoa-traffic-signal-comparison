"""Shared vehicle dimensions and physical road compatibility."""

VEHICLE_TYPES = {
    "motorcycle": ("motorcycle", "1.8", "0.8", "1.0"),
    "car": ("passenger", "4.5", "1.8", "2.0"),
    "truck": ("truck", "8.0", "2.4", "2.5"),
    "bus": ("bus", "12.0", "2.5", "2.5"),
}
VEHICLE_WIDTHS = {spec[0]: float(spec[2]) for spec in VEHICLE_TYPES.values()}


def allows_lane(lane, vehicle_class):
    """Require permission and sufficient width for a single-file vehicle."""
    required = VEHICLE_WIDTHS[vehicle_class]
    return lane.allows(vehicle_class) and lane.getWidth() + 1e-6 >= required


def allows_vehicle(edge, vehicle_class):
    """Require one permitted lane wide enough for the lane-based vehicle body."""
    return any(allows_lane(lane, vehicle_class) for lane in edge.getLanes())
