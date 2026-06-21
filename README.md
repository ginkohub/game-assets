# Game Assets

Indonesian puzzle game assets for:

| Game | Description | Questions |
|------|-------------|-----------|
| **Tebak Gambar** | Guess the Picture | 1,000 (50 levels, 20 each) |
| **Tebak Kata** | Guess the Word | 302 |
| **Susun Kata** | Arrange the Word | 356 |
| **Asah Otak** | Brain Teaser | 228 |
| **Cak Lontong** | Wordplay / Joke Game | 414 |

## Structure

```
├── tebak-gambar/
│   └── data.json          # Questions + answers + URLs
├── tebak-kata/data.json   # Clue-based word puzzles
├── susun-kata/data.json   # Scrambled letters by category
├── asah-otak/data.json    # General knowledge trivia
└── cak-lontong/data.json  # Misleading questions with pun answers
```

- **Total files:** 5 JSON data files

## Data Format

### tebak-gambar
```json
{
  "1": [
    { "img": "url.jpg", "jawaban": "answer", "deskripsi": "hint" }
  ]
}
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

### cak-lontong
```json
{ "soal": "question", "jawaban": "answer", "deskripsi": "humorous explanation" }
```

## Notice

All assets belong to their respective owners. This repository is for educational/personal use only.
