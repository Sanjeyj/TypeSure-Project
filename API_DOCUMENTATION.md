# TypeSure — REST API Specification (v2.0)

Base URL: `http://localhost:5000` (Local) / `https://type-sure-project.vercel.app` (Production)

---

## 1. Authentication & Session Headers

TypeSure provides session-isolated history tracking. Clients can pass a custom session token or rely on the automatic signed session cookie.

| Header | Type | Description |
| :--- | :--- | :--- |
| `X-Session-ID` | String (Optional) | Client-defined session token (up to 64 chars) for history isolation. |
| `Content-Type` | String | Must be `application/json` for JSON POST endpoints. |

---

## 2. Endpoints

### 2.1 Check Spelling
Performs Unicode NFC normalization, grapheme-aware tokenization, dictionary verification, morphological suffix analysis, and BK-tree candidate retrieval.

- **Route**: `POST /api/check`
- **Headers**: `Content-Type: application/json`, `X-Session-ID: <session_uuid>` (optional)
- **Request Body**:
```json
{
  "text": "வணககம். நான் தமழ் படிகிறேன்.",
  "store_text": false,
  "corrections": 0,
  "method": "bktree"
}
```

- **Response (200 OK)**:
```json
{
  "check_id": 14,
  "session_id": "9a8b7c6d5e4f3a2b1c0d",
  "timestamp": "2026-11-10T16:30:00.000000Z",
  "spans": [
    {
      "text": "வணககம்",
      "start": 0,
      "end": 6,
      "is_tamil": true,
      "is_english": false,
      "is_word": true,
      "status": "unknown"
    },
    {
      "text": ". ",
      "start": 6,
      "end": 8,
      "is_tamil": false,
      "is_english": false,
      "is_word": false
    }
  ],
  "issues": [
    {
      "word": "வணககம்",
      "occurrences": 1,
      "span_indices": [0],
      "has_suggestions": true,
      "suggestions": [
        {
          "word": "வணக்கம்",
          "distance": 2,
          "weighted_distance": 1.0,
          "confidence": 0.56,
          "score": 0.45
        }
      ]
    }
  ],
  "stats": {
    "total_words_scanned": 4,
    "issues_found": 3,
    "recognized": 1,
    "morphology_recognized": 0,
    "dictionary_coverage_pct": 25.0,
    "dictionary_size": 436,
    "processing_time_ms": 2.45,
    "search_method": "bktree"
  }
}
```

---

### 2.2 History Management

#### Get History
- **Route**: `GET /api/history?limit=20`
- **Response (200 OK)**:
```json
{
  "session_id": "9a8b7c6d5e4f3a2b1c0d",
  "history": [
    {
      "id": 14,
      "session_id": "9a8b7c6d5e4f3a2b1c0d",
      "created_at": "2026-11-10T16:30:00Z",
      "word_count": 4,
      "issue_count": 3,
      "corrections": 0,
      "store_text": 0,
      "input_text": null
    }
  ],
  "summary": {
    "total_checks": 1,
    "total_words": 4,
    "total_issues": 3,
    "total_corrections": 0
  }
}
```

#### Clear History (Session Scoped)
- **Route**: `DELETE /api/history`
- **Response (200 OK)**:
```json
{
  "deleted": 1,
  "message": "History cleared for session."
}
```

#### Delete Single History Record
- **Route**: `DELETE /api/history/<int:record_id>`
- **Response (200 OK)**:
```json
{
  "success": true,
  "deleted_id": 14
}
```

---

### 2.3 Dictionary Management

#### Import Word List
Uploads a UTF-8 text file with one Tamil word per line.
- **Route**: `POST /api/dictionary/import`
- **Headers**: `Content-Type: multipart/form-data`
- **Body**: Form field `file` containing `.txt` file (Max 2 MB / 50,000 words).
- **Response (200 OK)**:
```json
{
  "added": 120,
  "duplicates": 15,
  "invalid": 2,
  "errors": [
    "Line 42: 'computer' has no Tamil characters, skipped."
  ]
}
```

#### Dictionary & DB Statistics
- **Route**: `GET /api/stats`
- **Response (200 OK)**:
```json
{
  "dictionary": {
    "total_words": 436,
    "starter_words": 423,
    "imported_words": 13,
    "bktree_nodes": 436
  },
  "database": {
    "total_checks": 25,
    "total_words": 148,
    "total_issues": 32,
    "total_corrections": 18
  }
}
```

---

### 2.4 Algorithm Benchmark
Empirically benchmarks linear length-filtered candidate search against BK-Tree metric retrieval.
- **Route**: `GET /api/benchmark?word=வணககம்`
- **Response (200 OK)**:
```json
{
  "query_word": "வணககம்",
  "dictionary_size": 436,
  "bktree_nodes": 436,
  "bktree": {
    "time_ms": 1.45,
    "candidates_found": 1
  },
  "linear_length_filtered": {
    "time_ms": 2.85,
    "candidates_found": 1
  },
  "speedup_factor": 1.97
}
```

---

### 2.5 Report Generation
- **Route**: `GET /api/report?format=csv` (or `format=txt`)
- **Response**: Binary stream with `Content-Disposition: attachment; filename="typesure_report_YYYYMMDD_HHMMSS.csv"`.

---

### 2.6 Health Probe
- **Route**: `GET /healthz`
- **Response (200 OK)**:
```json
{
  "app": "TypeSure",
  "status": "ok",
  "version": "2.0.0",
  "dictionary_size": 436
}
```
