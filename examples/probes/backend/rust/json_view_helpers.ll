; Immutable admitted Node80/Entry24 only. Null is Missing, never dereferenced.
define internal i64 @json_word(ptr %node, i64 %offset) {
entry:
  %missing = icmp eq ptr %node, null
  br i1 %missing, label %none, label %read
read:
  %p = getelementptr i8, ptr %node, i64 %offset
  %v = load i64, ptr %p, align 8
  ret i64 %v
none:
  ret i64 0
}
define internal ptr @json_pointer(ptr %node, i64 %offset) {
entry:
  %missing = icmp eq ptr %node, null
  br i1 %missing, label %none, label %read
read:
  %p = getelementptr i8, ptr %node, i64 %offset
  %v = load ptr, ptr %p, align 8
  ret ptr %v
none:
  ret ptr null
}
define internal i64 @json_object_count(ptr %node) {
entry:
  %kind = call i64 @json_word(ptr %node, i64 0)
  %object = icmp eq i64 %kind, 7
  %count = call i64 @json_word(ptr %node, i64 8)
  %v = select i1 %object, i64 %count, i64 0
  ret i64 %v
}
define internal %Option @json_length(ptr %node) {
entry:
  %kind = call i64 @json_word(ptr %node, i64 0)
  %array = icmp eq i64 %kind, 6
  %object = icmp eq i64 %kind, 7
  %valid = or i1 %array, %object
  %count = call i64 @json_word(ptr %node, i64 8)
  %value = select i1 %valid, i64 %count, i64 0
  %flag = zext i1 %valid to i64
  %a = insertvalue %Option zeroinitializer, i64 %flag, 0
  %b = insertvalue %Option %a, i64 %value, 1
  ret %Option %b
}
define internal %Option @json_integer(ptr %node) {
entry:
  %flag = call i64 @json_word(ptr %node, i64 24)
  %value = call i64 @json_word(ptr %node, i64 32)
  %a = insertvalue %Option zeroinitializer, i64 %flag, 0
  %b = insertvalue %Option %a, i64 %value, 1
  ret %Option %b
}
define internal %Text @json_text(ptr %node) {
entry:
  %pointer = call ptr @json_pointer(ptr %node, i64 40)
  %length = call i64 @json_word(ptr %node, i64 48)
  %scalars = call i64 @json_word(ptr %node, i64 56)
  %a = insertvalue %Text zeroinitializer, ptr %pointer, 0
  %b = insertvalue %Text %a, i64 %length, 1
  %c = insertvalue %Text %b, i64 %scalars, 2
  ret %Text %c
}
define internal ptr @json_at(ptr %node, i64 %index) {
entry:
  %kind = call i64 @json_word(ptr %node, i64 0)
  %array = icmp eq i64 %kind, 6
  %count = call i64 @json_word(ptr %node, i64 8)
  %within = icmp ult i64 %index, %count
  %valid = and i1 %array, %within
  br i1 %valid, label %read, label %none
read:
  %entries = call ptr @json_pointer(ptr %node, i64 64)
  %offset = mul i64 %index, 24
  %item = getelementptr i8, ptr %entries, i64 %offset
  %p = getelementptr i8, ptr %item, i64 16
  %child = load ptr, ptr %p, align 8
  ret ptr %child
none:
  ret ptr null
}
define internal ptr @json_field(ptr %node, ptr %key, i64 %key_length) {
entry:
  %count = call i64 @json_object_count(ptr %node)
  %entries = call ptr @json_pointer(ptr %node, i64 64)
  br label %loop
loop:
  %i = phi i64 [0, %entry], [%next, %advance]
  %within = icmp ult i64 %i, %count
  br i1 %within, label %item, label %none
item:
  %offset = mul i64 %i, 24
  %p = getelementptr i8, ptr %entries, i64 %offset
  %kp = load ptr, ptr %p, align 8
  %lp = getelementptr i8, ptr %p, i64 8
  %length = load i64, ptr %lp, align 8
  %same_length = icmp eq i64 %length, %key_length
  %scalar = icmp ne ptr %kp, null
  %possible = and i1 %same_length, %scalar
  br i1 %possible, label %compare, label %advance
compare:
  %order = call i64 @text_compare(ptr %kp, i64 %length, ptr %key, i64 %key_length)
  %same = icmp eq i64 %order, 0
  br i1 %same, label %found, label %advance
found:
  %cp = getelementptr i8, ptr %p, i64 16
  %child = load ptr, ptr %cp, align 8
  ret ptr %child
advance:
  %next = add i64 %i, 1
  br label %loop
none:
  ret ptr null
}
@json_kind_0 = private constant [7 x i8] c"missing", align 1
@json_kind_1 = private constant [4 x i8] c"null", align 1
@json_kind_2 = private constant [4 x i8] c"bool", align 1
@json_kind_3 = private constant [3 x i8] c"int", align 1
@json_kind_4 = private constant [6 x i8] c"number", align 1
@json_kind_5 = private constant [4 x i8] c"text", align 1
@json_kind_6 = private constant [5 x i8] c"array", align 1
@json_kind_7 = private constant [6 x i8] c"object", align 1
define internal %Text @json_kind(ptr %node) {
entry:
  %kind = call i64 @json_word(ptr %node, i64 0)
  switch i64 %kind, label %k0 [
    i64 1, label %k1
    i64 2, label %k2
    i64 3, label %k3
    i64 4, label %k4
    i64 5, label %k5
    i64 6, label %k6
    i64 7, label %k7
  ]
k0:
  ret %Text {ptr @json_kind_0, i64 7, i64 7}
k1:
  ret %Text {ptr @json_kind_1, i64 4, i64 4}
k2:
  ret %Text {ptr @json_kind_2, i64 4, i64 4}
k3:
  ret %Text {ptr @json_kind_3, i64 3, i64 3}
k4:
  ret %Text {ptr @json_kind_4, i64 6, i64 6}
k5:
  ret %Text {ptr @json_kind_5, i64 4, i64 4}
k6:
  ret %Text {ptr @json_kind_6, i64 5, i64 5}
k7:
  ret %Text {ptr @json_kind_7, i64 6, i64 6}
}
