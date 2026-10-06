# Partial build-record data inspection

This experimental [inspector](../examples/probes/build-record/inspect_record.py) compares one bounded descriptive JSON record with an independently supplied expected descriptor and four exact byte strings. It hashes source, module, harness and artifact bytes without interpreting or executing them. The [contract](../examples/probes/build-record/contract.md) fixes shape, limits and refusal ordering. Dependency names and interpreter paths are inert data, never opened or resolved.

Matching returns matched-data with build_verified, dependencies_resolved and execution_admission all false. An observed-build label remains an unverified assertion. Arbitrary non-executable bytes can match their declared artifact digest. Receiver expectation selection, truthful build provenance, transitive tools/linker/sysroot, loader resolution, signatures and execution admission are outside this interface. This is not adoption of a production build manifest or a native loader.

## Synthetic qualification

The [42 pre-existing literal cases](../examples/probes/build-record/cases.json) cover duplicate keys, transport/shape, independently supplied expectation, four content dimensions, bounds and refusal-order collisions. [Five mutations](../examples/probes/build-record/mutations.json) produce normal wrong success: ignoring build context, provenance or artifact bytes; choosing the expectation from the submitted record; and promoting a descriptive build assertion. The final case is detected even though the status string remains matched-data.

Run python3 tests/probes/check_build_record.py from a bounded approved environment. The runner imports only the local inspected module and applies these five explicitly listed source substitutions; it launches no native artifact, compiler or network process and writes no external files. It preserves caller inputs. Fixture byte limits require up to32MiB plus copies for the largest negative case. The native-calls and builds counts remain zero.

These are finite same-maintainer source/data checks, not independent reproduction or proof against arbitrary inputs. No host-specific artifact associations or compiler/runtime inventories accompany this public example. Existing native profiles, workflows and execution permissions are unchanged.
