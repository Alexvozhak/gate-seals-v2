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

     More on blueprints
     https://docs.vyperlang.org/en/v0.4.1/built-in-functions.html#chain-interaction

     More on EIP-5202
     https://eips.ethereum.org/EIPS/eip-5202
"""

event GateSealCreated:
    gate_seal: address


# First 3 bytes of the blueprint are the EIP-5202 header;
# The actual code of the contract starts at 4th byte
EIP5202_CODE_OFFSET: constant(uint256) = 3

# The maximum number of sealables is 8.
# GateSeals were originally designed to pause WithdrawalQueue and ValidatorExitBus,
# however, there is a non-zero chance that there might be more in the future, which
# is why we've opted to use a dynamic-size array.
MAX_SEALABLES: constant(uint256) = 8

# Constants from GateSeal for validation
SECONDS_PER_DAY: constant(uint256) = 60 * 60 * 24
MIN_SEAL_DURATION_SECONDS: constant(uint256) = SECONDS_PER_DAY * 6
MAX_SEAL_DURATION_SECONDS: constant(uint256) = SECONDS_PER_DAY * 21
MAX_EXPIRY_PERIOD_SECONDS: constant(uint256) = SECONDS_PER_DAY * 365 * 3
MAX_PROLONGATIONS: constant(uint256) = 5
MAX_PROLONGATION_DURATION_SECONDS: constant(uint256) = SECONDS_PER_DAY * 180

# Address of the blueprint that must be deployed beforehand
BLUEPRINT: immutable(address)

# @dev Error messages
BLUEPRINT_ZERO_ADDRESS: constant(String[32]) = "blueprint: zero address"

@deploy
def __init__(_blueprint: address):
    """
    @notice Initialize the factory with a blueprint contract
    @param _blueprint The address of the blueprint contract
    """
    assert _blueprint != empty(address), BLUEPRINT_ZERO_ADDRESS
    BLUEPRINT = _blueprint


@external
@view
def get_blueprint() -> address:
    return BLUEPRINT


@external
@view
def validate_gate_seal_params(
    _sealing_committee: address,
    _seal_duration_seconds: uint256,
    _sealables: DynArray[address, MAX_SEALABLES],
    _expiry_timestamp: uint256,
    _prolongations: uint256,
    _prolongation_duration_seconds: uint256
) -> bool:
    """
    @notice Validate GateSeal parameters before deployment
    @dev This function performs the same validation as GateSeal constructor
    @return True if all parameters are valid
    """
    # Validate sealing committee
    if _sealing_committee == empty(address):
        return False
        
    # Validate seal duration
    if _seal_duration_seconds < MIN_SEAL_DURATION_SECONDS:
        return False
    if _seal_duration_seconds > MAX_SEAL_DURATION_SECONDS:
        return False
        
    # Validate sealables
    if len(_sealables) == 0:
        return False
    if len(_sealables) > MAX_SEALABLES:
        return False
        
    # Check for zero addresses and duplicates in sealables
    for sealable: address in _sealables:
        if sealable == empty(address):
            return False
            
    # Check for duplicates
    unique: DynArray[address, MAX_SEALABLES] = []
    for sealable: address in _sealables:
        if sealable in unique:
            return False
        unique.append(sealable)
        
    # Validate expiry timestamp
    if _expiry_timestamp <= block.timestamp:
        return False
    if _expiry_timestamp > block.timestamp + MAX_EXPIRY_PERIOD_SECONDS:
        return False
        
    # Validate prolongations
    if _prolongations > MAX_PROLONGATIONS:
        return False
        
    # Validate prolongation duration
    if _prolongations == 0:
        if _prolongation_duration_seconds != 0:
            return False
    else:
        if _prolongation_duration_seconds == 0:
            return False
        if _prolongation_duration_seconds > MAX_PROLONGATION_DURATION_SECONDS:
            return False
            
    return True


@external
def create_gate_seal(
    _sealing_committee: address,
    _seal_duration_seconds: uint256,
    _sealables: DynArray[address, MAX_SEALABLES],
    _expiry_timestamp: uint256,
    _prolongations: uint256,
    _prolongation_duration_seconds: uint256
):
    """
    @notice Create a new GateSeal.
    @dev    All of the security checks are done inside the GateSeal constructor.
    @param _sealing_committee address of the multisig committee
    @param _seal_duration_seconds duration of the seal in seconds
    @param _sealables addresses of pausable contracts
    @param _expiry_timestamp unix timestamp when the GateSeal will naturally expire
    @param _prolongations number of prolongations
    @param _prolongation_duration_seconds duration of the prolongation in seconds
    """
    gate_seal: address = create_from_blueprint(
        BLUEPRINT,
        _sealing_committee,
        _seal_duration_seconds,
        _sealables,
        _expiry_timestamp,
        _prolongations,
        _prolongation_duration_seconds,
        code_offset=EIP5202_CODE_OFFSET,
    )

    log GateSealCreated(gate_seal=gate_seal)