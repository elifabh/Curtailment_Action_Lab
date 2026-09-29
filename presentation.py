"""Presentation contract shared by recorded and live numerical comparisons."""
from __future__ import annotations

LIMITATIONS = [
    "Planning screen only: existing and changed voltage violations below 100 kV remain unresolved. Neither case is approved for operation.",
    "The original strict source-reconstruction residual gate failed. Solved voltages closely match the source, but this is an approximate reconstruction, not independently validated operational data.",
    "HVDC boundary injections are calibrated from the source solution; transformer/shunt settings and remote voltage controls are held fixed. Generator Q boundaries use local PV-to-PQ switching.",
    "No complete N-1, dynamic, protection, market or outage-scheduling feasibility assessment. No measured national avoided curtailment, savings or annual benefit is claimed.",
    "This is a snapshot in MW. It is not an energy result in MWh. The wind increment and line outage are hypothetical.",
]
ASSUMPTIONS = [
    "EirGrid TYTFS2024 Winter Peak 2024 reference case; unchanged original constant-power demand of 7,324.51 MW.",
    "Additional unity-power-factor wind at Binbane 110 kV (bus 1341), balanced by equal active-power reduction at generator bus 10470 (Aghada); the slack accounts for losses.",
    "Compare circuit 1341–1701–1 in service against its hypothetical outage. No real maintenance permission or weather forecast is implied.",
    "Screen all rated branch thermal limits, voltage limits at buses >=100 kV, generator active/reactive bounds and AC balance. Reactive-power tolerance: 0.02 Mvar.",
]


def checks(result):
    converged = result.get("converged", False)
    def zero(name):
        return converged and result.get(name) == 0
    return [
        {"label": "AC solution converged", "passed": bool(converged), "detail": "Numerical convergence does not establish operational feasibility."},
        {"label": "AC nodal balance", "passed": converged and result.get("AC_balance_residual_MVA", 1) < 1e-4,
         "detail": f"Maximum residual: {result.get('AC_balance_residual_MVA', 'unreported')} MVA."},
        {"label": "Rated branch thermal limits", "passed": zero("thermal_violations"), "detail": f"Violations: {result.get('thermal_violations', 'unreported')}; maximum loading: {result.get('max_loading_pct', 'unreported')}%."},
        {"label": "Transmission voltages (>=100 kV)", "passed": zero("transmission_voltage_violations"), "detail": "Only the specified transmission-voltage subset is screened here."},
        {"label": "Generator active-power bounds", "passed": zero("generator_P_violations"), "detail": "Includes the balancing generator and solved slack output."},
        {"label": "Generator reactive-power bounds", "passed": zero("generator_Q_violations"), "detail": "0.02 Mvar tolerance; local PV-to-PQ conversion at violated Q limits."},
        {"label": "Voltages below 100 kV", "passed": zero("collector_voltage_violations"), "detail": f"Unresolved violations: {result.get('collector_voltage_violations', 'unreported')}. These prevent an all-network feasibility claim."},
        {"label": "Original strict source residual gate", "passed": False, "detail": "Failed. Close voltage matching supports an exploratory approximation, not a passed independent validation."},
        {"label": "Full N-1 and dynamic security", "passed": None, "detail": "Not evaluated. A single hypothetical outage comparison is not full N-1 security."},
        {"label": "Operator approval", "passed": None, "detail": "No real switching, dispatch or maintenance approval has been obtained."},
    ]


def result_document(case_id, name, baseline, selected, metrics, message, evidence=None):
    return {
        "scenario": {"id": case_id, "name": name},
        "baseline": baseline,
        "selected": selected,
        "comparison": {"metrics": metrics, "message": message},
        "decision_status": "engineering_review_required_not_operationally_approved",
        "checks": checks(selected),
        "assumptions": ASSUMPTIONS,
        "limitations": LIMITATIONS,
        "evidence": evidence or {"baseline": baseline, "selected": selected},
        "physical_actions_executed": False,
    }


def live_document(wind, in_service, baseline, selected):
    metrics = []
    for label, key, unit in [("Requested additional wind", "added_wind_MW", "MW"),
                             ("Maximum branch loading", "max_loading_pct", "%"),
                             ("Thermal violations", "thermal_violations", "branches"),
                             ("Unresolved lower-voltage violations", "collector_voltage_violations", "buses")]:
        metrics.append({"label": label, "baseline": baseline.get(key), "selected": selected.get(key), "unit": unit})
    doc = result_document("live_comparison", "Live AC check: " + ("line in service" if in_service else "line outage"),
                          baseline, selected, metrics,
                          "Both topologies use the same requested wind injection. A failed check blocks an operational recommendation.")
    doc.update(mode="live_fixed_control_ac_comparison", request={"available_wind_MW": wind, "line_in_service": in_service})
    doc["evidence"]["baseline_topology"] = "outage" if in_service else "in service"
    doc["evidence"]["selected_topology"] = "in service" if in_service else "outage"
    return doc
