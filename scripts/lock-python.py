"""Pin the installed transitive closure of the project's runtime + test dependencies only."""
from importlib.metadata import distribution
from pathlib import Path
from packaging.requirements import Requirement

pending = ['fastapi', 'uvicorn', 'httpx', 'pydantic', 'pytest']
versions = {}
while pending:
    name = pending.pop()
    dist = distribution(name)
    canonical = dist.metadata['Name'].lower().replace('_', '-')
    if canonical in versions:
        continue
    versions[canonical] = dist.version
    for requirement in dist.requires or []:
        req = Requirement(requirement)
        if req.marker is None or req.marker.evaluate({'extra': ''}):
            pending.append(req.name)
target = Path(__file__).resolve().parents[1] / 'services/api/requirements-lock.txt'
target.write_text('# Resolved installed dependency closure on Windows/Python 3.14.6\n' +
    '\n'.join(f'{name}=={version}' for name, version in sorted(versions.items())) + '\n', encoding='utf-8')
print(f'Pinned {len(versions)} project dependency distributions')
