class_name ManifestValue
extends RefCounted
## The one comparison of a value read from the manifest with the value it must be
## (CLAUDE.md Hard Rules 2 and 4; brief M3-R1-fix-5, M3 review R1 G-03).
##
## Godot's JSON hands a reader a Variant of any type. In GDScript `!=` between two types it
## cannot compare (a float and a String, a String and a Dictionary, an Array and a
## Dictionary, a bool and anything but a bool) is not true but a runtime error, "Invalid
## operands 'float' and 'String' in operator '!='" (brain.md H9): the function holding the
## guard stops there, the guard does not refuse, and the reader goes on to return a block it
## was meant to refuse. Two containers of the same type compare without an error whatever
## their elements hold, and null compares with every type.


## True when [param value] is not [param expected]: another type, or the same type and
## another value. An int and a float count as one type (Godot's JSON reads every number as a
## float, and 5 equals 5.0); any other two types differ. Never a runtime error, whatever the
## two hold.
static func differs(value: Variant, expected: Variant) -> bool:
	var both_numbers := _is_number(value) and _is_number(expected)
	if typeof(value) != typeof(expected) and not both_numbers:
		return true
	return value != expected


static func _is_number(value: Variant) -> bool:
	return typeof(value) == TYPE_FLOAT or typeof(value) == TYPE_INT
