"""Apply the surveyed 18E programme and centre-lane turn restrictions.

Run from the project root with .venv/Scripts/python.exe scripts/configure_18e.py.
Netconvert rebuilds the affected junction. External road geometry is verified
before the junction is transferred into the project network.
"""

from pathlib import Path
import copy
import gzip
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from traffic_study import run_fixed_time as baseline


def connection_patch(raw):
    patch = ET.Element("connections")
    for connection in raw.findall("connection"):
        if connection.get("tl") != baseline.TLS_18E:
            continue
        attributes = {key: connection.get(key) for key in ("from", "to", "fromLane", "toLane")}
        if connection.get("from") in baseline.CENTER_18E_EDGES and connection.get("dir") in (
            "l",
            "L",
            "t",
            "T",
        ):
            ET.SubElement(patch, "delete", attributes)
        # Include every connection of this approach to preserve its other turns.
        if connection.get("from") == "1424752055#1":
            if connection.get("to") == "1094755428#0":
                attributes["allow"] = "motorcycle moped bicycle scooter"
            ET.SubElement(patch, "connection", attributes)
    return patch


def belongs_to_18e(element):
    prefix = ":" + baseline.TLS_18E + "_"
    if element.tag in ("edge", "junction"):
        return element.get("id") == baseline.TLS_18E or element.get("id", "").startswith(prefix)
    if element.tag == "tlLogic":
        return element.get("id") == baseline.TLS_18E
    if element.tag == "connection":
        return (
            element.get("tl") == baseline.TLS_18E
            or element.get("from", "").startswith(prefix)
            or element.get("to", "").startswith(prefix)
        )
    return False


def configure():
    original_bytes = baseline.SOURCE_NET.read_bytes()
    original = ET.fromstring(gzip.decompress(original_bytes))
    patch = connection_patch(original)
    ROOT.joinpath("tmp").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="configure_18e_", dir=ROOT / "tmp") as folder:
        folder = Path(folder)
        patch_file = folder / "18e.con.xml"
        converted_file = folder / "network.net.xml.gz"
        ET.ElementTree(patch).write(patch_file, encoding="utf-8", xml_declaration=True)
        netconvert = shutil.which("netconvert")
        if not netconvert:
            raise RuntimeError("Cannot find netconvert on PATH.")
        result = subprocess.run(
            [
                netconvert,
                "--sumo-net-file",
                str(baseline.SOURCE_NET),
                "--connection-files",
                str(patch_file),
                "--output-file",
                str(converted_file),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
        converted = ET.fromstring(gzip.decompress(converted_file.read_bytes()))

    old_edges = {
        e.get("id"): e for e in original.findall("edge") if e.get("function") != "internal"
    }
    new_edges = {
        e.get("id"): e for e in converted.findall("edge") if e.get("function") != "internal"
    }
    affected = {
        c.get(key)
        for c in original.findall("connection")
        if c.get("tl") == baseline.TLS_18E
        for key in ("from", "to")
    }
    for edge_id in affected:
        old_lanes = old_edges[edge_id].findall("lane")
        new_lanes = new_edges[edge_id].findall("lane")
        if len(old_lanes) != len(new_lanes) or any(
            a.attrib != b.attrib for a, b in zip(old_lanes, new_lanes)
        ):
            raise RuntimeError(f"External lane geometry or permissions changed at {edge_id}.")

    for element in list(original):
        if belongs_to_18e(element):
            original.remove(element)
    for element in converted:
        if belongs_to_18e(element):
            original.append(copy.deepcopy(element))
    program = next(t for t in original.findall("tlLogic") if t.get("id") == baseline.TLS_18E)
    phases, audit = baseline.build_18e_phases(original, program)
    for phase in list(program.findall("phase")):
        program.remove(phase)
    program.set("type", "static")
    for duration, state in phases:
        ET.SubElement(program, "phase", duration=f"{duration:g}", state=state)
    if baseline.SOURCE_NET.read_bytes() != original_bytes:
        raise RuntimeError(
            "The source network changed while rebuilding 18E. Save NetEdit and retry."
        )
    temporary = baseline.SOURCE_NET.with_suffix(".tmp")
    temporary.write_bytes(
        gzip.compress(ET.tostring(original, encoding="utf-8", xml_declaration=True), mtime=0)
    )
    temporary.replace(baseline.SOURCE_NET)
    print("Configured 18E:", phases)
    print("Timing:", audit[-1])


if __name__ == "__main__":
    configure()
