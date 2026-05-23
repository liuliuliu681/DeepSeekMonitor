# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Run

```bash
# Install dependencies
pip install -r requirements.txt

# Run directly
python main.py

# Package to single EXE
pyinstaller --onefile --windowed --name "DeepSeekMonitor" \
  --add-data "config.json;." --add-data "assets;assets" main.py
# Output: dist/DeepSeekMonitor.exe

# Or use the build script
build.bat
```

No test suite exists. Manual testing is done by launching the app and verifying:
- Balance query loops correctly
- Network error recovery (watchdog resets state after 40s)
- Animation preview buttons work repeatedly

## Architecture

```
main.py          → Entry point, creates QApplication + MainWindow
ui.py            → All UI: MainWindow, SettingsPanel, LogPanel, StatusBar,
                    BigAmountWidget, BalanceWorker (QThread)
animation.py     → BalanceAnimator: fly-away (spend) and coin-fall (income) animations + sound
api.py           → fetch_balance(): HTTP GET with 3-retry + timeout, returns dict
config.py        → load/save config.json (next to script or EXE)
logger.py        → logging setup with file handler + optional UI callback
```

## Key Design Patterns

### Watchdog + Request ID (anti-stuck mechanism)

`MainWindow.refresh_balance()` uses a 40s single-shot QTimer as a watchdog. Each request gets a monotonic `_request_id`. If the worker thread's `finished` signal never fires (Qt C-level crash, hung request), the watchdog increments `_request_id` to invalidate the pending callback and resets `_worker = None`. The next periodic timer tick starts a fresh request.

`_on_balance_result()` is wrapped in `try/finally` — the `finally` block always stops the watchdog and sets `_worker = None`, so a failed request can never permanently block the refresh cycle.

### Worker thread lifecycle

`BalanceWorker` (QThread subclass) captures config at construction and emits `finished(dict)`. The callback is a closure that compares `request_id` against `self._request_id` — stale callbacks from abandoned requests are silently dropped. `worker.deleteLater()` is called in the closure to ensure cleanup regardless of which code path triggers it.

### Animation cleanup (critical for repeatability)

`BalanceAnimator._clear()` stops all timers/animations and deletes all sprites. Every call to `_clear()` is wrapped in try/except because C++ QObjects may already be deleted by Qt's event loop (via `finished → deleteLater` chains from a previous animation cycle). `_animate_fly_away` and `_animate_coin_fall` use closure-based cleanup callbacks that remove themselves from `self._active` and `self._sprites` lists when animations finish naturally, preventing stale references.

### Config flow

Config is a flat dict loaded from `config.json` next to the EXE/script. `SettingsPanel.get_config()` reads widget values; `MainWindow._on_settings_saved()` merges them into `self.cfg`, persists to disk, restarts the refresh timer, then triggers an immediate refresh. `animations_enabled` and `sound_enabled` are pushed to the `BalanceAnimator` instance on save.

### Theme system

Two flat color dicts (`LIGHT`, `DARK`) keyed by semantic names (`accent`, `text`, `card_bg`, `error`, etc.). Each widget class has an `apply_theme(t)` method that sets its own stylesheet using f-strings. `_toggle_theme()` swaps the dict, calls `_apply_theme()` which cascades to all child widgets.

## Gotchas

- **Qt C++ object lifecycle**: Calling methods on a QObject whose C++ side has been deleted raises `RuntimeError`. Always use try/except when iterating tracked sprite/animation lists in cleanup code.
- **QApplication singleton**: Only one QApplication/QCoreApplication can exist per process. Tests that need Qt must reuse or sequence carefully.
- **Frozen path**: Use `sys._MEIPASS` when `getattr(sys, 'frozen', False)` for PyInstaller bundles. Asset paths in `animation.py` and config path in `config.py` both check this.
- **Chinese path names**: This project runs on a system with Chinese usernames/paths. All file I/O uses `os.path.abspath()` and `QUrl.fromLocalFile()` which handle Unicode paths correctly on Windows.
- **`--windowed` flag**: The EXE is built without a console window. All logging goes to `monitor.log` file and the in-app log panel.
