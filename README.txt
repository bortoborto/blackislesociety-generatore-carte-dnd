# Carte incantesimo 5E (regole 2024) in italiano

Generatore di carte incantesimo stampabili, in italiano, per le regole 2024 della quinta edizione (quelle del System Reference Document 5.2.1, spesso chiamate informalmente "5.5"). A partire da un CSV crea PDF in formato A3 con 25 carte per foglio, pronti per la stampa fronte/retro, in due layout: **scuro** e **chiaro**. Può anche creare una cartella per ogni classe, con fronte e retro nei colori di quella classe.

![Anteprima dei retri per classe](docs/anteprima_retri_classe.png)

## Caratteristiche

- **Formato di stampa:** 25 carte per foglio A3 (5 × 5), circa 55 × 80 mm l'una, con le linee di taglio. Ogni pagina di fronte è seguita dal suo retro.
- **Due layout:** scuro, fedele al design originale, e chiaro, che consuma molto meno inchiostro.
- **Carta completa:** simbolo della scuola, livello, gittata, durata, tempo di lancio, componenti, rituale e classi.
- **Evidenziazioni nel testo:** dadi, tipi di danno, tiri salvezza e distanze sono colorati.
- **Diagrammi automatici:** gittata e area d'effetto (sfera, cono, cubo, linea, emanazione) sono disegnate su una griglia da 1,5 m.
- **Adattamento del testo:** la descrizione completa viene rimpicciolita finché entra nella carta. Se non entra comunque, la carta usa la descrizione breve.
- **Modalità per classe:** una cartella per ogni classe, con fronte tinto e retro dedicato nel colore della classe.

## Struttura del progetto

```
.
├── genera_carte.py                # lo script
├── incantesimi_srd_5.2.1_it.csv   # dati degli incantesimi (SRD 5.2.1)
├── assets/                        # icone (scuole, statistiche, classi) e motivo del retro
├── fonts/                         # font Ubuntu + licenza UFL
└── docs/                          # immagini per questo README
```

## Requisiti

- Python 3.9 o superiore
- [ReportLab](https://pypi.org/project/reportlab/) e [Pillow](https://pypi.org/project/Pillow/)

```bash
pip install reportlab pillow
```

## Uso

```bash
# PDF scuro e chiaro con tutte le carte
python genera_carte.py incantesimi_srd_5.2.1_it.csv

# Tutto in una volta: PDF completi + una cartella per classe
python genera_carte.py incantesimi_srd_5.2.1_it.csv --per-classe --out-dir carte
```

Risultato con `--per-classe`:

```
carte/
├── carte_scure_A3.pdf
├── carte_chiare_A3.pdf
├── Bardo/
│   ├── carte_scure_A3.pdf
│   └── carte_chiare_A3.pdf
├── Chierico/
├── Druido/
├── Paladino/
├── Ranger/
├── Stregone/
├── Warlock/
└── Mago/
```

### Edizione Black Isle Society

Versione dedicata all'associazione [Black Isle Society](https://blackislesociety.com/) di Imola:

- fronte in **bianco e nero**, con le evidenziazioni rese in grassetto, e fronte **chiaro**;
- retro **nero** con il logo al centro di ogni carta.

Salva il logo in `assets/logo_bis.png`, poi lancia:

```bash
python genera_carte.py incantesimi_srd_5.2.1_it.csv --bis
```

Se il logo è scuro, viene reso bianco in automatico per risaltare sul nero.

### Opzioni

| Opzione | Effetto |
| --- | --- |
| `--out-dir CARTELLA` | Cartella in cui salvare i PDF (default: cartella corrente) |
| `--testo auto\|completo\|breve` | Testo sulle carte. `auto` (default) usa il completo se entra, altrimenti il breve |
| `--solo scuro\|chiaro` | Genera un solo layout |
| `--classe NOME` | Solo gli incantesimi di una classe (es. `mago`) |
| `--per-classe` | Crea anche una cartella per ogni classe |
| `--solo-classi` | Come `--per-classe`, ma senza i PDF con tutte le carte |
| `--fronte-standard` | Nei PDF per classe usa il fronte nei colori normali |
| `--retro-standard` | Nei PDF per classe usa il retro normale |
| `--bis` | Edizione Black Isle Society: fronte in bianco e nero e in versione chiara, retro nero con il logo |
| `--logo PERCORSO` | Logo per il retro dell'edizione `--bis` (default `assets/logo_bis.png`) |
| `--senza-retro` | Non inserisce le pagine del retro |
| `--senza-diagrammi` | Non disegna i diagrammi di gittata e area |

A fine esecuzione lo script elenca le carte che usano la descrizione breve perché il testo completo non entrava.

## Formato del CSV

File UTF-8, separatore virgola, una riga per incantesimo. Nella descrizione i paragrafi sono separati da un a capo dentro la cella, e i sottotitoli si scrivono in stile markdown (`**Titolo.**`).

| Colonna | Contenuto | Esempio |
| --- | --- | --- |
| `nome` | Nome dell'incantesimo | Palla di fuoco |
| `livello` | 0–9 (0 = trucchetto) | 3 |
| `livello_testo` | Livello in forma testuale | 3º livello |
| `scuola` | Abiurazione, Ammaliamento, Divinazione, Evocazione, Illusione, Invocazione, Necromanzia, Trasmutazione | Invocazione |
| `classi` | Classi separate da virgola | Mago, Stregone |
| `tempo_di_lancio` | Testo completo, con l'eventuale innesco | azione |
| `tempo_di_lancio_breve` | Azione, Azione bonus, Reazione, 1 minuto… | Azione |
| `rituale` | Sì / No | No |
| `gittata` | Testo della gittata | 45 metri |
| `componenti` | V, S, M | V, S, M |
| `materiale` | Componente materiale | una pallina di guano di pipistrello e zolfo |
| `durata` | Testo della durata | istantanea |
| `concentrazione` | Sì / No | No |
| `descrizione_breve` | Riassunto per il tavolo | Sfera di 6 m: TS Destrezza, 8d6 danni da fuoco… |
| `descrizione_completa` | Testo integrale | … |
| `livelli_superiori` | Effetto con slot superiori | I danni aumentano di 1d6… |
| `trucchetto_potenziato` | Miglioramento dei trucchetti | … |

Colonne facoltative: `fonte`, `da_verificare`, `note`. Lo script le ignora, ma sono utili per tenere traccia dei dati.

## Stampa

- Stampa in A3, **fronte/retro sul lato lungo**, al 100% e senza adattamento alla pagina.
- Nei PDF per classe i retri sono disposti a specchio, così che ogni retro cada dietro la sua carta.
- Per carte più resistenti, usa un cartoncino da 250–300 g/m², oppure stampa su carta normale e inserisci le carte in bustine protettive insieme a una carta da gioco.

## Personalizzazione

- **Colori delle classi:** sono nel dizionario `COLORI_CLASSE` in `genera_carte.py`.
- **Temi scuro e chiaro:** colori di sfondo, testo ed evidenziazioni sono nel dizionario `THEMES`.
- **Icone:** si possono sostituire i PNG in `assets/` mantenendo gli stessi nomi.
- **Geometria:** dimensioni delle carte e margini sono in costanti in testa allo script (`CARD_W`, `CARD_H`, `PITCH_X`…).

## Licenze e attribuzioni

Il testo degli incantesimi proviene dal System Reference Document 5.2.1 in italiano, rilasciato con licenza CC-BY-4.0. Come richiesto dalla licenza:

> Quest'opera include materiale tratto dal System Reference Document 5.2.1 ("SRD 5.2.1") di Wizards of the Coast LLC, disponibile all'indirizzo https://www.dndbeyond.com/srd. Il SRD 5.2.1 è concesso in licenza ai sensi della licenza di attribuzione 4.0 Internazionale di Creative Commons, disponibile all'indirizzo https://creativecommons.org/licenses/by/4.0/legalcode.

Questo progetto non è affiliato a Wizards of the Coast né approvato da essa. È un materiale compatibile con la quinta edizione: "5.5" non è un nome ufficiale, perché le regole 2024 restano la quinta edizione. Per questo il SRD consente solo le diciture "compatibile con la quinta edizione" o "compatibile con 5E".

- **Font:** [Ubuntu](https://design.ubuntu.com/font), Ubuntu Font Licence 1.0 (vedi `fonts/UFL.txt`).
- **Codice:** _scegli una licenza, per esempio MIT, e aggiungi il file `LICENSE`._