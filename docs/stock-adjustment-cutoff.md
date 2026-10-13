# Current cutoffs after a lost stock response

This extends the selected [restart](stock-adjustment-restart.md) cases with
current deadline and epoch conditions. The application source, A-E fixtures,
complete E intent and two existing process-cut drivers are unchanged. E has
epoch 1 and deadline 100. Recovery uses either tick 101/epoch 1 or tick 2/epoch 2
in the same clock domain; it does not translate clocks or renew a deadline.

## An uncommitted intent cannot become a new effect after cutoff

After the pre-COMMIT exit, the saved image is G4/R9, quantity 0, two mutations.
E is Unknown. Submission with current submit/write permission disabled refuses
without changing that image. With those synthetic permissions explicitly enabled,
the deadline case records Refused/DeadlineExpired at revision 9, and the epoch
case records Refused/EpochMismatch at revision 9. Each advances G to 5 while
preserving stock, R and mutation count. Neither evaluates the application.

## A cutoff does not erase a committed fact

After the post-COMMIT exit, E already has its exact Applied receipt at revision
10, quantity 7, three mutations and G5. Current observation may retrieve it
despite the later deadline or epoch cutoff. Submission still needs current
submit permission; once granted, it returns the retained receipt without a new
application evaluation or any image change. This is historical observation,
not permission to perform an expired operation again.

All four cases also disable write permission and repeat the same submission,
then use a third fresh process with submit/write/cancel disabled to observe E.
The complete terminal image remains unchanged, and both post-cut processes
perform zero application evaluations.

## Reproduction and limits

Review the [parent driver](../tests/probes/stock_adjustment_cutoff_checks.py),
[recovery child](../tests/probes/stock_adjustment_cutoff_child.py), and their
existing cut-stage dependencies. Use separately reviewed reader/reference
binaries under an authorized bounded profile:

```console
python3 -B tests/probes/stock_adjustment_cutoff_checks.py --reader /absolute/reviewed/reader --reader-sha256 READER_SHA256 --reference /absolute/reviewed/record-reference10 --reference-sha256 REFERENCE_SHA256 --output /absolute/new-output-directory
```

The selected run passed four cases, each with three strictly serial processes.
Per pre-COMMIT case the reader/reference call counts were 52/58/12; per
post-COMMIT case they were 52/65/13. Total: 504 calls, with application
evaluations 5/0/0 per case. Repeated setup and reconstruction calls are not new
independent business cases. The base-main dependency subset also passed the
same cases without the separate final-CAS changes; that is a repetition, not
additional scenario coverage.

These are synthetic current-condition flags and selected own process exits.
No production authentication, clock migration, power-loss safety, arbitrary
crash coverage, external-effect guarantee, model or performance result is claimed.
Static CI does not execute these runtime checks.
