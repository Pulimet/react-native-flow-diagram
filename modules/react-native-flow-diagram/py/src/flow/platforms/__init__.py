from platforms.android import AndroidPlatform
from platforms.base import AmbiguousTarget, Platform, PlatformError, run_command
from platforms.ios_device import IosDevicePlatform
from platforms.ios_simulator import IosSimulatorPlatform

PLATFORMS = {
    "android": AndroidPlatform,
    "ios_simulator": IosSimulatorPlatform,
    "ios_device": IosDevicePlatform,
}


def create_platform(params, runner=run_command) -> Platform:
    """Return a validated platform. 'auto' picks the only target that is ready, else asks for an explicit one."""
    if params.platform != "auto":
        platform = PLATFORMS[params.platform](params, runner)
        platform.validate()
        return platform

    ready, ambiguous, problems = [], [], []
    for name, cls in PLATFORMS.items():
        candidate = cls(params, runner)
        try:
            candidate.validate()
            ready.append(candidate)
        except AmbiguousTarget as e:
            ambiguous.append((name, e))
        except PlatformError as e:
            problems.append(f"  {name}: {e}")
    if len(ready) == 1 and not ambiguous:
        return ready[0]
    if not ready and not ambiguous:
        raise PlatformError("No target is ready:\n" + "\n".join(problems))
    lines = ["Several targets are ready, choose one:"]
    for candidate in ready:
        lines.append(f"  {candidate.name} (pass --platform {candidate.name})")
    for name, e in ambiguous:
        lines.append(f"  {name} ({', '.join(e.choices)}; pass --platform {name} {e.flag} <id>)")
    if problems:
        lines.append("Not ready:")
        lines.extend(problems)
    raise PlatformError("\n".join(lines))
