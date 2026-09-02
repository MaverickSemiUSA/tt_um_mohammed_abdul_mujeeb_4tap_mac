# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, Timer


# ------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------

async def write_weight(dut, addr, data):
    """Load a signed 4-bit weight into the selected tap."""

    # Convert signed 4-bit value to two's complement representation
    data &= 0xF

    await FallingEdge(dut.clk)

    # Select tap
    dut.ui_in.value = (
        (addr & 0x3) |
        (1 << 2)          # LOAD_WEIGHT
    )

    # Put 4-bit signed data on uio_in[3:0]
    dut.uio_in.value = data

    # Hold write enable through the rising edge
    await RisingEdge(dut.clk)

    # Release controls after the write has occurred
    await FallingEdge(dut.clk)

    dut.ui_in.value = 0


async def write_sample(dut, addr, data):
    """Load a signed 4-bit sample into the selected tap."""

    # Convert signed 4-bit value to two's complement representation
    data &= 0xF

    await FallingEdge(dut.clk)

    # Select tap
    dut.ui_in.value = (
        (addr & 0x3) |
        (1 << 3)          # LOAD_SAMPLE
    )

    # Put 4-bit signed data on uio_in[3:0]
    dut.uio_in.value = data

    # Hold write enable through the rising edge
    await RisingEdge(dut.clk)

    # Release controls after the write has occurred
    await FallingEdge(dut.clk)

    dut.ui_in.value = 0


async def clear_accumulator(dut):
    """Clear the MAC accumulator."""

    await FallingEdge(dut.clk)

    # ui_in[6] = clear_acc
    dut.ui_in.value = 1 << 6

    # Clear occurs at this rising edge
    await RisingEdge(dut.clk)

    await FallingEdge(dut.clk)

    dut.ui_in.value = 0


async def start_mac(dut, accumulate=False):
    """Start a MAC operation."""

    await FallingEdge(dut.clk)

    # ui_in[4] = start
    # ui_in[5] = accumulate
    dut.ui_in.value = (
        (1 << 4) |
        ((1 << 5) if accumulate else 0)
    )

    # MAC occurs at this rising edge
    await RisingEdge(dut.clk)

    await FallingEdge(dut.clk)

    dut.ui_in.value = 0


def signed8(value):
    """Convert an unsigned 8-bit value to a signed integer."""

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
    #
    # always #5 clk = ~clk;
    #
    # 10 ns period = 100 MHz
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

    await Timer(20, unit="ns")

    dut.rst_n.value = 1

    # Allow reset release to settle
    await Timer(1, unit="ns")

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

    assert result == 30, (
        f"TEST 1 FAILED: expected 30, got {result}"
    )

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

    assert result == -10, (
        f"TEST 2 FAILED: expected -10, got {result}"
    )

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

    # First MAC
    weights = [1, 1, 1, 1]
    samples = [1, 1, 1, 1]

    for addr in range(4):
        await write_weight(dut, addr, weights[addr])

    for addr in range(4):
        await write_sample(dut, addr, samples[addr])

    await start_mac(dut, accumulate=False)

    first_result = signed8(dut.uo_out.value)

    dut._log.info(f"FIRST MAC RESULT = {first_result}")

    assert first_result == 4, (
        f"TEST 3 FIRST MAC FAILED: expected 4, "
        f"got {first_result}"
    )

    # Change weights to 2
    weights = [2, 2, 2, 2]

    for addr in range(4):
        await write_weight(dut, addr, weights[addr])

    # Second MAC = 8
    # Accumulate with previous result = 4 + 8 = 12
    await start_mac(dut, accumulate=True)

    accumulated_result = signed8(dut.uo_out.value)

    dut._log.info(
        f"ACCUMULATED RESULT = {accumulated_result}"
    )
    dut._log.info("EXPECTED           = 12")

    assert accumulated_result == 12, (
        f"TEST 3 FAILED: expected 12, "
        f"got {accumulated_result}"
    )

    dut._log.info("TEST 3 PASSED")

    # ========================================================
    # TEST 4 : OVERFLOW
    #
    # W = [7, 7, 7, 7]
    # X = [7, 7, 7, 7]
    #
    # 7*7 = 49
    #
    # 49 + 49 + 49 + 49 = 196
    #
    # Signed 8-bit range:
    # -128 ... +127
    #
    # Therefore overflow must be asserted.
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

    # overflow is a wire inside tt_um_4tap_mac
    overflow = int(dut.user_project.overflow.value)

    dut._log.info(f"OVERFLOW FLAG = {overflow}")

    assert overflow == 1, (
        f"TEST 4 FAILED: expected overflow=1, "
        f"got {overflow}"
    )

    dut._log.info("TEST 4 PASSED")

    # --------------------------------------------------------
    # Final
    # --------------------------------------------------------

    dut._log.info("----------------------------------------")
    dut._log.info("ALL TESTS PASSED")
    dut._log.info("----------------------------------------")
