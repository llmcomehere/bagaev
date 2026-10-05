define internal i64 @text_compare(ptr %a, i64 %al, ptr %b, i64 %bl) {
entry:
  br label %loop
loop:
  %i = phi i64 [0, %entry], [%next, %same]
  %ina = icmp ult i64 %i, %al
  %inb = icmp ult i64 %i, %bl
  %both = and i1 %ina, %inb
  br i1 %both, label %bytes, label %lengths
bytes:
  %ap = getelementptr i8, ptr %a, i64 %i
  %bp = getelementptr i8, ptr %b, i64 %i
  %av = load i8, ptr %ap, align 1
  %bv = load i8, ptr %bp, align 1
  %eq = icmp eq i8 %av, %bv
  br i1 %eq, label %same, label %different
same:
  %next = add i64 %i, 1
  br label %loop
different:
  %less = icmp ult i8 %av, %bv
  %order = select i1 %less, i64 -1, i64 1
  ret i64 %order
lengths:
  %equal_length = icmp eq i64 %al, %bl
  %shorter = icmp ult i64 %al, %bl
  %length_order = select i1 %shorter, i64 -1, i64 1
  %result = select i1 %equal_length, i64 0, i64 %length_order
  ret i64 %result
}
