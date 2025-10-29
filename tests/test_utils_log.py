import logging
from pathlib import Path

from generative_agents.modules.utils.log import create_io_logger, create_file_logger, block_msg, split_line


def test_create_io_logger_levels_and_methods(capsys):
    # String level parsing
    logger = create_io_logger('info')
    logger.info('hello')
    captured = capsys.readouterr().out
    assert 'hello' in captured

    # debug requires level <= DEBUG
    logger_debug = create_io_logger('debug')
    logger_debug.debug('dbg')
    assert 'dbg' in capsys.readouterr().out


def test_create_file_logger_and_helpers(tmp_path: Path):
    log_file = tmp_path / 'app.log'
    logger = create_file_logger(str(log_file), 'info')
    logger.info('line1')
    assert log_file.exists()

    # calling twice should not duplicate handlers
    logger2 = create_file_logger(str(log_file), 'info')
    assert logger2 is not None

    line = split_line('TITLE', '-')
    assert 'TITLE' in line and line.count('-') > 0

    formatted = block_msg('TT', {'a': 1})
    assert 'a:' in formatted


def test_invalid_level_raises():
    import pytest
    with pytest.raises(Exception):
        create_io_logger('invalid-level')
