# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles


# ------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------

async def write_weight(dut, addr, data):
    """
    Load a signed 4-bit weight into the selected tap.
    """

    # Convert signed 4-bit value to two's complement representation
    data &= 0xF

    dut.ui_in.value = (addr & 0x3) | (1 << 2)       # weight_we = 1
    dut.uio_in.value = data

    await ClockCycles(dut.clk, 1)

    dut.ui_in.value = 0


async def write_sample(dut, addr, data):
    """
    Load a signed 4-bit sample into the selected tap.
    """

    # Convert signed 4-bit value to two's complement representation
    data &= 0xF

    dut.ui_in.value = (addr & 0x3) | (1 << 3)       # sample_we = 1
    dut.uio_in.value = data

    await ClockCycles(dut.clk, 1)

    dut.ui_in.value = 0


async def clear_accumulator(dut):
    """
    Clear the MAC accumulator.
    """

    dut.ui_in.value = 1 << 6                         # clear_acc = 1

    await ClockCycles(dut.clk, 1)

    dut.ui_in.value = 0


async def start_mac(dut, accumulate=False):
    """
    Start the MAC operation.

    accumulate=False:
        Replace the accumulator with the new MAC result.

    accumulate=True:
        Add the new MAC result to the existing accumulator.
    """

    dut.ui_in.value = (1 << 4) | ((1 << 5) if accumulate else 0)

    await ClockCycles(dut.clk, 1)

    dut.ui_in.value = 0


def signed8(value):
    """
    Convert an unsigned 8-bit value to signed integer.
    """

    value = int(value) & 0xFF

    if value & 0x80:
        return value - 256

    return value


# ------------------------------------------------------------
# Main test
# ------------------------------------------------------------

@cocotb.test()
async def test_project(dut):

    dut._log.info("Starting 4-Tap Signed MAC test")

    # --------------------------------------------------------
    # Clock
    # --------------------------------------------------------
    #
    # Participant testbench:
    # always #5 clk = ~clk;
    #
    # Therefore:
    # 10 ns period = 100 MHz
    #
    # --------------------------------------------------------

    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    # --------------------------------------------------------
    # Initial values
    # --------------------------------------------------------

    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0

    # --------------------------------------------------------
    # Reset
    # --------------------------------------------------------

    dut._log.info("Resetting DUT")

    await ClockCycles(dut.clk, 3)

    dut.rst_n.value = 1

    await ClockCycles(dut.clk, 1)

    dut._log.info("Reset released")

    # ========================================================
    # TEST 1 : BASIC MAC
    #
    # W = [1, 2, 3, 4]
    # X = [1, 2, 3, 4]
    #
    # 1*1 + 2*2 + 3*3 + 4*4
    # = 1 + 4 + 9 + 16
    # = 30
    # ========================================================

    dut._log.info("----------------------------------------")
    dut._log.info("TEST 1 : BASIC MAC")
    dut._log.info("----------------------------------------")

    weights = [1, 2, 3, 4]
    samples = [1, 2, 3, 4]

    for addr in range(4):
        await write_weight(dut, addr, weights[addr])

    for addr in range(4):
        await write_sample(dut, addr, samples[addr])

    await start_mac(dut, accumulate=False)

    result = signed8(dut.uo_out.value)

    dut._log.info(f"RESULT   = {result}")
    dut._log.info("EXPECTED = 30")

    assert result == 30, f"TEST 1 FAILED: expected 30, got {result}"

    dut._log.info("TEST 1 PASSED")

    # ========================================================
    # TEST 2 : SIGNED MAC
    #
    # W = [-1, 2, -3, 4]
    # X = [ 2, 3,  2,-2]
    #
    # (-1*2) + (2*3) + (-3*2) + (4*-2)
    # = -2 + 6 - 6 - 8
    # = -10
    # ========================================================

    dut._log.info("----------------------------------------")
    dut._log.info("TEST 2 : SIGNED MAC")
    dut._log.info("----------------------------------------")

    weights = [-1, 2, -3, 4]
    samples = [2, 3, 2, -2]

    for addr in range(4):
        await write_weight(dut, addr, weights[addr])

    for addr in range(4):
        await write_sample(dut, addr, samples[addr])

    await start_mac(dut, accumulate=False)

    result = signed8(dut.uo_out.value)

    dut._log.info(f"RESULT   = {result}")
    dut._log.info("EXPECTED = -10")

    assert result == -10, f"TEST 2 FAILED: expected -10, got {result}"

    dut._log.info("TEST 2 PASSED")

    # ========================================================
    # TEST 3 : ACCUMULATION
    #
    # First MAC:
    #
    # 1*1 + 1*1 + 1*1 + 1*1 = 4
    #
    # Second MAC:
    #
    # 2*1 + 2*1 + 2*1 + 2*1 = 8
    #
    # Accumulated result:
    #
    # 4 + 8 = 12
    # ========================================================

    dut._log.info("----------------------------------------")
    dut._log.info("TEST 3 : ACCUMULATION")
    dut._log.info("----------------------------------------")

    await clear_accumulator(dut)

    # First set of weights
    weights = [1, 1, 1, 1]
    samples = [1, 1, 1, 1]

    for addr in range(4):
        await write_weight(dut, addr, weights[addr])

    for addr in range(4):
        await write_sample(dut, addr, samples[addr])

    # First MAC = 4
    await start_mac(dut, accumulate=False)

    first_result = signed8(dut.uo_out.value)

    dut._log.info(f"FIRST MAC RESULT = {first_result}")

    assert first_result == 4, (
        f"TEST 3 FIRST MAC FAILED: expected 4, got {first_result}"
    )

    # Change weights to 2
    weights = [2, 2, 2, 2]

    for addr in range(4):
        await write_weight(dut, addr, weights[addr])

    # Second MAC = 8
    # Accumulate with previous 4
    await start_mac(dut, accumulate=True)

    accumulated_result = signed8(dut.uo_out.value)

    dut._log.info(f"ACCUMULATED RESULT = {accumulated_result}")
    dut._log.info("EXPECTED           = 12")

    assert accumulated_result == 12, (
        f"TEST 3 FAILED: expected 12, got {accumulated_result}"
    )

    dut._log.info("TEST 3 PASSED")

    # ========================================================
    # TEST 4 : OVERFLOW
    #
    # W = [7, 7, 7, 7]
    # X = [7, 7, 7, 7]
    #
    # Each product:
    #
    # 7 * 7 = 49
    #
    # Total:
    #
    # 49 + 49 + 49 + 49 = 196
    #
    # 196 is outside signed 8-bit range:
    #
    # -128 ... +127
    #
    # Therefore overflow_o must be 1.
    # ========================================================

    dut._log.info("----------------------------------------")
    dut._log.info("TEST 4 : OVERFLOW")
    dut._log.info("----------------------------------------")

    await clear_accumulator(dut)

    weights = [7, 7, 7, 7]
    samples = [7, 7, 7, 7]

    for addr in range(4):
        await write_weight(dut, addr, weights[addr])

    for addr in range(4):
        await write_sample(dut, addr, samples[addr])

    await start_mac(dut, accumulate=False)

    result_raw = int(dut.uo_out.value)
    result = signed8(result_raw)

    dut._log.info(f"RESULT        = {result}")
    dut._log.info("EXPECTED SUM  = 196")

    # overflow is internal to mac4 and is reachable hierarchically
    overflow = int(dut.user_project.u_mac.overflow.value)

    dut._log.info(f"OVERFLOW FLAG = {overflow}")

    assert overflow == 1, (
        f"TEST 4 FAILED: expected overflow=1, got {overflow}"
    )

    dut._log.info("TEST 4 PASSED")

    # --------------------------------------------------------
    # Final
    # --------------------------------------------------------

    dut._log.info("----------------------------------------")
    dut._log.info("ALL TESTS PASSED")
    dut._log.info("----------------------------------------")
