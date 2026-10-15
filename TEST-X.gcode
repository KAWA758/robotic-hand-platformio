; ONLY for this TinyBee X Motor Test firmware: M92 X15.80, no extruders.
; X is the robot base, TMC2209 in STEP/DIR standalone mode, MS1/MS2 OFF/OFF (1/8).
; 9T motor pinion drives a 32T base gear. 1 X unit = 1 degree of base rotation.
; Check M503 first: steps per unit must show X15.80.
; No homing (G28), no EEPROM write, no automatic motor release.
G91
G1 X10 F360
M400
G4 P1000
G1 X-10 F360
M400
G90
; Motor remains enabled. M18 X releases it only when mechanically supported.
