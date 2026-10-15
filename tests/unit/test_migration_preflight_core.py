"""Source-level migration manifest regressions; never opens production connections."""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import subprocess
import sys

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / 'bot_core/scripts/check_migration_versions.py'
spec = importlib.util.spec_from_file_location('zina_migration_guard', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def chain(tmp_path, *names):
    root = tmp_path / 'migrations'
    root.mkdir()
    for name in names:
        (root / name).write_text('-- test migration\n')
    return root


def manifest(root, *names):
    return [f'{name}\t{hashlib.sha256((root / name).read_bytes()).hexdigest()}' for name in names]


def test_valid_chain(tmp_path):
    root = chain(tmp_path, '001_init.sql', '002_more.sql', '003_final.sql')
    assert module.validate_migrations(root) == []
    assert module.validate_migrations(root, applied_manifest=manifest(root, '001_init.sql', '002_more.sql')) == []


def test_collision_rejected(tmp_path):
    root = chain(tmp_path, '001_init.sql', '002_a.sql', '002_b.sql')
    assert any('duplicate migration version 002' in e for e in module.validate_migrations(root))


def test_missing_checkout_number_rejected(tmp_path):
    root = chain(tmp_path, '001_init.sql', '003_final.sql')
    assert any('missing migration version 002' in e for e in module.validate_migrations(root))


def test_changed_installed_filename_rejected(tmp_path):
    root = chain(tmp_path, '001_init.sql', '002_new.sql')
    assert any('changed filename' in e for e in module.validate_migrations(root, applied_versions=['001_init.sql', '002_old.sql']))


def test_missing_installed_file_rejected(tmp_path):
    root = chain(tmp_path, '001_init.sql')
    assert any('missing from checkout' in e for e in module.validate_migrations(root, applied_versions=['001_init.sql', '002_old.sql']))


def test_missing_installed_prefix_rejected(tmp_path):
    root = chain(tmp_path, '001_init.sql', '002_more.sql', '003_final.sql')
    assert any('not a contiguous prefix' in e for e in module.validate_migrations(root, applied_versions=['001_init.sql', '003_final.sql']))
    assert any('not a contiguous prefix' in e for e in module.validate_migrations(root, applied_versions=['002_more.sql']))


def test_changed_checksum_rejected(tmp_path):
    root = chain(tmp_path, '001_init.sql')
    good = manifest(root, '001_init.sql')[0]
    assert module.validate_migrations(root, applied_manifest=[good]) == []
    assert any('checksum mismatch' in e for e in module.validate_migrations(root, applied_manifest=['001_init.sql\t' + '0'*64]))


@pytest.mark.parametrize('row', ['001_init.sql', '001_init.sql\tgarbage', '001_init.sql\t' + 'a'*63, 'bad\t' + 'a'*64])
def test_malformed_manifest_rejected(tmp_path, row):
    root = chain(tmp_path, '001_init.sql')
    assert module.validate_migrations(root, applied_manifest=[row])


def test_duplicate_installed_rows_rejected(tmp_path):
    root = chain(tmp_path, '001_init.sql')
    row = manifest(root, '001_init.sql')[0]
    assert any('duplicate installed migration manifest' in e for e in module.validate_migrations(root, applied_manifest=[row, row]))


def test_missing_directory_rejected(tmp_path):
    assert any('missing' in e for e in module.validate_migrations(tmp_path / 'none'))


def test_symlink_migration_rejected(tmp_path):
    root = chain(tmp_path, '001_init.sql')
    (root / '002_more.sql').symlink_to(root / '001_init.sql')
    assert any('regular file' in e for e in module.validate_migrations(root))


def test_cli_returns_failure_on_checksum_drift(tmp_path):
    root = chain(tmp_path, '001_init.sql')
    run = subprocess.run([sys.executable, str(SCRIPT), str(root), '--applied-manifest-stdin'], input='001_init.sql\t' + '0'*64 + '\n', text=True, capture_output=True)
    assert run.returncode == 1
    assert 'checksum mismatch' in run.stderr


def test_cli_accepts_valid_manifest(tmp_path):
    root = chain(tmp_path, '001_init.sql')
    run = subprocess.run([sys.executable, str(SCRIPT), str(root), '--applied-manifest-stdin'], input=manifest(root, '001_init.sql')[0] + '\n', text=True, capture_output=True)
    assert run.returncode == 0


def test_cli_rejects_both_manifest_formats(tmp_path):
    root = chain(tmp_path, '001_init.sql')
    run = subprocess.run([sys.executable, str(SCRIPT), str(root), '--applied-manifest-stdin', '--applied-versions-stdin'], text=True, capture_output=True)
    assert run.returncode != 0
