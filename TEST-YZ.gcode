; Safe first-motion test for Y and Z.
; Assumes 1 unit = 1 degree and 30 degrees/s maximum speed.
; Do not run this until the arm has free, safe travel around its current position.
G91
G1 Y5 F360
M400
G1 Y-5 F360
M400
G1 Z5 F360
M400
G1 Z-5 F360
M400
G90
