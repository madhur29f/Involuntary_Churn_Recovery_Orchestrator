import pytest
from services.simulation.engine import population, event as sim_event, oracle

def test_population_generation_is_strictly_reproducible():
    pop1 = population(seed=42, size=50)
    pop2 = population(seed=42, size=50)
    assert pop1 == pop2

def test_oracle_outcome_is_deterministic():
    sub = population(seed=123, size=1)[0]
    evt = sim_event(sub, "batch_123_1")
    res1_naive = oracle(evt, "naive")
    res2_naive = oracle(evt, "naive")
    assert res1_naive == res2_naive

    res1_orch = oracle(evt, "orchestrator")
    res2_orch = oracle(evt, "orchestrator")
    assert res1_orch == res2_orch

def test_oracle_benchmark_rates_meet_specification_band():
    """Verify over a representative cohort (N=500) that naive lands ~20-40% and orchestrator ~55-75%."""
    cohort = population(seed=999, size=500)
    naive_recovered = 0
    orch_recovered = 0

    for sub in cohort:
        evt = sim_event(sub, "batch_test")
        if oracle(evt, "naive"):
            naive_recovered += 1
        if oracle(evt, "orchestrator"):
            orch_recovered += 1

    naive_rate = (naive_recovered / 500) * 100
    orch_rate = (orch_recovered / 500) * 100

    assert 20.0 <= naive_rate <= 40.0, f"Naive rate {naive_rate}% outside 20-40% band"
    assert 55.0 <= orch_rate <= 75.0, f"Orchestrator rate {orch_rate}% outside 55-75% band"
