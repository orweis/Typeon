import warnings

import pytest

from typeon.utils import dataUtils, pyUtils


class TestFlatten:
    def test_nested_lists_and_tuples(self):
        assert list(dataUtils.flatten([1, [2, (3, [4])], 5])) == [1, 2, 3, 4, 5]

    def test_single_element_sequences_are_not_duplicated(self):
        assert list(dataUtils.flatten([[1], [[2]]])) == [1, 2]

    def test_empty_inputs(self):
        assert list(dataUtils.flatten([])) == []
        assert list(dataUtils.flatten([[], [[]]])) == []

    def test_strings_are_leaves_by_default(self):
        assert list(dataUtils.flatten(["ab", ["cd"]])) == ["ab", "cd"]

    def test_strings_flattened_when_requested(self):
        assert list(dataUtils.flatten(["ab", ["c"]], flattenStrings=True)) == ["a", "b", "c"]

    def test_one_char_string_terminates(self):
        assert list(dataUtils.flatten(["a"], True)) == ["a"]

    def test_bytes_are_leaves(self):
        assert list(dataUtils.flatten([b"ab", [b"c"]], True)) == [b"ab", b"c"]

    def test_non_sequence_leaves_kept(self):
        assert list(dataUtils.flatten([{1, 2}, None, 3])) == [{1, 2}, None, 3]

    def test_legacy_misspelled_keyword_warns(self):
        with pytest.warns(DeprecationWarning):
            assert list(dataUtils.flatten(["ab"], flatenStrings=True)) == ["a", "b"]

    def test_unknown_keyword_rejected(self):
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            with pytest.raises(TypeError):
                list(dataUtils.flatten([1], bogus=1))


class Sample:
    def __init__(self):
        self.a = 1
        self.b = 2

    def total(self):
        return self.a + self.b


class SampleRepr(dataUtils.GenericProxy):
    def __init__(self, target):
        self._proxyWrap(target)

    def __repr__(self):
        return "a==%s b==%s" % (self.a, self.b)

    def own(self):
        return "own"


class TestGenericProxy:
    def test_attribute_and_method_access_passes_through(self):
        proxy = SampleRepr(Sample())
        assert (proxy.a, proxy.b, proxy.total()) == (1, 2, 3)
        assert repr(proxy) == "a==1 b==2"

    def test_own_members_stay_on_wrapper(self):
        assert SampleRepr(Sample()).own() == "own"

    def test_wrapped_object_reachable(self):
        target = Sample()
        assert SampleRepr(target).getWrappedObject() is target

    def test_missing_attribute_raises_attribute_error(self):
        with pytest.raises(AttributeError):
            SampleRepr(Sample()).nope

    def test_unwrapped_proxy_behaves_like_plain_object(self):
        class Bare(dataUtils.GenericProxy):
            pass

        with pytest.raises(AttributeError):
            Bare().anything


class TestPyStack:
    def test_lists_this_file_and_frame_names(self):
        stack = pyUtils.PyStack()
        assert any(m.endswith("test_utils.py") for m in stack.listModules())
        assert stack.listFrameNames()[0] == "test_lists_this_file_and_frame_names"
        assert "->" in repr(stack) or repr(stack) == ""
