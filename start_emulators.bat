:: arg: Name Units Place UpdateTime

@echo off
setlocal

:: Windows helper to launch the Smart Pet Feeder demo stack.
:: Mirrors start_emulators.sh: tank/tray emulators, feeder device, manager, GUI.

:: Allow overriding Python executable (default: python)
if "%SMARTPETFEEDER_PYTHON%"=="" (
    set "SMARTPETFEEDER_PYTHON=python"
)

:: Launch tank/tray level emulators (name units topic-suffix update-interval)
start "Emulator: FoodTank-1" %SMARTPETFEEDER_PYTHON% -m smart_pet_feeder.tank_tray_emulator FoodTank-1 N food-1 5
timeout 2 >nul
start "Emulator: WaterTank-1" %SMARTPETFEEDER_PYTHON% -m smart_pet_feeder.tank_tray_emulator WaterTank-1 N water-1 5
timeout 2 >nul
start "Emulator: FoodTray-1" %SMARTPETFEEDER_PYTHON% -m smart_pet_feeder.tank_tray_emulator FoodTray-1 N foodtray-1 5
timeout 2 >nul
start "Emulator: WaterTray-1" %SMARTPETFEEDER_PYTHON% -m smart_pet_feeder.tank_tray_emulator WaterTray-1 N watertray-1 5
timeout 2 >nul

:: Feeder actuator emulator (handles relay + dispense commands)
start "Feeder Emulator" %SMARTPETFEEDER_PYTHON% -m smart_pet_feeder.feeder_emulator feeder
timeout 2 >nul

:: Manager collects MQTT data into SQLite and emits alarms
start "PetFeeder Manager" %SMARTPETFEEDER_PYTHON% -m smart_pet_feeder.manager
timeout 5 >nul

:: GUI dashboard (PyQt)
start "System GUI" %SMARTPETFEEDER_PYTHON% -m smart_pet_feeder.app_gui

echo All Smart Pet Feeder components started. Close their windows or use Task Manager to stop them.
endlocal
