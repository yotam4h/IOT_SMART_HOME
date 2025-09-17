:: arg: Name Units Place UpdateTime

@echo off
setlocal

:: Windows helper to launch the Smart Pet Feeder demo stack.
:: Mirrors start_emulators.sh: tank/tray emulators, feeder device, manager, GUI.

:: Allow overriding Python executable (default: python)
if "%SMARTPETFEEDER_PYTHON%"=="" (
    set "SMARTPETFEEDER_PYTHON=python"
)

:: Allow configurable gaps between launches to avoid broker rate limits
if "%SMARTPETFEEDER_LAUNCH_GAP%"=="" (
    set "SMARTPETFEEDER_LAUNCH_GAP=4"
)
if "%SMARTPETFEEDER_GUI_DELAY%"=="" (
    set "SMARTPETFEEDER_GUI_DELAY=6"
)

:: helper to start a process then sleep for the requested delay
:: usage: call :launch 4 "Title" "cmd" args...
goto launch_calls

:launch
setlocal
set "_delay=%~1"
set "_title=%~2"
if "%_title%"=="" goto launch_end
shift
shift
echo Starting: %_title%
start "%_title%" %*
if defined _delay (
    if not "%_delay%"=="0" (
        timeout /t %_delay% /nobreak >nul
    )
)
:launch_end
endlocal
exit /b

:launch_calls

:: Launch tank/tray level emulators (name units topic-suffix update-interval)
call :launch %SMARTPETFEEDER_LAUNCH_GAP% "Emulator: FoodTank-1" "%SMARTPETFEEDER_PYTHON%" -m smart_pet_feeder.tank_tray_emulator FoodTank-1 N food-1 5
call :launch %SMARTPETFEEDER_LAUNCH_GAP% "Emulator: WaterTank-1" "%SMARTPETFEEDER_PYTHON%" -m smart_pet_feeder.tank_tray_emulator WaterTank-1 N water-1 5
call :launch %SMARTPETFEEDER_LAUNCH_GAP% "Emulator: FoodTray-1" "%SMARTPETFEEDER_PYTHON%" -m smart_pet_feeder.tank_tray_emulator FoodTray-1 N foodtray-1 5
call :launch %SMARTPETFEEDER_LAUNCH_GAP% "Emulator: WaterTray-1" "%SMARTPETFEEDER_PYTHON%" -m smart_pet_feeder.tank_tray_emulator WaterTray-1 N watertray-1 5

:: Feeder actuator emulator (handles relay + dispense commands)
call :launch %SMARTPETFEEDER_LAUNCH_GAP% "Feeder Emulator" "%SMARTPETFEEDER_PYTHON%" -m smart_pet_feeder.feeder_emulator feeder

:: Manager collects MQTT data into SQLite and emits alarms
call :launch %SMARTPETFEEDER_GUI_DELAY% "PetFeeder Manager" "%SMARTPETFEEDER_PYTHON%" -m smart_pet_feeder.manager

:: GUI dashboard (PyQt)
call :launch %SMARTPETFEEDER_GUI_DELAY% "System GUI" "%SMARTPETFEEDER_PYTHON%" -m smart_pet_feeder.app_gui

echo All Smart Pet Feeder components started. Close their windows or use Task Manager to stop them.
endlocal
