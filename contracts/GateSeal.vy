# @version 0.4.1

"""
@title GateSeal
@author mymphe
@notice A one-time panic button for pausable contracts
@dev GateSeal is an one-time immediate emergency pause for pausable contracts.
     It must be operated by a multisig committee, though the code does not
     perform any such checks. Bypassing the DAO vote, GateSeal pauses 
     the contract(s) immediately for a set duration, e.g. one week, which gives
     the DAO the time to analyze the situation, decide on the course of action,
     hold a vote, implement fixes, etc. GateSeal can only be used once.
     GateSeal assumes that they have the permission to pause the contracts.

     GateSeals have a lifetime duration (1 month to 1 year) and can be extended
     up to 5 times. Each prolongation period equals the lifetime duration.
     Prolongations can only be activated within a specified activation window
     (1 week to 1 month) before the current expiry timestamp.

     GateSeals are only a temporary solution and will be deprecated in the future,
     as it is undesirable for the protocol to rely on a multisig. This was 
     introduced as an intermediate solution between having and not having an
     Emergency pause that bypasses the DAO vote.
"""

interface IPausable:
    def pauseFor(_duration: uint256): nonpayable
    def isPaused() -> bool: view

interface IPausableUntil:
    def pauseFor(_duration: uint256): nonpayable
    def isPaused() -> bool: view

MAX_SEALABLES: constant(uint256) = 8

# New constants for the updated logic
MIN_LIFETIME_DURATION_SECONDS: constant(uint256) = 30 * 24 * 60 * 60  # 1 month
MAX_LIFETIME_DURATION_SECONDS: constant(uint256) = 365 * 24 * 60 * 60  # 1 year
MAX_PROLONGATIONS: constant(uint256) = 5
MIN_PROLONGATION_WINDOW_SECONDS: constant(uint256) = 7 * 24 * 60 * 60    # 1 week
MAX_PROLONGATION_WINDOW_SECONDS: constant(uint256) = 30 * 24 * 60 * 60   # 1 month
MIN_SEAL_DURATION_SECONDS: constant(uint256) = 6 * 24 * 60 * 60  # 6 days
MAX_SEAL_DURATION_SECONDS: constant(uint256) = 21 * 24 * 60 * 60  # 21 days

MAX_EXPIRY_PERIOD_DAYS: constant(uint256) = 365 * 3  # 3 years
MAX_EXPIRY_PERIOD_SECONDS: constant(uint256) = MAX_EXPIRY_PERIOD_DAYS * 24 * 60 * 60

event Sealed:
    sealed_by: indexed(address)
    sealables: DynArray[address, MAX_SEALABLES]
    sealed_for: uint256

event LifetimeProlonged:
    prolonged_by: indexed(address)
    old_expiry: uint256
    new_expiry: uint256
    prolongations_remaining: uint256

# sealing committee that has the power to seal and prolong lifetime
sealing_committee: public(address)

# the sealables that can be sealed
sealables: public(DynArray[address, MAX_SEALABLES])

# the duration for which the sealables will be paused
seal_duration_seconds: public(uint256)

# GateSeal lifetime parameters
lifetime_duration_seconds: public(uint256)    # Duration of each lifetime period (initial and each prolongation)
expiry_timestamp: public(uint256)             # When the GateSeal expires
max_prolongations: public(uint256)            # Maximum number of prolongations allowed
prolongations_used: public(uint256)           # Number of prolongations already used
prolongation_window_seconds: public(uint256)  # Window before expiry when prolongations can be activated

# whether the seal was used. This is a one-time use contract
is_used: public(bool)

@deploy
def __init__(
    _sealing_committee: address,
    _seal_duration_seconds: uint256,
    _sealables: DynArray[address, MAX_SEALABLES],
    _lifetime_duration_seconds: uint256,
    _max_prolongations: uint256,
    _prolongation_window_seconds: uint256,
):
    """
    @notice creates a new GateSeal with the given parameters
    @param _sealing_committee the address that can seal the contracts
    @param _seal_duration_seconds the duration for which the sealables will be paused
    @param _sealables the addresses of the contracts that can be sealed
    @param _lifetime_duration_seconds the duration of each lifetime period
    @param _max_prolongations the maximum number of prolongations allowed
    @param _prolongation_window_seconds the window before expiry when prolongations can be activated
    """
    assert _sealing_committee != empty(address), "committee cannot be zero address"
    assert len(_sealables) >= 1, "must provide at least one sealable"
    assert len(_sealables) <= MAX_SEALABLES, "too many sealables"
    assert not self._has_duplicates(_sealables), "duplicate sealables"
    assert _seal_duration_seconds >= MIN_SEAL_DURATION_SECONDS, "seal duration too short"
    assert _seal_duration_seconds <= MAX_SEAL_DURATION_SECONDS, "seal duration too long"
    assert _lifetime_duration_seconds >= MIN_LIFETIME_DURATION_SECONDS, "lifetime duration too short"
    assert _lifetime_duration_seconds <= MAX_LIFETIME_DURATION_SECONDS, "lifetime duration too long"
    assert _max_prolongations <= MAX_PROLONGATIONS, "max prolongations too high"
    assert _prolongation_window_seconds >= MIN_PROLONGATION_WINDOW_SECONDS, "prolongation window too short"
    assert _prolongation_window_seconds <= MAX_PROLONGATION_WINDOW_SECONDS, "prolongation window too long"
    assert _prolongation_window_seconds <= _lifetime_duration_seconds, "prolongation window cannot exceed lifetime duration"

    self.sealing_committee = _sealing_committee
    self.seal_duration_seconds = _seal_duration_seconds
    self.sealables = _sealables
    self.lifetime_duration_seconds = _lifetime_duration_seconds
    self.expiry_timestamp = block.timestamp + _lifetime_duration_seconds
    self.max_prolongations = _max_prolongations
    self.prolongations_used = 0
    self.prolongation_window_seconds = _prolongation_window_seconds
    self.is_used = False

@external
def seal(_sealables: DynArray[address, MAX_SEALABLES]):
    """
    @notice pauses the contracts for the specified seal duration
    @param _sealables a subset of sealables passed to the constructor.
                     can pause multiple contracts in the same call 
    @dev this function can be used only once and only by sealing committee
    """
    assert msg.sender == self.sealing_committee, "unauthorized caller"
    assert block.timestamp < self.expiry_timestamp, "gate seal expired"
    assert not self.is_used, "gate seal already used"
    assert len(_sealables) > 0, "must provide sealables"

    # Verify all provided sealables are in the allowed list
    for sealable: address in _sealables:
        assert sealable in self.sealables, "sealable not in list"

    self.is_used = True
    failed_sealables: DynArray[uint256, MAX_SEALABLES] = []

    for i: uint256 in range(MAX_SEALABLES):
        if i >= len(_sealables):
            break
        
        sealable: address = _sealables[i]
        
        # Check current pause state before attempting to pause
        was_paused: bool = False
        pause_call_success: bool = False
        
        # Get current pause state (with safety fallback)
        pause_check_success: bool = False
        pause_response: Bytes[32] = b""
        pause_check_success, pause_response = raw_call(
            sealable,
            method_id("isPaused()"),
            max_outsize=32,
            revert_on_failure=False,
            is_static_call=True
        )
        
        if pause_check_success and len(pause_response) >= 32:
            was_paused = convert(pause_response, bool)
        
        # Attempt to pause the contract
        pause_success: bool = False
        pause_call_response: Bytes[32] = b""
        pause_success, pause_call_response = raw_call(
            sealable, 
            concat(method_id("pauseFor(uint256)"), convert(self.seal_duration_seconds, bytes32)),
            revert_on_failure=False
        )
        pause_call_success = pause_success
        
        # Verify successful sealing: pause call succeeded AND (contract became paused OR was already paused)
        is_now_paused: bool = False
        final_check_success: bool = False
        final_response: Bytes[32] = b""
        final_check_success, final_response = raw_call(
            sealable,
            method_id("isPaused()"),
            max_outsize=32,
            revert_on_failure=False,
            is_static_call=True
        )
        
        if final_check_success and len(final_response) >= 32:
            is_now_paused = convert(final_response, bool)
        
        # Operation is successful if: pause call succeeded AND (now paused OR was already paused)
        sealing_successful: bool = pause_call_success and (is_now_paused or was_paused)
        
        if not sealing_successful:
            failed_sealables.append(i)

    # Revert if any sealable failed to seal properly
    if len(failed_sealables) > 0:
        raise self._to_error_string(failed_sealables)

    log Sealed(sealed_by=msg.sender, sealables=_sealables, sealed_for=self.seal_duration_seconds)

@external
def prolongLifetime():
    """
    @notice prolongs the GateSeal lifetime by the lifetime duration
    @dev can only be called by sealing committee and within activation window
    """
    assert msg.sender == self.sealing_committee, "unauthorized caller"
    assert self.prolongations_used < self.max_prolongations, "no prolongations remaining"
    
    # Check if we're within the prolongation activation window
    time_until_expiry: uint256 = 0
    if block.timestamp < self.expiry_timestamp:
        time_until_expiry = self.expiry_timestamp - block.timestamp
    
    assert time_until_expiry <= self.prolongation_window_seconds, "outside activation window"
    assert time_until_expiry > 0, "gate seal expired"
    
    old_expiry: uint256 = self.expiry_timestamp
    
    # Overflow protection: check if addition would overflow
    assert old_expiry <= max_value(uint256) - self.lifetime_duration_seconds, "timestamp overflow"
    
    self.expiry_timestamp = old_expiry + self.lifetime_duration_seconds
    self.prolongations_used += 1
    
    log LifetimeProlonged(
        prolonged_by=msg.sender, 
        old_expiry=old_expiry, 
        new_expiry=self.expiry_timestamp, 
        prolongations_remaining=self.max_prolongations - self.prolongations_used
    )

@external
@view
def can_prolong_lifetime() -> bool:
    """
    @notice checks if the GateSeal lifetime can be prolonged right now
    @return true if prolongation is possible, false otherwise
    """
    if self.prolongations_used >= self.max_prolongations:
        return False
    
    if block.timestamp >= self.expiry_timestamp:
        return False
        
    time_until_expiry: uint256 = self.expiry_timestamp - block.timestamp
    return time_until_expiry <= self.prolongation_window_seconds

@external
@view
def is_expired() -> bool:
    """
    @notice checks if the GateSeal is expired
    @return true if expired, false otherwise
    """
    return block.timestamp >= self.expiry_timestamp

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

@internal
@pure
def _to_error_string(_failed_indexes: DynArray[uint256, MAX_SEALABLES]) -> String[100]:
    """
    @notice converts a list of indexes into an error message to facilitate debugging
    @param _failed_indexes a list of sealable indexes that failed to seal 
    """
    if len(_failed_indexes) == 0:
        return "no failures"
    
    return "sealable operations failed"
