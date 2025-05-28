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

     GateSeals are only a temporary solution and will be deprecated in the future,
     as it is undesirable for the protocol to rely on a multisig. This is why
     each GateSeal has an expiry date. Once expired, GateSeal is no longer
     usable and a new GateSeal must be set up with a new multisig committee. This
     works as a kind of difficulty bomb, a device that encourages the protocol
     to get rid of GateSeals sooner rather than later.

     In the context of GateSeals, sealing is synonymous with pausing the contracts,
     sealables are pausable contracts that implement `pauseFor(duration)` interface.
"""

# The maximum GateSeal expiry duration is 1 year.
MAX_EXPIRY_PERIOD_DAYS: constant(uint256) = 365
MAX_EXPIRY_PERIOD_SECONDS: constant(uint256) = SECONDS_PER_DAY * MAX_EXPIRY_PERIOD_DAYS

interface IPausableUntil:
    def pauseFor(_duration: uint256): nonpayable
    def isPaused() -> bool: view


# A unix epoch timestamp starting from which GateSeal is completely unusable
# and a new GateSeal will have to be set up. This timestamp will be changed
# upon sealing to expire GateSeal immediately which will revert any consecutive sealings.


event Sealed:
    gate_seal: address
    sealed_by: address
    sealed_for: uint256
    sealable: address
    sealed_at: uint256

SECONDS_PER_DAY: constant(uint256) = 60 * 60 * 24

# The minimum allowed seal duration is 4 days. This is because it takes at least
# 3 days to pass and enact. Additionally, we want to include a 1-day padding.
MIN_SEAL_DURATION_DAYS: constant(uint256) = 4
MIN_SEAL_DURATION_SECONDS: constant(uint256) = SECONDS_PER_DAY * MIN_SEAL_DURATION_DAYS

# The maximum allowed seal duration is 14 days.
# Anything higher than that may be too long of a disruption for the protocol.
# Keep in mind, that the DAO still retains the ability to resume the contracts
# (or, in the GateSeal terms, "break the seal") prematurely.
MAX_SEAL_DURATION_DAYS: constant(uint256) = 14
MAX_SEAL_DURATION_SECONDS: constant(uint256) = SECONDS_PER_DAY * MAX_SEAL_DURATION_DAYS

# The maximum number of sealables is 8.
# GateSeals were originally designed to pause WithdrawalQueue and ValidatorExitBus,
# however, there is a non-zero chance that there might be more in the future, which
# is why we've opted to use a dynamic-size array.
MAX_SEALABLES: constant(uint256) = 8

# Below are string constants with error messages used for input validation and GateSeal operation checks.
SEALABLE_NOT_IN_LIST: constant(String[34]) = "sealables: includes a non-sealable"
SEALING_COMMITTEE_ZERO: constant(String[31]) = "sealing committee: zero address"
SEAL_DURATION_TOO_SHORT: constant(String[24]) = "seal duration: too short"
SEAL_DURATION_EXCEEDS_MAX: constant(String[26]) = "seal duration: exceeds max"
SEALABLES_EMPTY_LIST: constant(String[21]) = "sealables: empty list"
EXPIRY_MUST_BE_FUTURE: constant(String[39]) = "expiry timestamp: must be in the future"
EXPIRY_EXCEEDS_MAX: constant(String[43]) = "expiry timestamp: exceeds max expiry period"
SEALABLES_INCLUDES_ZERO: constant(String[32]) = "sealables: includes zero address"
SEALABLES_INCLUDES_DUPLICATES: constant(String[30]) = "sealables: includes duplicates"


# To simplify the code, we chose not to implement committees in GateSeals.
# Instead, GateSeals are operated by a single account which must be a multisig.
# The code does not perform any such checks but we pinky-promise that
# the sealing committee will always be a multisig. 
SEALING_COMMITTEE: immutable(address)
# The addresses of pausable contracts. The gate seal must have the permission to
# pause these contracts at the time of the sealing.
# Sealing can be partial, meaning the committee may decide to pause only a subset of this list,
# though GateSeal will still expire immediately.

# The duration of the seal in seconds. This period cannot exceed 14 days. 
# The DAO may decide to resume the contracts prematurely via the DAO voting process.
SEAL_DURATION_SECONDS: immutable(uint256)

sealables: DynArray[address, MAX_SEALABLES]
expiry_timestamp: uint256
@deploy
def __init__(
    _sealing_committee: address,
    _seal_duration_seconds: uint256,
    _sealables: DynArray[address, MAX_SEALABLES],
    _expiry_timestamp: uint256
):
    assert _sealing_committee != empty(address), SEALING_COMMITTEE_ZERO
    assert _seal_duration_seconds >= MIN_SEAL_DURATION_SECONDS, SEAL_DURATION_TOO_SHORT
    assert _seal_duration_seconds <= MAX_SEAL_DURATION_SECONDS, SEAL_DURATION_EXCEEDS_MAX
    assert len(_sealables) > 0, SEALABLES_EMPTY_LIST
    assert _expiry_timestamp > block.timestamp, EXPIRY_MUST_BE_FUTURE
    assert _expiry_timestamp <= block.timestamp + MAX_EXPIRY_PERIOD_SECONDS, EXPIRY_EXCEEDS_MAX
    for sealable: address in _sealables:
        assert sealable != empty(address), SEALABLES_INCLUDES_ZERO
    assert not self._has_duplicates(_sealables), SEALABLES_INCLUDES_DUPLICATES

    SEALING_COMMITTEE = _sealing_committee
    SEAL_DURATION_SECONDS = _seal_duration_seconds
    self.sealables = _sealables
    self.expiry_timestamp = _expiry_timestamp


@external
@view
def get_sealing_committee() -> address:
    return SEALING_COMMITTEE


@external
@view
def get_seal_duration_seconds() -> uint256:
    return SEAL_DURATION_SECONDS


@external
@view
def get_sealables() -> DynArray[address, MAX_SEALABLES]:
    return self.sealables


@external
@view
def get_expiry_timestamp() -> uint256:
    return self.expiry_timestamp


@external
@view
def is_expired() -> bool:
    return self._is_expired()


@external
def seal(_sealables: DynArray[address, MAX_SEALABLES]):
    """
    @notice Seal the contract(s).
    @dev    Immediately expires GateSeal and, thus, can only be called once.
    @param _sealables a list of sealables to seal; may include all or only a subset.
    """
    assert msg.sender == SEALING_COMMITTEE, "sender: not SEALING_COMMITTEE"
    assert not self._is_expired(), "gate seal: expired"
    assert len(_sealables) > 0, "sealables: empty subset"
    assert not self._has_duplicates(_sealables), "sealables: includes duplicates"

    self._expire_immediately()

    # Instead of reverting the transaction as soon as one of the sealables fails,
    # we iterate through the entire list and collect the indexes of those that failed
    # and report them in the dynamically-generated error message.
    # This will make it easier for us to debug in a hectic situation.
    failed_indexes: DynArray[uint256, MAX_SEALABLES] = []
    sealable_index: uint256 = 0

    for sealable: address in _sealables:
        assert sealable in self.sealables, SEALABLE_NOT_IN_LIST

        success: bool = False
        response: Bytes[32] = b""

        # using `raw_call` to catch external revert and continue execution
        # capturing `response` to keep the compiler from acting out but will not be checking it
        # as different sealables may return different values if anything at all
        # for details, see https://docs.vyperlang.org/en/stable/built-in-functions.html#raw_call
        success, response = raw_call(
            sealable,
            abi_encode(SEAL_DURATION_SECONDS, method_id=method_id("pauseFor(uint256)")),
            max_outsize=32,
            revert_on_failure=False
        )
        
        if success and staticcall IPausableUntil(sealable).isPaused():
            log Sealed(
                gate_seal=self,
                sealed_by=SEALING_COMMITTEE,
                sealed_for=SEAL_DURATION_SECONDS,
                sealable=sealable,
                sealed_at=block.timestamp
            )
        else:
            failed_indexes.append(sealable_index)
    
        sealable_index += 1

    assert len(failed_indexes) == 0, self._to_error_string(failed_indexes)


@internal
@view
def _is_expired() -> bool:
    return block.timestamp >= self.expiry_timestamp


@internal
def _expire_immediately():
    self.expiry_timestamp = block.timestamp


@internal
@pure
def _has_duplicates(_sealables: DynArray[address, MAX_SEALABLES]) -> bool:
    """
    @notice checks the list for duplicates 
    @param  _sealables list of addresses to check
    """
    unique: DynArray[address, MAX_SEALABLES] = []

    for sealable: address in _sealables:
        if sealable in unique:
            return True
        unique.append(sealable)

    return False


@internal
@pure
def _to_error_string(_failed_indexes: DynArray[uint256, MAX_SEALABLES]) -> String[78]:
    """
    @notice converts a list of indexes into an error message to facilitate debugging
    @dev    The indexes in the error message are given in the descending order to avoid
            losing leading zeros when casting to string,

            e.g. [0, 2, 3, 6] -> "6320"
    @param _failed_indexes a list of sealable indexes that failed to seal 
    """
    indexes_as_decimal: uint256 = 0
    loop_index: uint256 = 0

    # convert failed indexes to a decimal representation
    for failed_index: uint256 in _failed_indexes:
        indexes_as_decimal += failed_index * 10 ** loop_index
        loop_index += 1

    # generate error message with indexes as a decimal string
    # return type of `uint2str` is String[78] because 2^256 has 78 digits
    error_message: String[78] = uint2str(indexes_as_decimal)

    return error_message
