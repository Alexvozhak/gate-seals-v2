# @version 0.4.1

"""
@title AdvancedSealableMock
@notice Advanced mock contract for testing GateSeal edge cases
@dev This contract provides configurable behavior for testing various scenarios:
     - Normal pausable behavior
     - High gas consumption
     - Revert behavior
     - Reentrancy attempts
     - Custom return values
"""

interface IGateSeal:
    def seal(_sealables: DynArray[address, 8]): nonpayable
    def prolongLifetime(): nonpayable

# Behavior configuration flags
paused_until: uint256
gas_bomb_enabled: bool
revert_on_pause: bool
revert_on_is_paused: bool
reentrancy_target: address
custom_is_paused_return: bool
simulate_async_pause_change: bool

# Gas bomb settings
gas_consumption_loops: uint256

@deploy  
def __init__(
    _gas_bomb_enabled: bool,
    _revert_on_pause: bool,
    _revert_on_is_paused: bool,
    _gas_consumption_loops: uint256,
    _custom_is_paused_return: bool
):
    """
    @notice Initialize the mock with specific behavior
    @param _gas_bomb_enabled Whether to consume excessive gas
    @param _revert_on_pause Whether to revert on pauseFor calls
    @param _revert_on_is_paused Whether to revert on isPaused calls  
    @param _gas_consumption_loops Number of loops for gas consumption
    @param _custom_is_paused_return Whether to return custom isPaused values
    """
    self.gas_bomb_enabled = _gas_bomb_enabled
    self.revert_on_pause = _revert_on_pause
    self.revert_on_is_paused = _revert_on_is_paused
    self.gas_consumption_loops = _gas_consumption_loops
    self.custom_is_paused_return = _custom_is_paused_return
    self.paused_until = 0


@external
def pauseFor(_duration: uint256):
    """
    @notice Pause contract for specified duration with configurable behavior
    @param _duration Duration to pause in seconds
    """
    if self.revert_on_pause:
        raise "Mock: revert on pause"
        
    # Gas bomb simulation
    if self.gas_bomb_enabled:
        # Use fixed upper bound to avoid variable range issues
        for i: uint256 in range(10000):
            if i >= self.gas_consumption_loops:
                break
            # Consume gas with meaningless operations
            temp: uint256 = i * i + i
            temp = temp % 1000
            
    # Reentrancy attempt simulation
    if self.reentrancy_target != empty(address):
        # Try to call gate seal functions during pauseFor
        success: bool = False
        response: Bytes[32] = b""
        success, response = raw_call(
            self.reentrancy_target,
            abi_encode(method_id("prolongLifetime()")),
            max_outsize=32,
            revert_on_failure=False
        )
        
    # Simulate async pause state change
    if self.simulate_async_pause_change:
        # First set paused, then unset it in the same transaction
        self.paused_until = block.timestamp + _duration
        # Simulate some external event that unpauses
        if _duration > 1000:
            self.paused_until = 0
    else:
        # Normal behavior
        self.paused_until = block.timestamp + _duration


@external
@view
def isPaused() -> bool:
    """
    @notice Check if contract is paused with configurable behavior
    @return True if paused, custom value if configured
    """
    if self.revert_on_is_paused:
        raise "Mock: revert on isPaused"
        
    if self.custom_is_paused_return:
        # Return opposite of actual state for testing
        return not (block.timestamp < self.paused_until)
        
    return block.timestamp < self.paused_until


@external
def setReentrancyTarget(_target: address):
    """
    @notice Set target for reentrancy attempts
    @param _target Address to call back during pauseFor
    """
    self.reentrancy_target = _target


@external  
def setGasBombLoops(_loops: uint256):
    """
    @notice Configure gas consumption for testing
    @param _loops Number of loops to execute
    """
    self.gas_consumption_loops = _loops
    

@external
def setAsyncPauseSimulation(_enabled: bool):
    """
    @notice Enable/disable async pause state change simulation
    @param _enabled Whether to simulate async changes
    """
    self.simulate_async_pause_change = _enabled


@external
def setCustomIsPausedReturn(_enabled: bool):
    """
    @notice Enable/disable custom isPaused return values
    @param _enabled Whether to return custom values
    """
    self.custom_is_paused_return = _enabled


@external
@view
def getPausedUntil() -> uint256:
    """
    @notice Get the timestamp until which contract is paused
    @return Paused until timestamp
    """
    return self.paused_until


@external
def reset():
    """
    @notice Reset all state for testing
    """
    self.paused_until = 0
    self.reentrancy_target = empty(address)
    self.simulate_async_pause_change = False