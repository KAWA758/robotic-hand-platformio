# TinyBee V1.0 — test bazy ramienia na X

Profil do testu silnika na wyjściu X, ze sterownikiem TMC2209. Użytkownik potwierdził nieograniczony obrót bazy. Pozostałe osie i kinematyka ramienia 4-osiowego wymagają osobnej konfiguracji.

## Ustawienia

- X_DRIVER_TYPE = TMC2209_STANDALONE: sterowanie STEP/DIR, bez UART. Prąd ustawia się na module sterownika, mikrokrok zależy od ustawień sprzętowych.
- EXTRUDERS = 0, czujniki temperatury = 0: bez ekstrudera, grzałek i wymagania podłączenia termistorów.
- Skala X: **1 jednostka = 1 impuls STEP**, nie stopień ani rzeczywisty milimetr.
- Maksymalna prędkość 100 impulsów/s, przyspieszenie 100 impulsów/s².
- Programowe limity minimum/maksimum wyłączone tylko dla X.
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

Silnik wymaga zasilania wejścia płytki zgodnego z TinyBee (12–24 V); samo USB nie zasila napędu. Przed ruchem ustaw ograniczenie prądu TMC2209 odpowiednio do silnika i konkretnego modułu. Silnik i sterownik przepinaj przy odłączonym zasilaniu.

## Pierwszy ruch

Najpierw wyślij M115 oraz M503. W M503 sprawdź **X1.00** przy M92. Jeżeli wartość jest inna, sprawdź wgrany profil przed ruchem.

Nie wysyłaj G28 — bazowanie i krańcówki nie są skonfigurowane dla ramienia.

Wysyłaj kolejno linie z TEST-X.gcode albo wpisz:

```gcode
G91
G1 X16 F600
M400
G1 X-16 F600
M400
G90
```

To 16 impulsów w jedną stronę i 16 z powrotem, z prędkością do 10 impulsów/s. Przy dużym mikrokroku/przełożeniu ruch może być ledwo widoczny. Po potwierdzeniu działania można zwiększyć liczbę impulsów, np. X160. F6000 odpowiada maksimum 100 impulsów/s.

M18 X zwalnia moment trzymający X — użyj dopiero, gdy ramię nie wymaga podtrzymania przez silnik. Test nie zwalnia napędu automatycznie.

## Docelowa skala w stopniach

Potrzebne są: kąt pełnego kroku silnika, mikrokrok oraz przełożenie (obroty silnika na obrót bazy).

impulsy/stopień = (360 / kąt_kroku_silnika) × mikrokrok × przełożenie / 360

Po zmianie M92 X... plik TEST-X.gcode przestaje oznaczać test 16 impulsów. Nie ustawiono zgadywanej skali kątowej.

## Narzędzia i wynik

VS Code 1.124.0, PlatformIO IDE 3.3.4, Auto Build Marlin 2.1.88, PlatformIO Core 6.2.0, Python 3.14.6. Baza Makerbase: Marlin 2.0.9.2, espressif32@2.1.0, partycje default_8MB.csv.

Wynik kompilacji: WYNIK-KOMPILACJI.txt. Firmware: .pio/build/mks_tinybee/firmware.bin.
Przygotowanie projektu nie uruchamia wgrywania ani ruchów silnika.

Źródło: https://github.com/makerbase-mks/MKS-TinyBee/tree/a6c038f15d6f2cbb46640158fe700755f1499c36/firmware/mks%20tinybee%20marlin

Dokumentacja:
- https://marlinfw.org/docs/gcode/G000-G001.html
- https://marlinfw.org/docs/gcode/M092.html
- https://marlinfw.org/docs/gcode/M018.html
