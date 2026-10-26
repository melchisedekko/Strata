// C ABI for the FINAL local patch (arm A = JointGate defaults, Strata Lead decision 25/10/2026).  Same entry points as
// strata_spec_capi_p3.cpp (included verbatim) plus jg_new_default(): a JointGate built with Options() exactly as the
// engine gets it with STRATA_SPEC_JOINT=1, no parameter passed from the replay.  No logic lives here.
#include "strata_spec_capi_p3.cpp"
extern "C" {
void* jg_new_default() { return new JointGate(); }
int jg_default_tmax() { return JointGate().tmax(); }
int jg_env_enabled() { return JointGate::enabled_from_env() ? 1 : 0; }
}
