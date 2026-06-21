# Game Assets

Indonesian puzzle game assets for:

| Game | Description | Questions |
|------|-------------|-----------|
| **Tebak Gambar** | Guess the Picture | 1,000 (50 levels, 20 each) |
| **Tebak Kata** | Guess the Word | 302 |
| **Susun Kata** | Arrange the Word | 356 |
| **Asah Otak** | Brain Teaser | 228 |
| **Tebak Negara** | Guess the Country | 194 |
| **Cak Lontong** | Wordplay / Joke Game | 414 |
| **Sambung Kata** | Chain Word Game | 71,332 |
| **Family 100** | Survey / Family Feud Game | 7,162 |

## Structure

```
├── tebak-gambar/
│   ├── data.json          # Questions + answers + URLs
│   └── images/            # Downloaded level images
├── tebak-kata/
│   └── data.json          # Clue-based word puzzles
├── susun-kata/
│   └── data.json          # Scrambled letters by category
├── tebak-negara/
│   ├── data.json          # Country data with capital + region
│   ├── images/            # Flag images
│   └── scrape.py          # Data scraper
├── asah-otak/
│   └── data.json          # General knowledge trivia
├── sambung-kata/
│   └── data.txt           # Word list (one per line)
├── family-100/
│   └── data.json          # Survey questions with multiple answers
└── cak-lontong/
    └── data.json          # Misleading questions with pun answers
```

- **Total files:** 7 JSON + 1 TXT data files

## Data Format

### tebak-gambar
```json
{
  "1": [
    { "img": "url.jpg", "jawaban": "answer", "deskripsi": "hint" }
  ]
}
```

### tebak-negara
```json
{ "bendera": "images/indonesia.png", "negara": "Indonesia", "wilayah": "Asia", "ibukota": "Jakarta" }
```

### tebak-kata
```json
{ "soal": "clue1,clue2,clue3", "jawaban": "answer" }
```

### susun-kata
```json
{ "soal": "scrambled", "tipe": "category", "jawaban": "answer" }
```

### asah-otak
```json
{ "soal": "question", "jawaban": "answer" }
```

### family-100
```json
{ "soal": "Pertanyaan survey", "jawaban": ["jawaban1", "jawaban2", ...] }
```

### cak-lontong
```json
{ "soal": "question", "jawaban": "answer", "deskripsi": "humorous explanation" }
```

## Notice

All assets belong to their respective owners. This repository is for educational/personal use only.
