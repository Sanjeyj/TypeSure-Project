# TypeSure — Personal Custom Dictionary Architecture & Security Documentation

## 1. Purpose & Overview

The TypeSure Personal Dictionary system allows authenticated users to save custom Tamil vocabulary, technical jargon, proper nouns, institutional names, and domain-specific terminology.

Any word saved to a user's personal dictionary is seamlessly integrated into the TypeSure recognition engine during their spell checking sessions, ensuring that custom or specialized terms are never flagged as errors.

---

## 2. Security Architecture & Data Isolation

### Cryptographic & Per-User Isolation Principles:
1. **Per-User Isolation**:
   Every personal dictionary entry is permanently tied to an authenticated `user_id` foreign key referencing the `users` table:
   ```sql
   CREATE TABLE personal_words (
       id          INTEGER PRIMARY KEY AUTOINCREMENT,
       user_id     INTEGER NOT NULL,
       word        TEXT NOT NULL,
       notes       TEXT,
       created_at  TEXT NOT NULL,
       UNIQUE(user_id, word),
       FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
   );
   ```
2. **Access Control (Authorization)**:
   All personal dictionary endpoints strictly enforce `@login_required`. In every database query, `WHERE user_id = ?` is enforced with parameterized SQL queries, preventing cross-tenant leakage or enumeration attacks.
3. **No Unauthenticated Leaks**:
   Guest users cannot view or modify any personal dictionary records.

---

## 3. RESTful API Specification

| HTTP Method | Route | Description | Request Body / Query | Success Response |
|---|---|---|---|:---:|
| `GET` | `/api/personal-dictionary` | List & search user's custom words | `?q=...&page=1&limit=50` | `200 OK` (JSON) |
| `POST` | `/api/personal-dictionary` | Add a single word to personal dictionary | `{"word": "...", "notes": "..."}` | `201 Created` |
| `PUT` | `/api/personal-dictionary/<id>` | Update notes for a personal word | `{"notes": "..."}` | `200 OK` |
| `DELETE` | `/api/personal-dictionary/<id>` | Remove a word from personal dictionary | None | `200 OK` |
| `POST` | `/api/personal-dictionary/import` | Bulk import words (.txt or JSON) | Multi-part `.txt` or JSON `{words}` | `200 OK` |
| `GET` | `/api/personal-dictionary/export` | Download dictionary (.txt or .csv) | `?format=txt` or `?format=csv` | File download |

---

## 4. Integration with Spellchecker

When an authenticated user submits text to `/api/check`:
1. The session extracts `user_id = session.get("user_id")`.
2. `typesure/spellchecker.py` retrieves the user's personal vocabulary set using `get_personal_word_set(user_id)`.
3. During the 7-stage recognition hierarchy, any token matching the user's personal words is classified as `PERSONAL_DICTIONARY_WORD` with `status: "ok"`.
4. In the text editor UI, unrecognized words offer a 1-click **"+ Add to Personal Dict"** button, instantly saving the word without requiring the user to switch screens.
