; One full 360-degree base rotation.
; Profile assumptions: 1.8° motor, TMC2209 MS1/MS2 OFF/OFF = 1/8,
; 9-tooth motor pinion driving 32-tooth base gear.
; F1800 = 30 degrees/s. Completion is about 13 seconds including acceleration.
G91
G1 X360 F1800
M400
G90
