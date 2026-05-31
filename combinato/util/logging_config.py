"""
Centralized logging configuration for Combinato.

Called once from __init__.py after options are loaded and merged with
local_options.
"""
import datetime
import logging
from logging.handlers import RotatingFileHandler
import os
import warnings


# Subsystems that get their own dedicated log file
_SUBSYSTEMS = {
    'extract':    'combinato_extract.log',
    'cluster':    'combinato_cluster.log',
    'artifacts':  'combinato_cluster.log',   # shares with cluster
    'guisort':    'combinato_gui.log',
    'guioverview': 'combinato_gui.log',      # shares with guisort
}

_CATCHALL_FNAME = 'combinato.log'


class _SubsystemFilter(logging.Filter):
    """Reject records from subsystems that have their own dedicated log file."""
    def filter(self, record):
        name = record.name
        for prefix in _SUBSYSTEMS:
            if name == 'combinato.' + prefix or name.startswith('combinato.' + prefix + '.'):
                return False
        return True


class _ColoredFormatter(logging.Formatter):
    """Apply ANSI color codes to console output by component.

    Colour scheme
    ─────────────
      ·  level tag [DEBUG/INFO/…]  →  by severity
      ·  logger name                →  #32BDC8 (cyan, no relation to severity)
      ·  message text               →  by severity (same as level tag)

    File handlers keep the plain Formatter so log files are readable
    in any editor or pager.
    """
    _COLORS = {
        'DEBUG':    '\033[1;94m',    # bold bright blue
        'INFO':     '\033[1;92m',    # bold light green
        'WARNING':  '\033[1;33m',    # bold yellow
        'ERROR':    '\033[1;31m',    # bold red
        'CRITICAL': '\033[1;31m',    # bold red
    }
    _RESET = '\033[0m'
    _CYAN = '\033[36m'              # #32BDC8 approximates to ANSI 36

    def format(self, record):
        # Build message first so getMessage() is called once
        record.message = record.getMessage()
        asctime = self.formatTime(record, self.datefmt)

        level_color = self._COLORS.get(record.levelname, '')
        reset = self._RESET

        # 1) level name inside brackets — coloured by severity
        level_tag = (f'[{level_color}{record.levelname:<7}{reset}]'
                     if level_color
                     else f'[{record.levelname:<7}]')

        # 2) logger name — always cyan
        name_tag = f'{self._CYAN}{record.name}{reset}'

        # 3) message — coloured by severity
        msg = (f'{level_color}{record.message}{reset}'
               if level_color else record.message)

        parts = [f'{asctime} {level_tag} {name_tag}: {msg}']

        # Append exception / stack trace (same logic as Formatter.format)
        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            parts.append(record.exc_text)
        if record.stack_info:
            parts.append(self.formatStack(record.stack_info))

        return '\n'.join(parts)


def configure_logging(options):
    """
    Configure the Python logging framework from the Combinato options dict.

    Must be called AFTER local_options have been merged into the global
    options dict (i.e., from __init__.py).

    Produces one StreamHandler on the root 'combinato' logger for console
    output, plus per-subsystem FileHandlers:

        combinato_extract.log   — extraction pipeline
        combinato_cluster.log   — clustering, artifacts
        combinato_gui.log       — GUI (guisort, guioverview)
        combinato.log           — everything else (manager, plot, util, etc.)
    """
    # --- Resolve log level ---
    level_name = options.get('LogLevel', 'INFO').upper()
    if options.get('Debug', False):
        warnings.warn(
            "options['Debug'] is deprecated. "
            "Set options['LogLevel'] = 'DEBUG' instead.",
            DeprecationWarning, stacklevel=2,
        )
        level_name = 'DEBUG'
    level = getattr(logging, level_name, logging.INFO)

    # --- Resolve log directory ---
    ts = datetime.datetime.now().strftime('%Y%m%d')
    base = options.get('LogDir', '') or os.path.join(os.getcwd(), 'logs')
    log_dir = os.path.join(base, ts)
    max_bytes = options.get('LogMaxBytes', 5 * 1024 * 1024)
    backup_count = options.get('LogBackupCount', 3)

    # --- Build formatter ---
    fmt = options.get(
        'LogFormat',
        '%(asctime)s [%(levelname)-7s] %(name)s: %(message)s',
    )
    datefmt = options.get('LogDateFormat', '%Y-%m-%d %H:%M:%S')
    formatter = logging.Formatter(fmt, datefmt=datefmt)

    # --- Root 'combinato' logger ---
    root = logging.getLogger('combinato')
    root.setLevel(level)
    root.handlers.clear()

    # Console handler (all subsystems share this one) — with colors
    if options.get('LogToConsole', True):
        ch = logging.StreamHandler()
        ch.setLevel(level)
        ch.setFormatter(_ColoredFormatter(fmt, datefmt=datefmt))
        root.addHandler(ch)

    if options.get('LogToFile', True):
        os.makedirs(log_dir, exist_ok=True)
        mode = options.get('LogFileMode', 'a')

        # Catch-all file handler (filters out subsystem messages)
        catchall_path = os.path.join(log_dir, _CATCHALL_FNAME)
        fh_catchall = RotatingFileHandler(
            catchall_path, mode=mode,
            maxBytes=max_bytes, backupCount=backup_count,
        )
        fh_catchall.setLevel(level)
        fh_catchall.setFormatter(formatter)
        fh_catchall.addFilter(_SubsystemFilter())
        root.addHandler(fh_catchall)

        # Per-subsystem file handlers
        _configure_subsystem_handlers(level, formatter, log_dir, mode,
                                      max_bytes, backup_count)

    root.debug('Logging configured: level=%s, dir=%s',
               level_name, log_dir)


def _configure_subsystem_handlers(level, formatter, log_dir, mode,
                                  max_bytes, backup_count):
    """
    Attach a dedicated RotatingFileHandler to each subsystem's top-level logger.

    Propagation stays enabled so console output (via root's StreamHandler)
    still works.  The _SubsystemFilter on root's catch-all FileHandler
    prevents records from being duplicated into combinato.log.
    """
    # Group subsystem prefixes by their target log file name
    file_to_loggers = {}
    for prefix, fname in _SUBSYSTEMS.items():
        file_to_loggers.setdefault(fname, []).append('combinato.' + prefix)

    for fname, logger_names in file_to_loggers.items():
        fh = RotatingFileHandler(
            os.path.join(log_dir, fname), mode=mode,
            maxBytes=max_bytes, backupCount=backup_count,
        )
        fh.setLevel(level)
        fh.setFormatter(formatter)
        for name in logger_names:
            logging.getLogger(name).addHandler(fh)
