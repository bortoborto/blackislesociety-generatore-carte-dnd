# Carte incantesimo 5E (regole 2024) in italiano

Generatore di carte incantesimo stampabili, in italiano, per le regole 2024 della quinta edizione: quelle del System Reference Document 5.2.1, spesso chiamate informalmente "5.5". A partire da un CSV crea PDF pronti per la stampa fronte/retro.

Il progetto offre due formati:

- **Poker:** carte da 63 × 88 mm, la misura delle carte di Magic. Ogni carta ha una cornice grafica illustrata e il logo della [Black Isle Society](https://blackislesociety.com/) nel piede. È disponibile in tre versioni: scura, chiara e bianco e nero.
- **Classico A3:** carte da circa 55 × 80 mm, 25 per foglio, nel layout originale scuro o in una variante chiara. Può avere fronte e retro nei colori di ciascuna classe.

![Anteprima delle carte in formato poker](docs/anteprima_poker.png)

## Indice

- [Caratteristiche](#caratteristiche)
- [Requisiti](#requisiti)
- [Avvio rapido](#avvio-rapido)
- [Formato poker](#formato-poker)
- [Formato classico A3](#formato-classico-a3)
- [Tutte le opzioni](#tutte-le-opzioni)
- [Formato del CSV](#formato-del-csv)
- [Stampa](#stampa)
- [Personalizzazione](#personalizzazione)
- [Struttura del progetto](#struttura-del-progetto)
- [Licenze e attribuzioni](#licenze-e-attribuzioni)

## Caratteristiche

- **Carta completa:** simbolo della scuola, livello in numeri romani, gittata, durata, tempo di lancio, componenti, rituale e classi.
- **Testo leggibile al tavolo:** dadi, tipi di danno, tiri salvezza e distanze sono evidenziati a colori, o in grassetto nella versione bianco e nero.
- **Righe aggiuntive:** il componente materiale, l'innesco per reazioni e punizioni, e un riquadro per gli effetti con slot di livello superiore o per il potenziamento dei trucchetti.
- **Diagrammi automatici:** gittata e area d'effetto (sfera, cono, cubo, linea, emanazione) sono disegnate su una griglia a caselle da 1,5 m.
- **Rimando alla fonte:** in fondo alla descrizione compare la pagina dell'SRD in cui leggere il testo ufficiale, per esempio "SRD 5.2.1 · p. 171".
- **Adattamento del testo:** la descrizione completa viene rimpicciolita finché entra nella carta. Se non entra comunque, la carta usa una descrizione breve pensata per il tavolo.
- **Cartelle per classe:** si può generare una cartella per ogni classe, con i PDF dei soli incantesimi di quella classe.

## Requisiti

- Python 3.9 o superiore
- [ReportLab](https://pypi.org/project/reportlab/) e [Pillow](https://pypi.org/project/Pillow/)

```bash
pip install reportlab pillow
```

## Avvio rapido

```bash
# Formato poker, A3 con 16 carte per foglio: versioni scura, chiara e bianco e nero
python genera_carte.py incantesimi_srd_5.2.1_it.csv --poker

# Formato classico A3: versioni scura e chiara
python genera_carte.py incantesimi_srd_5.2.1_it.csv
```

A fine esecuzione lo script elenca le carte che usano la descrizione breve.

## Formato poker

```bash
python genera_carte.py incantesimi_srd_5.2.1_it.csv --poker                 # A3, 16 carte per foglio
python genera_carte.py incantesimi_srd_5.2.1_it.csv --poker --foglio A4     # A4, 9 carte per foglio
python genera_carte.py incantesimi_srd_5.2.1_it.csv --poker --solo chiaro   # una sola versione
python genera_carte.py incantesimi_srd_5.2.1_it.csv --poker --solo-bn       # solo bianco e nero
```

| Versione | File | Fronte | Retro |
| --- | --- | --- | --- |
| Scura | `carte_poker_scure_A3.pdf` | Cornice scura, testo chiaro, evidenziazioni a colori | Nero |
| Chiara | `carte_poker_chiare_A3.pdf` | Cornice color pergamena, testo scuro | Color pergamena (`#e7e4db`) |
| Bianco e nero | `carte_poker_bianco_nero_A3.pdf` | Fondo bianco, filetti e testo in nero puro, evidenziazioni in grassetto | Nero |

Note sul formato:

- **Carta:** 63 × 88 mm, con 3 mm di abbondanza per lato. Le carte sono distanziate di 6 mm, con i segni di taglio sui margini del foglio.
- **Logo:** viene preso da `assets/logo_bis.png` e inserito nel cartiglio ovale del piede. Se il file manca, lo script prova a scaricarlo dal sito della Black Isle Society.
- **Retro nero:** nella versione bianco e nero il retro e i neri della cornice sono nero puro (RGB 0/0/0). Con `--nero-k` il retro viene scritto come CMYK 0/0/0/100.
- **Per classe:** funziona anche con `--per-classe` e `--solo-classi`, con la stessa cornice per tutte le classi.

## Formato classico A3

Carte da 157 × 226,5 pt (circa 55 × 80 mm), 25 per foglio A3, nel layout originale.

```bash
python genera_carte.py incantesimi_srd_5.2.1_it.csv                                  # scuro + chiaro
python genera_carte.py incantesimi_srd_5.2.1_it.csv --per-classe --out-dir carte     # + una cartella per classe
python genera_carte.py incantesimi_srd_5.2.1_it.csv --bis                            # edizione Black Isle Society
```

- **Per classe:** con `--per-classe` ogni cartella ha il fronte tinto e il retro dedicato nel colore della classe, con simbolo e nome.
- **Edizione Black Isle Society:** con `--bis` il fronte è in bianco e nero o in versione chiara, e il retro è nero con il logo al centro di ogni carta.

Con `--per-classe` il risultato è questo:

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

## Tutte le opzioni

| Opzione | Effetto |
| --- | --- |
| `--out-dir CARTELLA` | Cartella in cui salvare i PDF (default: cartella corrente) |
| `--poker` | Formato poker 63 × 88 mm con cornice grafica, logo e retro a tinta unita |
| `--foglio A3\|A4` | Foglio per `--poker`: A3 con 16 carte, A4 con 9 carte |
| `--solo scuro\|chiaro` | Genera una sola versione |
| `--solo-bn` | Con `--poker`, genera solo la versione bianco e nero |
| `--testo auto\|completo\|breve` | Testo sulle carte. `auto` (default) usa il completo se entra, altrimenti il breve |
| `--classe NOME` | Solo gli incantesimi di una classe (es. `mago`) |
| `--per-classe` | Crea anche una cartella per ogni classe |
| `--solo-classi` | Come `--per-classe`, ma senza i PDF con tutte le carte |
| `--fronte-standard` | Formato classico per classe: fronte nei colori normali |
| `--retro-standard` | Formato classico per classe: retro normale |
| `--bis` | Formato classico, edizione Black Isle Society |
| `--logo PERCORSO` | Logo da usare (default `assets/logo_bis.png`) |
| `--nero-k` | Con `--poker`, retro nero come CMYK 0/0/0/100 invece di RGB 0/0/0 |
| `--senza-pagina` | Non stampa il rimando "SRD 5.2.1 · p. N" |
| `--senza-diagrammi` | Non disegna i diagrammi di gittata e area |
| `--senza-retro` | Non inserisce le pagine del retro |

Le opzioni si possono combinare, per esempio `--poker --foglio A4 --solo chiaro --per-classe`.

## Formato del CSV

File UTF-8 (anche con BOM), separatore virgola, una riga per incantesimo. Nella descrizione i paragrafi sono separati da un a capo dentro la cella, e i sottotitoli si scrivono in stile markdown (`**Titolo.**`).

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
| `pagina_srd` | Pagina dell'SRD 5.2.1 italiano in cui inizia l'incantesimo | 171 |
| `fonte` | Facoltativa: provenienza del dato | SRD 5.2.1 |
| `da_verificare` | Facoltativa: Sì / No | No |
| `note` | Facoltativa: appunti sui dati | … |

Le colonne obbligatorie sono `nome`, `livello`, `scuola`, `classi`, `gittata`, `durata`, `componenti` e `descrizione_breve`; le altre si possono lasciare vuote.

Le descrizioni brevi sono riassunti scritti per questo progetto: sono utili al tavolo, ma il testo di riferimento resta quello dell'SRD indicato da `pagina_srd`.

## Stampa

- **Impostazioni:** stampa fronte/retro **sul lato lungo**, al 100% e senza adattamento alla pagina. I retri sono disposti a specchio, così che ognuno cada dietro la sua carta.
- **Prova:** stampa prima un foglio e controllalo controluce. Sul cartoncino spesso il fronte/retro può sfasarsi di 1–2 mm.
- **Carta:** per carte da tenere in mano senza bustine, usa un cartoncino patinato opaco da 300 g/m². Le stampanti di casa spesso non superano i 220–256 g/m². Con bustine protettive bastano 120–160 g/m², con una carta da gioco dietro come supporto.
- **Bustine:** il formato poker ha la stessa misura delle carte di Magic, quindi vanno bene le bustine "standard size" (circa 66 × 91 mm), i deck box e i raccoglitori da 9 tasche.
- **Nero:** per i retri neri pieni chiedi alla copisteria se preferisce un nero ricco (il file standard) o solo inchiostro nero (`--nero-k`).
- **Taglio:** usa una taglierina. Una fustella arrotonda-angoli da 3–4 mm segue gli angoli della cornice.

## Personalizzazione

- **Cornici poker:** sono in `assets/cornice_scura.png`, `cornice_chiara.png` e `cornice_bn.png`, con dimensione 815 × 1110 px (69 × 94 mm a 300 dpi, abbondanze comprese). Le posizioni dei riquadri sono nei dizionari `Z_ORNATA` (scura e bianco e nero) e `Z_CHIARA` dello script: se cambi una cornice, aggiorna le coordinate.
- **Colori:** i temi del formato classico sono nel dizionario `THEMES`, i colori delle classi in `COLORI_CLASSE`, i retri poker in `PK_RETRO`.
- **Icone:** si possono sostituire i PNG in `assets/` mantenendo gli stessi nomi.
- **Geometria del formato classico:** è nelle costanti in testa allo script (`CARD_W`, `CARD_H`, `PITCH_X`…).

## Struttura del progetto

```
.
├── genera_carte.py                # lo script
├── incantesimi_srd_5.2.1_it.csv   # dati dei 339 incantesimi dell'SRD 5.2.1
├── assets/
│   ├── cornice_*.png              # cornici del formato poker
│   ├── logo_bis.png               # logo Black Isle Society
│   ├── retro.jpg                  # motivo del retro (formato classico)
│   ├── scuola_*.png               # simboli delle scuole di magia
│   ├── classe_*.png               # simboli delle classi
│   └── ...                        # icone di gittata, durata, tempo, componenti
├── fonts/                         # font Ubuntu + licenza UFL
├── docs/                          # immagini per questo README
└── LEGGIMI.txt                    # istruzioni rapide
```

## Licenze e attribuzioni

Il testo degli incantesimi proviene dal System Reference Document 5.2.1 in italiano, rilasciato con licenza CC-BY-4.0. Come richiesto dalla licenza:

> Quest'opera include materiale tratto dal System Reference Document 5.2.1 ("SRD 5.2.1") di Wizards of the Coast LLC, disponibile all'indirizzo https://www.dndbeyond.com/srd. Il SRD 5.2.1 è concesso in licenza ai sensi della licenza di attribuzione 4.0 Internazionale di Creative Commons, disponibile all'indirizzo https://creativecommons.org/licenses/by/4.0/legalcode.

Questo progetto non è affiliato a Wizards of the Coast né approvato da essa. È un materiale compatibile con la quinta edizione: "5.5" non è un nome ufficiale, perché le regole 2024 restano la quinta edizione. Per questo il SRD consente solo le diciture "compatibile con la quinta edizione" o "compatibile con 5E".

- **Dati:** il repository contiene solo gli incantesimi dell'SRD. Gli incantesimi presenti esclusivamente nel *Manuale del Giocatore* non sono coperti dalla licenza CC-BY e non vanno pubblicati.
- **Logo:** il logo Black Isle Society appartiene all'associazione ed è incluso con il suo permesso.
- **Cornici:** le cornici del formato poker sono state generate con [Magnific](https://magnific.ai/) per questo progetto.
- **Font:** [Ubuntu](https://design.ubuntu.com/font), Ubuntu Font Licence 1.0 (vedi `fonts/UFL.txt`).
- **Codice:** _scegli una licenza, per esempio MIT, e aggiungi il file `LICENSE`._