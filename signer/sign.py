from SignerPy import sign as signer_sign

def sign(params: str, payload: str or None = None, sec_device_id: str = '', cookie: str or None = None, aid: int = 1233, license_id: int = 1611921764, sdk_version_str: str = 'v05.00.03-ov-android', sdk_version: int = 167773760, platform: int = 0, unix: float = None, version: int = 8404):
    """
    Generate TikTok API signatures using SignerPy library
    
    Args:
        params: URL query parameters string
        payload: Request body/payload
        sec_device_id: Device security token
        cookie: Cookie string
        aid: App ID (default: 1233)
        license_id: License ID
        sdk_version_str: SDK version string
        sdk_version: SDK version integer
        platform: Platform identifier
        unix: Unix timestamp (auto-generated if None)
        version: Gorgon version (8404, 8402, or 4404)
    
    Returns:
        Dictionary containing signature headers (x-gorgon, x-argus, x-ladon, x-khronos, etc.)
    """
    signature = signer_sign(params=params, payload=payload, version=8404)
    
    return signature
