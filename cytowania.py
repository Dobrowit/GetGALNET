#!/usr/bin/python3

import os
import re
import sys

def przetworz_tresc(zawartosc):
    akapity = re.split(r'\n\s*\n', zawartosc)
    wynik = []

    for akapit in akapity:
        akapit = akapit.strip()
        if not akapit:
            continue

        # Czy akapit zaczyna się od cudzysłowu i kończy kropką lub cudzysłowem?
        if re.match(r'^["„]', akapit) and akapit.endswith(('.', '”', '"')):
            wynik.append(f"> {akapit}")
        else:
            wynik.append(akapit)

    return '\n\n'.join(wynik)

def przetworz_plik(sciezka, preview=False):
    with open(sciezka, 'r', encoding='utf-8') as f:
        zawartosc = f.read()

    nowa_zawartosc = przetworz_tresc(zawartosc)

    if zawartosc == nowa_zawartosc:
        return  # brak zmian

    if preview:
        print("=" * 80)
        print(f"PLIK: {sciezka}")
        print("-" * 80)
        print("ORYGINAŁ:\n")
        print(zawartosc)
        print("-" * 80)
        print("PO ZMIANIE:\n")
        print(nowa_zawartosc)
        print("=" * 80)
        input("Naciśnij Enter, aby kontynuować...")
    else:
        with open(sciezka, 'w', encoding='utf-8') as f:
            f.write(nowa_zawartosc)

def przetworz_folder(folder, preview=False):
    for root, _, files in os.walk(folder):
        for nazwa_pliku in files:
            if nazwa_pliku.endswith('.md'):
                pelna_sciezka = os.path.join(root, nazwa_pliku)
                przetworz_plik(pelna_sciezka, preview)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Użycie: ./skrypt.py <ścieżka_do_katalogu> [--preview]")
        sys.exit(1)

    katalog = sys.argv[1]
    preview = '--preview' in sys.argv

    przetworz_folder(katalog, preview)
