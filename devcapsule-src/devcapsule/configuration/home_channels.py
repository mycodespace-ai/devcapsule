"""Adapt this launcher's embedded matrix to project-independent channels."""
from .trust import BASE_CHANNEL, Channel, base_channel, component_channel

def known_channels() -> dict[str, Channel]:
    """The channels of this launcher's embedded pins on this platform."""
    from devcapsule.platforms import Platform
    from devcapsule.resolution_matrix import MATRICES
    platform = Platform.current()
    result = {BASE_CHANNEL: base_channel()}
    for component_id, metadata in MATRICES[platform].component_pins().items():
        channel = component_channel(component_id, metadata, str(platform))
        if channel is not None:
            result[component_id] = channel
    return result
