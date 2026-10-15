# TinyBee V1.0 — test ramienia na osiach X/Y/Z

Profil do płynnego ruchu trzech silników ramienia na wyjściach X, Y i Z ze sterownikami TMC2209. X steruje bazą i może obracać się bez ograniczenia. Y oraz Z należy najpierw sprawdzić krótkim ruchem, gdy mechanika ma bezpieczny zakres.

## Ustawienia

- X/Y/Z_DRIVER_TYPE = TMC2209_STANDALONE: sterowanie STEP/DIR, bez UART. Prąd ustawia się na module sterownika, mikrokrok zależy od ustawień sprzętowych.
- EXTRUDERS = 0, czujniki temperatury = 0: bez ekstrudera, grzałek i wymagania podłączenia termistorów.
- Ustaw DIP: **MS1 OFF, MS2 ON, MS3 OFF** na każdym używanym TMC2209. To wybiera 1/64 mikrokroku na TinyBee i zmniejsza widoczność pojedynczych kroków.
- Skala X/Y/Z: **1 jednostka = 1 stopień obrotu osi**, przy założeniu silnika 1,8°, mikrokroku 1/64 i przełożeniu 9:32.
- Maksymalna prędkość 30°/s i przyspieszenie 15°/s² dla każdej osi, dla łagodniejszego startu i zatrzymania.
- Programowe limity minimum/maksimum są wyłączone; nie wysyłaj długich ruchów Y/Z przed ustaleniem mechanicznych zakresów.
- Brak automatycznego zwalniania silników po bezczynności.
- EEPROM wyłączony, aby stare ustawienia drukarki nie zastępowały testowej skali. M500 nie jest potrzebne; zmiany M92 nie przetrwają restartu.
- USB 115200, Flash 8 MB, środowisko mks_tinybee.
- Wyłączone Wi-Fi/ESP3D, ekran, karta SD oraz Linear Advance.

## Kompilacja i wgranie

Otwórz TinyBee.code-workspace z folderu nadrzędnego.

1. Ctrl+Shift+B: TinyBee: Build.
2. Podłącz płytkę kablem USB obsługującym transmisję danych.
3. Terminal → Run Task → TinyBee: Lista portow USB.
4. Terminal → Run Task → TinyBee: Upload USB.
5. Po wgraniu: TinyBee: Monitor 115200.

Ostrzeżenia PlatformIO o przestarzałym `src_filter` w innych profilach Marlina
nie dotyczą środowiska `mks_tinybee` i nie blokują kompilacji ani wgrywania.

Wykryta płytka używa portu COM3, który ustawiono jako upload_port i monitor_port. Zamknij monitor przed wgrywaniem.

Silnik wymaga zasilania wejścia płytki zgodnego z TinyBee (12–24 V); samo USB nie zasila napędu. Przed zmianą DIP całkowicie odłącz zasilanie płytki. Przed ruchem ustaw ograniczenie prądu TMC2209 odpowiednio do silnika i konkretnego modułu. Silnik i sterownik przepinaj przy odłączonym zasilaniu.

## Pierwszy ruch

Najpierw wyślij M115 oraz M503. W M503 sprawdź **X126.42 Y126.42 Z126.42** przy M92. Jeżeli wartości są inne, sprawdź wgrany profil przed ruchem.

Nie wysyłaj G28 — bazowanie i krańcówki nie są skonfigurowane dla ramienia.

Najpierw wyślij kolejno linie z `TEST-YZ.gcode`; testuje każdą z nowych osi o 5° w obie strony. Dla X użyj `TEST-X.gcode`.

Przykład ręcznego testu Y:

```gcode
G91
G1 Y5 F360
M400
G1 Y-5 F360
M400
G90
```

To 5° w jedną stronę i 5° z powrotem, z prędkością 6°/s. Po potwierdzeniu działania można zwiększać odległość stopniowo. F1800 odpowiada maksimum 30°/s.

M18 X, M18 Y lub M18 Z zwalnia moment trzymający danej osi — użyj dopiero, gdy ramię nie wymaga podtrzymania przez silnik. Test nie zwalnia napędów automatycznie.

## Docelowa skala w stopniach

Potrzebne są: kąt pełnego kroku silnika, mikrokrok oraz przełożenie (obroty silnika na obrót osi).

impulsy/stopień = (360 / kąt_kroku_silnika) × mikrokrok × przełożenie / 360

Obecna skala 126,41975 kroku/° wynika z: 200 pełnych kroków/obrót × 1/64 × 32/9 ÷ 360. Jeżeli Y lub Z mają inne przełożenie albo ustawienie DIP, zmień wyłącznie ich wartość w M92 i później w `DEFAULT_AXIS_STEPS_PER_UNIT`.

## Narzędzia i wynik

VS Code 1.124.0, PlatformIO IDE 3.3.4, Auto Build Marlin 2.1.88, PlatformIO Core 6.2.0, Python 3.14.6. Baza Makerbase: Marlin 2.0.9.2, espressif32@2.1.0, partycje default_8MB.csv.

Wynik kompilacji: WYNIK-KOMPILACJI.txt. Firmware: .pio/build/mks_tinybee/firmware.bin.
Przygotowanie projektu nie uruchamia wgrywania ani ruchów silnika.

Źródło: https://github.com/makerbase-mks/MKS-TinyBee/tree/a6c038f15d6f2cbb46640158fe700755f1499c36/firmware/mks%20tinybee%20marlin

Dokumentacja:
- https://marlinfw.org/docs/gcode/G000-G001.html
- https://marlinfw.org/docs/gcode/M092.html
- https://marlinfw.org/docs/gcode/M018.html
