extends GutTest
## Pinning tests for brief M3-R1-fix-5 (M3 review R1 G-03): ManifestValue.differs, the one
## comparison of a manifest value with the value it must be.
##
## Pinned decisions: differs(value, expected) is true when the two have another type or, with the
## same type, another value, and false when they are equal; an int and a float are one type
## (Godot's JSON reads every number as a float, and 5 equals 5.0). It is never a runtime error:
## every pair of the values below is compared, among them every pair of types that `!=` itself
## cannot compare (a float and a String, a String and a Dictionary, an Array and a Dictionary, a
## bool and a number), and the test fails on any error the run prints (GUT counts an engine error
## as a failure) as well as on a wrong answer. The pairs are symmetric: differs(a, b) equals
## differs(b, a).
##
## Does NOT prove: that the readers call it at every site (test_m3_r1_fix5_type_guards.gd does,
## site by site).

## [name, value]: two values with one name are equal, any two with other names differ. A
## container is compared by content, so two lists or two objects with the same content are one name.
var _values := [
	["null", null],
	["true", true],
	["false", false],
	["five", 5],
	["five", 5.0],
	["six", 6.0],
	["minus", -5.0],
	["text x", "x"],
	["text y", "y"],
	["empty text", ""],
	["list of a float", [1.0]],
	["list of a float", [1.0]],
	["list of a text", ["x"]],
	["empty list", []],
	["object with a float", {"a": 1.0}],
	["object with a float", {"a": 1.0}],
	["object with a text", {"a": "x"}],
	["object in an object", {"a": {"b": 1.0}}],
	["empty object", {}],
]


func test_differs_is_false_for_equal_values_and_true_for_every_other_pair() -> void:
	var wrong := []
	for one: Array in _values:
		for other: Array in _values:
			var expected: bool = one[0] != other[0]
			if ManifestValue.differs(one[1], other[1]) != expected:
				wrong.append("%s and %s" % [JSON.stringify(one[1]), JSON.stringify(other[1])])
	assert_eq(wrong, [], "every pair of %d values is told as it is" % _values.size())
	assert_eq(get_errors().size(), 0, "and no pair is a runtime error")


func test_an_int_and_a_float_of_the_same_number_do_not_differ() -> void:
	assert_false(ManifestValue.differs(5, 5.0), "5 is 5.0")
	assert_false(ManifestValue.differs(5.0, 5), "5.0 is 5")
	assert_true(ManifestValue.differs(5, 6.0), "5 is not 6.0")
	assert_true(ManifestValue.differs(5.0, 6), "5.0 is not 6")


func test_a_number_and_a_text_of_it_differ() -> void:
	# A guard that compared after converting to text would accept this.
	assert_true(ManifestValue.differs(5.0, "5.0"), "the number 5.0 is not the text 5.0")
	assert_true(ManifestValue.differs("5.0", 5.0), "the text 5.0 is not the number 5.0")
	assert_true(ManifestValue.differs(1.0, true), "the number 1.0 is not true")
	assert_true(ManifestValue.differs(true, 1.0), "true is not the number 1.0")
