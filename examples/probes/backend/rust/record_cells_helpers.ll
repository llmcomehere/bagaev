; Bounded immutable descriptor helpers. Caller has reserved logical work.
define internal ptr @cells_alloc(ptr %arena, i64 %n) {
entry:
  %cap_p = getelementptr i8, ptr %arena, i64 8
  %used_p = getelementptr i8, ptr %arena, i64 16
  %cap = load i64, ptr %cap_p, align 8
  %used = load i64, ptr %used_p, align 8
  %bad = icmp ugt i64 %used, %cap
  br i1 %bad, label %fail, label %check
check:
  %remaining = sub i64 %cap, %used
  %large = icmp ugt i64 %n, %remaining
  br i1 %large, label %fail, label %allocate
allocate:
  %base = load ptr, ptr %arena, align 8
  %result = getelementptr %Cell, ptr %base, i64 %used
  %next = add i64 %used, %n
  store i64 %next, ptr %used_p, align 8
  ret ptr %result
fail:
  ret ptr null
}
