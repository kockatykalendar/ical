<p align="center">
	<a href="https://kockatykalendar.sk/">
		<h1 align="center">KockatýKalendár.ics</h1>
	</a>
	<p align="center">📎 Kockatý Kalendár vo formáte iCal</p>
</p>


## Inštalácia

Generátor `.ics` súborov je naprogramovaný v Pythone 3, potrebné knižnice sa dajú nainštalovať zo súboru `requirements.txt`.
    
    pip install -r requirements.txt


## Používanie

    python build.py
    
Vygeneruje iCal zo všetkých udalostí z kalendára pre aktuálny školský rok a vypíše ho na štandardný výstup.

### Možnosti

- `-d URL`, `--data-source URL` - možnosť určiť iný JSON súbor ako zdroj dát. Predvolene používame aktuálny školský rok
    z https://data.kockatykalendar.sk.
- `-a`, `--all` -Vygeneruje ical pre každú kombináciu typu školy, vedy a organizátora a uloží do priečinku `build`.
- `--school X` - filtrovanie udalostí podľa typu školy. Povolené hodnoty sú `zs`, `ss` a `any`. Predvolená hodnota je `any`,
    teda sa budú zobrazovať udalosti pre všetky školy.
- `--science X` - filtrovanie udalostí podľa vied. Povolené hodnoty sú `mat`, `fyz`, `inf`, `other` a `any`.
    Pre tento parameter je možné uviesť viac hodnôt v tvare `--science mat fyz`. 
    Predvolená hodnota je `any`, teda sa budú zobrazovať udalosti všetkých vied.
- `--organizer X` - filtrovanie udalostí podľa organizátorov. Povolené hodnoty sú `trojsten`, `p-mat`, `sezam`, `riesky`, `strom`, `siov`, `iuventa`, `matfyz`.
    Pre tento parameter je možné uviesť viac hodnôt v tvare `--science trojsten p-mat`.
    Predvolená hodnota je `any`, teda sa budú zobrazovať udalosti všetkých organizátorov.
- `-o FILE`, `--output FILE` - určuje, kam sa má uložiť výsledný súbor. Predvolená hodnota je `-`, teda štandardný výstup.
