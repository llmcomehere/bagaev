# Separate typed-record/11 bounded pure list capacity

Add a pure reference profile with named record-list capacity0..16 instead of0..4.
Keep schemas1..10, their executables/ABI entrypoints and component-owned boundary
unchanged. New program/invocation/result schemas use11, with a separate reference
entrypoint. No native exporter/adapter/ABI or production admission is extended.

The existing8type/4096expanded-unit/32function/2048node/depth/work/transport/value
bounds remain. Type expansion must still reject excessive nested shapes even if
individual list capacity fits16. No new operations or evaluation order changes.
Freeze literal16element length/sum/push results and capacity/argument/expansion
refusals. Reuse old catalogue99literal responses as a compatibility corpus in the
new profile. Compile only own reviewed sources using the existing approved
build-only IPC profile; run only under the existing no-network bounded profile.
No settings, compiler dependencies or execution helpers are changed.
