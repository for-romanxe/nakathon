from math import erfc, sqrt
from random import Random

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LinkSimulation(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    narrow_amplitude: float = Field(default=1.0, ge=0.1, le=10)
    wide_amplitude: float = Field(default=3.0, ge=0.1, le=10)
    noise_sd: float = Field(default=1.0, ge=0, le=10)
    trials: int = Field(default=100, ge=1, le=200, strict=True)
    seed: int = Field(default=42, ge=0, le=2**32 - 1, strict=True)

    @model_validator(mode="after")
    def validate_amplitudes(self) -> "LinkSimulation":
        if self.wide_amplitude <= self.narrow_amplitude:
            raise ValueError("wide_amplitude must exceed narrow_amplitude.")
        return self


def compare_packet(payload: str, config: LinkSimulation) -> dict:
    symbols = tuple(
        1 if byte & (1 << shift) else -1
        for byte in payload.encode("utf-8")
        for shift in range(7, -1, -1)
    )
    random = Random(config.seed)
    narrow_bit_errors = wide_bit_errors = 0
    narrow_successes = wide_successes = 0
    for _ in range(config.trials):
        narrow_errors = wide_errors = 0
        for symbol in symbols:
            noise = random.gauss(0, config.noise_sd)
            narrow_received = symbol * config.narrow_amplitude + noise
            wide_received = symbol * config.wide_amplitude + noise
            narrow_errors += (narrow_received >= 0) != (symbol == 1)
            wide_errors += (wide_received >= 0) != (symbol == 1)
        narrow_bit_errors += narrow_errors
        wide_bit_errors += wide_errors
        narrow_successes += narrow_errors == 0
        wide_successes += wide_errors == 0

    bit_count = len(symbols)
    results = []
    for amplitude, bit_errors, successes in (
        (config.narrow_amplitude, narrow_bit_errors, narrow_successes),
        (config.wide_amplitude, wide_bit_errors, wide_successes),
    ):
        expected_ber = (
            0.5 * erfc(amplitude / (sqrt(2) * config.noise_sd)) if config.noise_sd else 0.0
        )
        results.append({
            "amplitude": amplitude,
            "signal_spacing": 2 * amplitude,
            "bit_errors": bit_errors,
            "bit_error_rate": bit_errors / (bit_count * config.trials),
            "successful_packets": successes,
            "packet_success_rate": successes / config.trials,
            "expected_packet_success_rate": (1 - expected_ber) ** bit_count,
            "relative_energy_per_bit": (amplitude / config.narrow_amplitude) ** 2,
        })
    return {"packet_bits": bit_count, "trials": config.trials, "noise_sd": config.noise_sd,
            "seed": config.seed, "narrow": results[0], "wide": results[1]}
