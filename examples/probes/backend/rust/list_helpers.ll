; Bounded immutable descriptor helpers. Caller has reserved logical work.
define internal ptr @list_alloc(ptr %arena, i64 %n) {
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
  %result = getelementptr %Text, ptr %base, i64 %used
  %next = add i64 %used, %n
  store i64 %next, ptr %used_p, align 8
  ret ptr %result
fail:
  ret ptr null
}
define internal i64 @list_contains(%List %list, %Text %query) {
entry:
  %base = extractvalue %List %list, 0
  %n = extractvalue %List %list, 1
  %qp = extractvalue %Text %query, 0
  %ql = extractvalue %Text %query, 1
  br label %loop
loop:
  %i = phi i64 [0, %entry], [%next, %advance]
  %more = icmp ult i64 %i, %n
  br i1 %more, label %compare, label %absent
compare:
  %p = getelementptr %Text, ptr %base, i64 %i
  %v = load %Text, ptr %p, align 8
  %vp = extractvalue %Text %v, 0
  %vl = extractvalue %Text %v, 1
  %c = call i64 @text_compare(ptr %vp, i64 %vl, ptr %qp, i64 %ql)
  %equal = icmp eq i64 %c, 0
  br i1 %equal, label %present, label %advance
advance:
  %next = add i64 %i, 1
  br label %loop
present:
  ret i64 1
absent:
  ret i64 0
}
define internal i64 @list_increasing(%List %list) {
entry:
  %base = extractvalue %List %list, 0
  %n = extractvalue %List %list, 1
  br label %loop
loop:
  %i = phi i64 [1, %entry], [%next, %advance]
  %more = icmp ult i64 %i, %n
  br i1 %more, label %compare, label %yes
compare:
  %prev = sub i64 %i, 1
  %ap = getelementptr %Text, ptr %base, i64 %prev
  %bp = getelementptr %Text, ptr %base, i64 %i
  %a = load %Text, ptr %ap, align 8
  %b = load %Text, ptr %bp, align 8
  %ab = extractvalue %Text %a, 0
  %al = extractvalue %Text %a, 1
  %bb = extractvalue %Text %b, 0
  %bl = extractvalue %Text %b, 1
  %c = call i64 @text_compare(ptr %ab, i64 %al, ptr %bb, i64 %bl)
  %less = icmp slt i64 %c, 0
  br i1 %less, label %advance, label %no
advance:
  %next = add i64 %i, 1
  br label %loop
yes:
  ret i64 1
no:
  ret i64 0
}
define internal %List @list_unique(%List %list, ptr %dest) {
entry:
  %count_p = alloca i64, align 8
  %sum_p = alloca i64, align 8
  store i64 0, ptr %count_p, align 8
  store i64 0, ptr %sum_p, align 8
  %base = extractvalue %List %list, 0
  %n = extractvalue %List %list, 1
  br label %loop
loop:
  %i = phi i64 [0, %entry], [%next_i, %advance]
  %more = icmp ult i64 %i, %n
  br i1 %more, label %item, label %done
item:
  %p = getelementptr %Text, ptr %base, i64 %i
  %v = load %Text, ptr %p, align 8
  %vp = extractvalue %Text %v, 0
  %vl = extractvalue %Text %v, 1
  %count = load i64, ptr %count_p, align 8
  br label %search
search:
  %pos = phi i64 [0, %item], [%next_pos, %search_next]
  %exists = icmp ult i64 %pos, %count
  br i1 %exists, label %compare, label %insert
compare:
  %at = getelementptr %Text, ptr %dest, i64 %pos
  %old = load %Text, ptr %at, align 8
  %op = extractvalue %Text %old, 0
  %ol = extractvalue %Text %old, 1
  %c = call i64 @text_compare(ptr %vp, i64 %vl, ptr %op, i64 %ol)
  %equal = icmp eq i64 %c, 0
  br i1 %equal, label %advance, label %order
order:
  %less = icmp slt i64 %c, 0
  br i1 %less, label %insert, label %search_next
search_next:
  %next_pos = add i64 %pos, 1
  br label %search
insert:
  br label %shift
shift:
  %j = phi i64 [%count, %insert], [%prev_j, %move]
  %needs = icmp ugt i64 %j, %pos
  br i1 %needs, label %move, label %store
move:
  %prev_j = sub i64 %j, 1
  %from = getelementptr %Text, ptr %dest, i64 %prev_j
  %to = getelementptr %Text, ptr %dest, i64 %j
  %moving = load %Text, ptr %from, align 8
  store %Text %moving, ptr %to, align 8
  br label %shift
store:
  %target = getelementptr %Text, ptr %dest, i64 %pos
  store %Text %v, ptr %target, align 8
  %new_count = add i64 %count, 1
  store i64 %new_count, ptr %count_p, align 8
  %sum = load i64, ptr %sum_p, align 8
  %new_sum = add i64 %sum, %vl
  store i64 %new_sum, ptr %sum_p, align 8
  br label %advance
advance:
  %next_i = add i64 %i, 1
  br label %loop
done:
  %final_count = load i64, ptr %count_p, align 8
  %final_sum = load i64, ptr %sum_p, align 8
  %a = insertvalue %List zeroinitializer, ptr %dest, 0
  %b = insertvalue %List %a, i64 %final_count, 1
  %result = insertvalue %List %b, i64 %final_sum, 2
  ret %List %result
}
