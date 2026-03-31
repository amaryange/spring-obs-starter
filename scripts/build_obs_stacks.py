"""
Generate all pre-built obs-stack variants into dist/obs-stacks/.
Run from the project root:  python scripts/build_obs_stacks.py
"""
import shutil
import sys
from pathlib import Path

# Allow running from the project root without installing the package
sys.path.insert(0, str(Path(__file__).parent.parent))

from cli.generator import ProjectGenerator
from cli.models import MetricsBackend, ProjectConfig, TraceBackend

VARIANTS = [
    (TraceBackend.TEMPO,   MetricsBackend.PROMETHEUS),
    (TraceBackend.TEMPO,   MetricsBackend.MIMIR),
    (TraceBackend.JAEGER,  MetricsBackend.PROMETHEUS),
    (TraceBackend.ZIPKIN,  MetricsBackend.PROMETHEUS),
]

dist = Path("dist") / "obs-stacks"
dist.mkdir(parents=True, exist_ok=True)

generator = ProjectGenerator()

for trace, metrics in VARIANTS:
    name = f"obs-stack-{trace.value}-{metrics.value}"
    output_dir = dist / name

    if output_dir.exists():
        shutil.rmtree(output_dir)

    config = ProjectConfig.for_obs_stack(trace_backend=trace, metrics_backend=metrics)
    generator.generate_obs_stack(config, output_dir)

    archive = shutil.make_archive(str(dist / name), "gztar", dist, name)
    shutil.rmtree(output_dir)

    print(f"✔ {Path(archive).name}")

print(f"\nAll archives written to {dist}/")