# @version 0.4.1

"""
@title GateSealFactory
@author mymphe
@notice A factory contract for GateSeals
@dev This contract is meant to simplify the GateSeal deploy.
     The factory features a single write function that deploys
     a new GateSeal with the given parameters based
     on the blueprint provided at the factory construction
     using `create_from_blueprint`.

     The blueprint must follow EIP-5202 and, thus, is not a
     functioning GateSeal itself but only its deployment code.

     Updated to support new GateSeal logic with lifetime duration,
     prolongations, and activation windows.

     More on blueprints
     https://docs.vyperlang.org/en/v0.4.1/built-in-functions.html#chain-interaction

     More on EIP-5202
     https://eips.ethereum.org/EIPS/eip-5202
"""

event GateSealCreated:
    gate_seal: address

# Constants for validation (must match GateSeal.vy)
MAX_SEALABLES: constant(uint256) = 8
MIN_SEAL_DURATION_SECONDS: constant(uint256) = 6 * 24 * 60 * 60    # 6 days
MAX_SEAL_DURATION_SECONDS: constant(uint256) = 21 * 24 * 60 * 60   # 21 days
MIN_LIFETIME_DURATION_SECONDS: constant(uint256) = 30 * 24 * 60 * 60  # 1 month
MAX_LIFETIME_DURATION_SECONDS: constant(uint256) = 365 * 24 * 60 * 60  # 1 year
MAX_PROLONGATIONS: constant(uint256) = 5
MIN_PROLONGATION_ACTIVATION_WINDOW_SECONDS: constant(uint256) = 7 * 24 * 60 * 60    # 1 week
MAX_PROLONGATION_ACTIVATION_WINDOW_SECONDS: constant(uint256) = 30 * 24 * 60 * 60   # 1 month

# First 3 bytes of the blueprint are the EIP-5202 header;
# The actual code of the contract starts at 4th byte.
# https://eips.ethereum.org/EIPS/eip-5202
BLUEPRINT_HEADER_SIZE: constant(uint256) = 3
BLUEPRINT: immutable(address)

@deploy
def __init__(_blueprint: address):
    """
    @notice initializes the factory with the GateSeal blueprint
    @param _blueprint the address of the GateSeal blueprint
    """
    assert _blueprint != empty(address), "blueprint: zero address"
    
    # Ensure blueprint has valid EIP-5202 header
    header: Bytes[3] = slice(_blueprint.code, 0, BLUEPRINT_HEADER_SIZE)
    assert len(header) == BLUEPRINT_HEADER_SIZE, "blueprint: invalid length"
    expected_header: Bytes[3] = b"\xFE\x71\x00"
    assert header == expected_header, "blueprint: invalid EIP-5202 header"
    
    BLUEPRINT = _blueprint

@external
def create_gate_seal(
    _sealing_committee: address,
    _seal_duration_seconds: uint256,
    _sealables: DynArray[address, MAX_SEALABLES],
    _lifetime_duration_seconds: uint256,
    _max_prolongations: uint256,
    _prolongation_activation_window_seconds: uint256,
) -> address:
    """
    @notice creates a new GateSeal with the specified parameters
    @param _sealing_committee the address that can seal the contracts and prolong lifetime
    @param _seal_duration_seconds the duration for which the sealables will be paused (6-21 days)
    @param _sealables the addresses of the contracts that can be sealed (1-8 contracts)
    @param _lifetime_duration_seconds the duration of each lifetime period - initial and each prolongation (1 month - 1 year)
    @param _max_prolongations maximum number of lifetime prolongations allowed (0-5)
    @param _prolongation_activation_window_seconds time window before expiry when prolongations can be activated (1 week - 1 month)
    @return the address of the newly created GateSeal
    """
    # Pre-validate all parameters to provide clear error messages
    assert self._validate_gate_seal_params(
        _sealing_committee,
        _seal_duration_seconds,
        _sealables,
        _lifetime_duration_seconds,
        _max_prolongations,
        _prolongation_activation_window_seconds
    ), "invalid parameters"
    
    gate_seal: address = create_from_blueprint(
        BLUEPRINT,
        _sealing_committee,
        _seal_duration_seconds,
        _sealables,
        _lifetime_duration_seconds,
        _max_prolongations,
        _prolongation_activation_window_seconds,
        salt=keccak256(
            concat(
                convert(_sealing_committee, bytes32),
                convert(_seal_duration_seconds, bytes32),
                convert(block.timestamp, bytes32)
            )
        )
    )
    
    log GateSealCreated(gate_seal=gate_seal)
    return gate_seal

@external
@view
def validate_gate_seal_params(
    _sealing_committee: address,
    _seal_duration_seconds: uint256,
    _sealables: DynArray[address, MAX_SEALABLES],
    _lifetime_duration_seconds: uint256,
    _max_prolongations: uint256,
    _prolongation_activation_window_seconds: uint256,
) -> bool:
    """
    @notice validates GateSeal parameters before deployment (external view)
    @dev performs the same validations as GateSeal constructor
    @return true if all parameters are valid, false otherwise
    """
    return self._validate_gate_seal_params(
        _sealing_committee,
        _seal_duration_seconds,
        _sealables,
        _lifetime_duration_seconds,
        _max_prolongations,
        _prolongation_activation_window_seconds
    )

@internal
@view
def _validate_gate_seal_params(
    _sealing_committee: address,
    _seal_duration_seconds: uint256,
    _sealables: DynArray[address, MAX_SEALABLES],
    _lifetime_duration_seconds: uint256,
    _max_prolongations: uint256,
    _prolongation_activation_window_seconds: uint256,
) -> bool:
    """
    @notice validates GateSeal parameters before deployment (internal)
    @dev performs the same validations as GateSeal constructor
    @return true if all parameters are valid, false otherwise
    """
    # Basic validations
    if _sealing_committee == empty(address):
        return False
    if len(_sealables) < 1 or len(_sealables) > MAX_SEALABLES:
        return False
    if self._has_duplicates(_sealables):
        return False
    
    # Validate seal duration
    if _seal_duration_seconds < MIN_SEAL_DURATION_SECONDS or _seal_duration_seconds > MAX_SEAL_DURATION_SECONDS:
        return False
    
    # Validate lifetime duration
    if _lifetime_duration_seconds < MIN_LIFETIME_DURATION_SECONDS or _lifetime_duration_seconds > MAX_LIFETIME_DURATION_SECONDS:
        return False
    
    # Validate prolongations
    if _max_prolongations > MAX_PROLONGATIONS:
        return False
    
    # Validate prolongation activation window
    if _prolongation_activation_window_seconds < MIN_PROLONGATION_ACTIVATION_WINDOW_SECONDS:
        return False
    if _prolongation_activation_window_seconds > MAX_PROLONGATION_ACTIVATION_WINDOW_SECONDS:
        return False
    if _prolongation_activation_window_seconds > _lifetime_duration_seconds:
        return False
    
    # Check for zero addresses in sealables
    for sealable: address in _sealables:
        if sealable == empty(address):
            return False
    
    return True

@external
@view
def get_blueprint() -> address:
    """
    @notice returns the blueprint address
    @return the address of the GateSeal blueprint
    """
    return BLUEPRINT

@internal
@view
def _has_duplicates(_sealables: DynArray[address, MAX_SEALABLES]) -> bool:
    """
    @notice checks if there are duplicate addresses in sealables list
    @param _sealables the list of sealable addresses to check
    @return true if duplicates found, false otherwise
    """
    for i: uint256 in range(MAX_SEALABLES):
        if i >= len(_sealables):
            break
        for j: uint256 in range(MAX_SEALABLES):
            if j >= len(_sealables) or j <= i:
                continue
            if _sealables[i] == _sealables[j]:
                return True
    return False