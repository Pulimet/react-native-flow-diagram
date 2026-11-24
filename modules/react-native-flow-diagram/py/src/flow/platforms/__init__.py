from platforms.android import AndroidPlatform
from platforms.base import Platform, PlatformError, run_command
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

    ready, problems = [], []
    for name, cls in PLATFORMS.items():
        candidate = cls(params, runner)
        try:
            candidate.validate()
            ready.append(candidate)
        except PlatformError as e:
            problems.append(f"  {name}: {e}")
    if len(ready) == 1:
        return ready[0]
    if not ready:
        raise PlatformError("No target is ready:\n" + "\n".join(problems))
    raise PlatformError("Several targets are ready (" + ", ".join(p.name for p in ready) +
                        "). Choose one with --platform.")
