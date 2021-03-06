# Copyright 2015, Tresys Technology, LLC
#
# This file is part of SETools.
#
# SETools is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# SETools is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with SETools.  If not, see <http://www.gnu.org/licenses/>.
#
import unittest

try:
    from unittest.mock import Mock, patch
except ImportError:
    from mock import Mock, patch

from setools import SELinuxPolicy
from setools.policyrep.qpol import qpol_policy_t, qpol_avrule_t, qpol_terule_t, \
                                   qpol_filename_trans_t
from setools.policyrep.terule import te_rule_factory, validate_ruletype
from setools.policyrep.exception import InvalidTERuleType, RuleNotConditional, RuleUseError, \
                                        TERuleNoFilename


@patch('setools.policyrep.boolcond.condexpr_factory', lambda x, y: y)
@patch('setools.policyrep.typeattr.type_or_attr_factory', lambda x, y: y)
@patch('setools.policyrep.objclass.class_factory', lambda x, y: y)
class AVRuleTest(unittest.TestCase):

    def mock_avrule_factory(self, ruletype, source, target, tclass, perms, cond=None):
        mock_rule = Mock(qpol_avrule_t)
        mock_rule.rule_type.return_value = ruletype
        mock_rule.source_type.return_value = source
        mock_rule.target_type.return_value = target
        mock_rule.object_class.return_value = tclass
        mock_rule.perm_iter = lambda x: iter(perms)

        if cond:
            mock_rule.cond.return_value = cond
        else:
            # this actually comes out of condexpr_factory
            # but it's simpler to have here
            mock_rule.cond.side_effect = ValueError

        return te_rule_factory(self.p, mock_rule)

    def setUp(self):
        self.p = Mock(qpol_policy_t)

    def test_000_factory(self):
        """AVRule factory lookup."""
        with self.assertRaises(TypeError):
            te_rule_factory(self.p, "INVALID")

    def test_001_validate_ruletype(self):
        """AVRule valid rule types."""
        # no return value means a return of None
        self.assertIsNone(validate_ruletype(["allow", "neverallow", "auditallow", "dontaudit"]))

    def test_002_validate_ruletype_invalid(self):
        """AVRule valid rule types."""
        with self.assertRaises(InvalidTERuleType):
            self.assertTrue(validate_ruletype("role_transition"))

    def test_010_ruletype(self):
        """AVRule rule type"""
        rule = self.mock_avrule_factory("neverallow", "a", "b", "c", ['d'])
        self.assertEqual("neverallow", rule.ruletype)

    def test_020_source_type(self):
        """AVRule source type"""
        rule = self.mock_avrule_factory("allow", "source20", "b", "c", ['d'])
        self.assertEqual("source20", rule.source)

    def test_030_target_type(self):
        """AVRule target type"""
        rule = self.mock_avrule_factory("allow", "a", "target30", "c", ['d'])
        self.assertEqual("target30", rule.target)

    def test_040_object_class(self):
        """AVRule object class"""
        rule = self.mock_avrule_factory("allow", "a", "b", "class40", ['d'])
        self.assertEqual("class40", rule.tclass)

    def test_050_permissions(self):
        """AVRule permissions"""
        rule = self.mock_avrule_factory("allow", "a", "b", "c", ['perm50a', 'perm50b'])
        self.assertSetEqual(set(['perm50a', 'perm50b']), rule.perms)

    def test_060_conditional(self):
        """AVRule conditional expression"""
        rule = self.mock_avrule_factory("allow", "a", "b", "c", ['d'], cond="cond60")
        self.assertEqual("cond60", rule.conditional)

    def test_061_unconditional(self):
        """AVRule conditional expression (none)"""
        rule = self.mock_avrule_factory("allow", "a", "b", "c", ['d'])
        with self.assertRaises(RuleNotConditional):
            rule.conditional

    def test_070_default(self):
        """AVRule default type"""
        rule = self.mock_avrule_factory("allow", "a", "b", "c", ['d'])
        with self.assertRaises(RuleUseError):
            rule.default

    def test_080_filename(self):
        """AVRule filename (none)"""
        rule = self.mock_avrule_factory("allow", "a", "b", "c", ['d'])
        with self.assertRaises(RuleUseError):
            rule.filename

    def test_100_statement_one_perm(self):
        """AVRule statement, one permission."""
        rule = self.mock_avrule_factory("allow", "a", "b", "c", ['d'])
        self.assertEqual("allow a b:c d;", rule.statement())

    def test_101_statement_two_perms(self):
        """AVRule statement, two permissions."""
        rule = self.mock_avrule_factory("allow", "a", "b", "c", ['d1', 'd2'])

        # permissions are stored in a set, so the order may vary
        self.assertRegexpMatches(rule.statement(), "("
                                 "allow a b:c { d1 d2 };"
                                 "|"
                                 "allow a b:c { d2 d1 };"
                                 ")")

    def test_102_statement_one_perm_cond(self):
        """AVRule statement, one permission, conditional."""
        rule = self.mock_avrule_factory("allow", "a", "b", "c", ['d'], cond="cond102")
        self.assertEqual("allow a b:c d; [ cond102 ]", rule.statement())

    def test_103_statement_two_perms_cond(self):
        """AVRule statement, two permissions, conditional."""
        rule = self.mock_avrule_factory("allow", "a", "b", "c", ['d1', 'd2'], cond="cond103")

        # permissions are stored in a set, so the order may vary
        self.assertRegexpMatches(rule.statement(), "("
                                 "allow a b:c { d1 d2 }; \[ cond103 ]"
                                 "|"
                                 "allow a b:c { d2 d1 }; \[ cond103 ]"
                                 ")")


@patch('setools.policyrep.boolcond.condexpr_factory', lambda x, y: y)
@patch('setools.policyrep.typeattr.type_factory', lambda x, y: y)
@patch('setools.policyrep.typeattr.type_or_attr_factory', lambda x, y: y)
@patch('setools.policyrep.objclass.class_factory', lambda x, y: y)
class TERuleTest(unittest.TestCase):

    def mock_terule_factory(self, ruletype, source, target, tclass, default, cond=None,
                            filename=None):

        if filename:
            assert not cond
            mock_rule = Mock(qpol_filename_trans_t)
            mock_rule.filename.return_value = filename

        else:
            mock_rule = Mock(qpol_terule_t)

            if cond:
                mock_rule.cond.return_value = cond
            else:
                # this actually comes out of condexpr_factory
                # but it's simpler to have here
                mock_rule.cond.side_effect = ValueError

        mock_rule.rule_type.return_value = ruletype
        mock_rule.source_type.return_value = source
        mock_rule.target_type.return_value = target
        mock_rule.object_class.return_value = tclass
        mock_rule.default_type.return_value = default

        return te_rule_factory(self.p, mock_rule)

    def setUp(self):
        self.p = Mock(qpol_policy_t)

    def test_000_factory(self):
        """TERule factory lookup."""
        with self.assertRaises(TypeError):
            te_rule_factory(self.p, "INVALID")

    def test_001_validate_ruletype(self):
        """TERule valid rule types."""
        # no return value means a return of None
        self.assertIsNone(validate_ruletype(["type_transition", "type_change", "type_member"]))

    def test_002_validate_ruletype_invalid(self):
        """TERule valid rule types."""
        with self.assertRaises(InvalidTERuleType):
            self.assertTrue(validate_ruletype("role_transition"))

    def test_010_ruletype(self):
        """TERule rule type"""
        rule = self.mock_terule_factory("type_transition", "a", "b", "c", "d")
        self.assertEqual("type_transition", rule.ruletype)

    def test_020_source_type(self):
        """TERule source type"""
        rule = self.mock_terule_factory("type_transition", "source20", "b", "c", "d")
        self.assertEqual("source20", rule.source)

    def test_030_target_type(self):
        """TERule target type"""
        rule = self.mock_terule_factory("type_transition", "a", "target30", "c", "d")
        self.assertEqual("target30", rule.target)

    def test_040_object_class(self):
        """TERule object class"""
        rule = self.mock_terule_factory("type_transition", "a", "b", "class40", "d")
        self.assertEqual("class40", rule.tclass)

    def test_050_permissions(self):
        """TERule permissions"""
        rule = self.mock_terule_factory("type_transition", "a", "b", "c", "d")
        with self.assertRaises(RuleUseError):
            rule.perms

    def test_060_conditional(self):
        """TERule conditional expression"""
        rule = self.mock_terule_factory("type_transition", "a", "b", "c", "d", cond="cond60")
        self.assertEqual("cond60", rule.conditional)

    def test_061_unconditional(self):
        """TERule conditional expression (none)"""
        rule = self.mock_terule_factory("type_transition", "a", "b", "c", "d")
        with self.assertRaises(RuleNotConditional):
            rule.conditional

    def test_070_default(self):
        """TERule default type"""
        rule = self.mock_terule_factory("type_transition", "a", "b", "c", "default70")
        self.assertEqual("default70", rule.default)

    def test_080_filename(self):
        """TERule filename"""
        rule = self.mock_terule_factory("type_transition", "a", "b", "c", "d", filename="name80")
        self.assertEqual("name80", rule.filename)

    def test_081_filename_none(self):
        """TERule filename (none)"""
        rule = self.mock_terule_factory("type_transition", "a", "b", "c", "d")
        with self.assertRaises(TERuleNoFilename):
            rule.filename

    def test_082_filename_wrong_ruletype(self):
        """TERule filename on wrong ruletype"""
        rule = self.mock_terule_factory("type_change", "a", "b", "c", "d")
        with self.assertRaises(RuleUseError):
            rule.filename

    def test_100_statement(self):
        """TERule statement."""
        rule1 = self.mock_terule_factory("type_transition", "a", "b", "c", "d")
        rule2 = self.mock_terule_factory("type_change", "a", "b", "c", "d")
        self.assertEqual("type_transition a b:c d;", rule1.statement())
        self.assertEqual("type_change a b:c d;", rule2.statement())

    def test_102_statement_cond(self):
        """TERule statement, conditional."""
        rule = self.mock_terule_factory("type_transition", "a", "b", "c", "d", cond="cond102")
        self.assertEqual("type_transition a b:c d; [ cond102 ]", rule.statement())

    def test_103_statement_filename(self):
        """TERule statement, two permissions, conditional."""
        rule = self.mock_terule_factory("type_transition", "a", "b", "c", "d", filename="name103")
        self.assertEqual("type_transition a b:c d \"name103\";", rule.statement())
