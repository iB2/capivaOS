: <<'CMDBLOCK'
@echo off
REM capivaOS hook dispatcher (Windows branch) — see docs/adr/0013.
REM Contract: NEVER block a session. Missing interpreter or script -> exit 0.
REM Harness hooks signal decisions via stdout JSON, never via exit codes
REM (a python "can't open file" exit 2 reads as a PreToolUse deny — the
REM CAP-001 live-fire deadlock this dispatcher exists to prevent).
setlocal
if "%~1"=="" exit /b 0
set "SCRIPT=%~dp0%~1.py"
if not exist "%SCRIPT%" exit /b 0
where py >nul 2>nul
if %ERRORLEVEL%==0 (
  py -3 "%SCRIPT%" %2 %3
  exit /b 0
)
where python >nul 2>nul
if %ERRORLEVEL%==0 (
  python "%SCRIPT%" %2 %3
  exit /b 0
)
exit /b 0
CMDBLOCK
# capivaOS hook dispatcher (POSIX branch). Same contract as above:
# never block — missing interpreter or script exits 0 silently.
[ -n "$1" ] || exit 0
HOOKDIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$HOOKDIR/$1.py"
[ -f "$SCRIPT" ] || exit 0
shift
if command -v python3 >/dev/null 2>&1; then
  python3 "$SCRIPT" "$@"
  exit 0
fi
if command -v python >/dev/null 2>&1; then
  python "$SCRIPT" "$@"
  exit 0
fi
exit 0
