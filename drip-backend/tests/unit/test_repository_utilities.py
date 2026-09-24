"""Repository helpers must not force database versions or ship fixed accounts."""
from unittest.mock import Mock

import fix_migration


def test_migration_helper_defaults_to_read_only(monkeypatch):
    current, upgrade = Mock(), Mock()
    monkeypatch.setattr(fix_migration.command, 'current', current)
    monkeypatch.setattr(fix_migration.command, 'upgrade', upgrade)
    assert fix_migration.main([]) == 0
    current.assert_called_once()
    upgrade.assert_not_called()


def test_migration_upgrade_requires_explicit_option(monkeypatch):
    upgrade = Mock()
    monkeypatch.setattr(fix_migration.command, 'upgrade', upgrade)
    assert fix_migration.main(['--upgrade', '--sql']) == 0
    assert upgrade.call_args.args[1] == 'head'
    assert upgrade.call_args.kwargs == {'sql': True}
