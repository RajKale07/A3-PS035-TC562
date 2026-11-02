"""
NEXUS — WSL2 Mininet Emulation Bridge
Translates database network topologies into executable Mininet scripts
and triggers hardware/software-in-the-loop emulation inside WSL2 Ubuntu.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.config import settings


@dataclass
class EmulationReport:
    """Report produced by executing real packet traffic through WSL2 Mininet."""

    topology_name: str
    packet_loss_pct: float
    hosts_tested: int
    switches_deployed: int
    links_deployed: int
    duration_ms: float
    output_log: str
    success: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "topology_name": self.topology_name,
            "packet_loss_pct": self.packet_loss_pct,
            "hosts_tested": self.hosts_tested,
            "switches_deployed": self.switches_deployed,
            "links_deployed": self.links_deployed,
            "duration_ms": self.duration_ms,
            "output_log": self.output_log,
            "success": self.success,
        }


def generate_mininet_script(
    nodes: list[dict[str, Any]],
    links: list[dict[str, Any]],
    failed_nodes: list[str] | None = None,
) -> str:
    """
    Generate an autonomous Python script for execution inside WSL2.
    Uses TCLink to emulate latency, bandwidth, and packet loss.
    """
    failed = set(failed_nodes or [])

    # Filter out failed nodes and incident links
    surviving_nodes = [n for n in nodes if str(n["id"]) not in failed]
    surviving_ids = {str(n["id"]) for n in surviving_nodes}
    surviving_links = [
        lnk for lnk in links
        if str(lnk["source"]) in surviving_ids and str(lnk["target"]) in surviving_ids
    ]

    script = f'''#!/usr/bin/env python3
import sys
import json
import time
from mininet.net import Mininet
from mininet.node import Controller, OVSSwitch
from mininet.link import TCLink
from mininet.log import setLogLevel

setLogLevel('info')

def run():
    net = Mininet(controller=Controller, switch=OVSSwitch, link=TCLink, waitConnected=True)
    c0 = net.addController('c0')

    # Deploy network nodes as virtual switches with an attached local test host
    hosts = {{}}
    switches = {{}}
'''

    for n in surviving_nodes:
        nid = str(n["id"])
        script += f'''
    s{nid} = net.addSwitch('s{nid}')
    h{nid} = net.addHost('h{nid}', ip='10.0.0.{int(nid)+1}/24')
    net.addLink(h{nid}, s{nid})
    hosts['{nid}'] = h{nid}
    switches['{nid}'] = s{nid}
'''

    for idx, lnk in enumerate(surviving_links):
        src = str(lnk["source"])
        tgt = str(lnk["target"])
        bw = lnk.get("bandwidth_mbps", 100)
        delay = f"{max(0.1, lnk.get('latency_ms', 1.0)):.1f}ms"
        script += f'''
    net.addLink(switches['{src}'], switches['{tgt}'], bw={bw}, delay='{delay}')
'''

    script += '''
    net.start()
    # Allow OpenFlow controller discovery
    time.sleep(1.5)

    # Execute reachability ping test across all deployed hosts
    loss = net.pingAll()
    net.stop()

    result = {
        "packet_loss_pct": loss,
        "hosts_count": len(hosts),
        "switches_count": len(switches),
        "links_count": len(switches) - 1
    }
    print("---NEXUS_MININET_JSON_START---")
    print(json.dumps(result))
    print("---NEXUS_MININET_JSON_END---")

if __name__ == '__main__':
    run()
'''
    return script


def run_mininet_emulation(
    topology_name: str,
    nodes: list[dict[str, Any]],
    links: list[dict[str, Any]],
    failed_nodes: list[str] | None = None,
) -> EmulationReport:
    """Execute the generated script inside WSL2 via `wsl -d <distro> -u root`."""
    t0 = time.perf_counter()
    script_content = generate_mininet_script(nodes, links, failed_nodes)

    distro = settings.wsl_distro

    # Write script to temporary file on D:
    temp_dir = Path("D:/AIORI/.temp_sim")
    temp_dir.mkdir(exist_ok=True)
    temp_script = temp_dir / f"mn_{int(time.time())}.py"
    temp_script.write_text(script_content, encoding="utf-8")

    # Convert Windows path to WSL path (e.g. /mnt/d/AIORI/...)
    wsl_script_path = f"/mnt/d/AIORI/.temp_sim/{temp_script.name}"

    cmd = [
        "wsl",
        "-d",
        distro,
        "-u",
        "root",
        "bash",
        "-c",
        f"python3 {wsl_script_path} 2>&1"
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=35,
        )
        stdout = proc.stdout
        duration_ms = round((time.perf_counter() - t0) * 1000, 2)

        # Parse JSON output from log
        packet_loss = 0.0
        hosts_count = len(nodes)
        switches_count = len(nodes)

        if "---NEXUS_MININET_JSON_START---" in stdout:
            json_part = stdout.split("---NEXUS_MININET_JSON_START---")[1].split("---NEXUS_MININET_JSON_END---")[0]
            data = json.loads(json_part.strip())
            packet_loss = float(data.get("packet_loss_pct", 0.0))
            hosts_count = data.get("hosts_count", len(nodes))
            switches_count = data.get("switches_count", len(nodes))

        return EmulationReport(
            topology_name=topology_name,
            packet_loss_pct=packet_loss,
            hosts_tested=hosts_count,
            switches_deployed=switches_count,
            links_deployed=len(links),
            duration_ms=duration_ms,
            output_log=stdout[-500:] if len(stdout) > 500 else stdout,
            success=proc.returncode == 0,
        )
    except Exception as e:
        return EmulationReport(
            topology_name=topology_name,
            packet_loss_pct=100.0,
            hosts_tested=len(nodes),
            switches_deployed=len(nodes),
            links_deployed=len(links),
            duration_ms=round((time.perf_counter() - t0) * 1000, 2),
            output_log=f"Execution error: {str(e)}",
            success=False,
        )
    finally:
        # Clean up script
        if temp_script.exists():
            temp_script.unlink(missing_ok=True)
