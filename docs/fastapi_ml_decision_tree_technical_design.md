# Dokumentasi Teknis Backend FastAPI
## Platform Analisis Dataset dan Decision Tree Berbasis Konfigurasi

**Versi:** 1.0  
**Tanggal:** 31 Juli 2026  
**Target implementasi:** Python FastAPI, PostgreSQL, SQLAlchemy, Alembic, scikit-learn

---

## 1. Tujuan

Dokumen ini menjadi acuan implementasi backend untuk aplikasi analisis dataset tabular yang:

- menerima file CSV dan Excel;
- melakukan profiling dan memberikan rekomendasi konfigurasi JSON;
- mengizinkan konfigurasi diedit, divalidasi, disimpan, dan diberi versi;
- menjalankan preprocessing serta Decision Tree Classification;
- menyimpan hasil setiap tahap secara terstruktur;
- menampilkan hasil aktual Confusion Matrix, Accuracy, Precision, Recall, F1-Score, Decision Tree, feature importance, aturan keputusan, dan prediksi data testing;
- menyediakan kontrak API yang stabil untuk frontend modern;
- menjaga keterlacakan dan reproduktibilitas setiap eksperimen.

Sistem bersifat **configuration-driven**. Backend tidak bergantung pada nama kolom tertentu. Dataset baru diproses berdasarkan konfigurasi JSON yang telah dikonfirmasi pengguna.

### 1.1 Cakupan MVP

- Dataset tabular `.csv`, `.xlsx`, dan `.xls`.
- Satu sheet aktif per versi dataset.
- Supervised binary atau multiclass classification.
- Decision Tree Classifier.
- Train/test split dengan opsi stratifikasi.
- Preprocessing numerik, kategorikal, dan ordinal.
- Evaluasi klasifikasi lengkap.
- Visualisasi dan laporan berbasis data hasil backend.

### 1.2 Di luar cakupan MVP

- Gambar, audio, video, dan natural-language dataset.
- Time-series khusus.
- Unsupervised learning.
- Distributed training.
- Model serving untuk trafik prediksi produksi berskala besar.
- Decision Tree Regression; disiapkan sebagai pengembangan berikutnya.

---

## 2. Prinsip desain

1. **Dataset tidak diubah secara permanen.** Semua transformasi disimpan sebagai konfigurasi, log, atau artifact turunan.
2. **Konfigurasi tidak sama dengan model.** JSON adalah instruksi pipeline; model terlatih disimpan sebagai artifact `.joblib`.
3. **Setiap run immutable.** Perubahan konfigurasi menghasilkan versi dan run baru.
4. **Tidak ada data leakage.** Imputer dan encoder hanya di-fit memakai data training.
5. **Output frontend bersifat framework-neutral.** Backend mengirim data visualisasi, bukan HTML.
6. **Hasil dapat direproduksi.** Dataset checksum, konfigurasi, versi library, random state, dan model artifact dicatat.
7. **Rekomendasi otomatis tetap memerlukan konfirmasi.** Target, positive class, ordinal order, identifier, dan leakage tidak boleh ditetapkan diam-diam.
8. **Proses panjang bersifat asinkron.** API mengembalikan `202 Accepted`; worker menyelesaikan profiling, training, dan report generation.

---

## 3. Arsitektur sistem

```mermaid
flowchart TB
    FE["Frontend Nuxt/Vue"] --> API["FastAPI REST API"]
    API --> DB["PostgreSQL"]
    API --> OBJ["Object Storage"]
    API --> Q["Task Queue"]
    Q --> W["ML Worker"]
    W --> DB
    W --> OBJ
```

### 3.1 Komponen

| Komponen | Tanggung jawab |
|---|---|
| FastAPI | REST API, validasi request, otorisasi, orkestrasi workflow |
| PostgreSQL | Metadata, konfigurasi, status, metrik, tree nodes, dan prediksi |
| Object storage | File dataset, model, grafik, JSON, Excel, DOCX, dan PDF |
| Task queue | Antrean proses profiling, training, evaluasi, dan laporan |
| ML worker | pandas, scikit-learn, plotting, serialization |
| Redis | Broker queue, cache, distributed lock, progress event |
| Frontend | Editor konfigurasi, wizard tahap, tabel dan visualisasi interaktif |

### 3.2 Rekomendasi teknologi

- Python 3.12.
- FastAPI dan Uvicorn.
- PostgreSQL 18.
- SQLAlchemy 2.x async.
- Alembic.
- Pydantic 2.x dan pydantic-settings.
- pandas, NumPy, scikit-learn.
- openpyxl untuk `.xlsx`; xlrd hanya bila `.xls` diwajibkan.
- Celery + Redis untuk produksi; FastAPI `BackgroundTasks` hanya untuk pekerjaan ringan.
- MinIO atau storage S3-compatible.
- joblib untuk model artifact.
- matplotlib dan Graphviz/pydot untuk ekspor pohon.
- pytest dan pytest-asyncio.

---

## 4. Struktur proyek FastAPI

```text
app/
├── main.py
├── core/
│   ├── config.py
│   ├── database.py
│   ├── security.py
│   ├── logging.py
│   └── task_queue.py
├── middleware/
│   ├── cors.py
│   ├── request_id.py
│   ├── exception_handler.py
│   └── timing.py
├── support/
│   ├── responses.py
│   ├── exceptions.py
│   ├── pagination.py
│   ├── file_storage.py
│   ├── checksums.py
│   └── enums.py
├── modules/
│   ├── projects/
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── repository.py
│   │   ├── service.py
│   │   └── routes.py
│   ├── datasets/
│   ├── profiling/
│   ├── configurations/
│   ├── experiments/
│   ├── training/
│   ├── evaluation/
│   ├── visualization/
│   ├── artifacts/
│   └── reports/
├── ml/
│   ├── schema_detector.py
│   ├── config_recommender.py
│   ├── validators.py
│   ├── data_loader.py
│   ├── cleaning.py
│   ├── pipeline_builder.py
│   ├── splitter.py
│   ├── trainer.py
│   ├── evaluator.py
│   ├── tree_exporter.py
│   ├── rule_extractor.py
│   └── importance_analyzer.py
├── workers/
│   ├── profiling_tasks.py
│   ├── experiment_tasks.py
│   └── report_tasks.py
└── tests/
    ├── unit/
    ├── integration/
    └── fixtures/
alembic/
requirements.txt
.env.example
```

Setiap modul mengikuti pemisahan `routes → service → repository → models`. Logika ML tidak ditempatkan dalam route atau model SQLAlchemy.

---

## 5. Workflow aplikasi

```mermaid
flowchart TD
    A["Upload dataset"] --> B["Validasi file"]
    B --> C["Profiling kolom"]
    C --> D["Rekomendasi JSON"]
    D --> E["Edit dan validasi"]
    E --> F["Simpan versi konfigurasi"]
    F --> G["Jalankan eksperimen"]
    G --> H["Evaluasi dan artifact"]
    H --> I["Tampilkan atau ekspor hasil"]
```

### 5.1 State dataset

`UPLOADED → VALIDATING → PROFILED → READY → INVALID → ARCHIVED`

### 5.2 State konfigurasi

`DRAFT → VALIDATING → VALID → ACTIVE → SUPERSEDED → INVALID`

### 5.3 State experiment run

`QUEUED → RUNNING → COMPLETED | FAILED | CANCELLED`

### 5.4 Tahap dalam run

1. `load_dataset`
2. `validate_config`
3. `cleaning`
4. `split_data`
5. `fit_preprocessor`
6. `transform_data`
7. `train_model`
8. `predict_test`
9. `evaluate_model`
10. `extract_tree`
11. `calculate_importance`
12. `generate_artifacts`

---

## 6. Konfigurasi JSON

### 6.1 Contoh konfigurasi kanonis

```json
{
  "schema_version": "1.0",
  "dataset": {
    "dataset_id": "8531b851-8665-4099-8f01-16ca42f44da9",
    "sheet_name": "Data Mahasiswa",
    "header_row": 1
  },
  "task": {
    "type": "classification",
    "target_column": "IPK_baik",
    "positive_class": "Ya"
  },
  "columns": [
    {
      "name": "nim",
      "data_type": "text",
      "role": "identifier",
      "enabled": false
    },
    {
      "name": "durasi_medsos_jam",
      "data_type": "numeric",
      "role": "feature",
      "enabled": true
    },
    {
      "name": "program_studi",
      "data_type": "categorical",
      "role": "feature",
      "enabled": true,
      "encoding": "one_hot"
    },
    {
      "name": "semester",
      "data_type": "ordinal",
      "role": "feature",
      "enabled": true,
      "encoding": "ordinal",
      "categories": [1, 2, 3, 4, 5, 6, 7, 8]
    },
    {
      "name": "IPK_baik",
      "data_type": "categorical",
      "role": "target",
      "enabled": true
    }
  ],
  "cleaning": {
    "remove_duplicates": true,
    "drop_constant_columns": true,
    "target_missing_strategy": "drop_row"
  },
  "preprocessing": {
    "numeric_missing": "median",
    "categorical_missing": "most_frequent",
    "categorical_encoding": "one_hot",
    "handle_unknown": "ignore"
  },
  "split": {
    "method": "train_test",
    "test_size": 0.2,
    "stratify": true,
    "random_state": 42
  },
  "model": {
    "algorithm": "decision_tree_classifier",
    "criterion": "gini",
    "splitter": "best",
    "max_depth": 4,
    "min_samples_split": 2,
    "min_samples_leaf": 5,
    "max_features": null,
    "class_weight": null,
    "ccp_alpha": 0.0,
    "random_state": 42
  },
  "evaluation": {
    "zero_division": 0,
    "permutation_importance": true,
    "permutation_repeats": 10
  }
}
```

### 6.2 Rekomendasi otomatis

`config_recommender.py` menghasilkan draf berdasarkan:

- dtype pandas dan keberhasilan parsing;
- unique count dan unique ratio;
- missing ratio;
- cardinality;
- pola nama identifier seperti `id`, `uuid`, `nim`, `kode`, `nomor`;
- nilai yang monoton atau hampir seluruhnya unik;
- target candidate dengan kardinalitas rendah;
- pola nama target yang dikonfigurasi;
- class distribution;
- kemungkinan tipe ordinal atau tanggal.

Setiap rekomendasi menyertakan bukti:

```json
{
  "column": "nim",
  "recommended_role": "identifier",
  "confidence": 0.98,
  "reasons": [
    "unique_ratio=1.0",
    "nama kolom cocok dengan pola identifier"
  ],
  "requires_confirmation": false
}
```

Target yang direkomendasikan selalu `requires_confirmation=true`.

### 6.3 Versioning

- Draf dapat disimpan berulang pada versi yang sama selama belum digunakan run.
- Saat pengguna memilih **Save as New Version**, backend membuat row immutable baru.
- Konfigurasi yang sudah digunakan run tidak boleh dimutasi.
- Aktivasi versi menggunakan transaksi dan hanya satu konfigurasi aktif per dataset/eksperimen.
- Simpan `config_hash` berbasis JSON kanonis untuk mendeteksi duplikasi.

---

## 7. Validasi dataset dan konfigurasi

### 7.1 Validasi upload

- Extension dan MIME harus diizinkan.
- Batas ukuran file ditentukan lewat konfigurasi.
- Nama file dibersihkan dan tidak digunakan sebagai storage key.
- File diperiksa sebagai ZIP bomb untuk `.xlsx`.
- Workbook harus dapat dibaca.
- Minimal satu sheet dan satu baris data.
- Header harus unik setelah normalisasi.
- Formula tidak dieksekusi oleh backend.
- File disimpan dengan UUID dan checksum SHA-256.

### 7.2 Validasi sebelum training

**Error yang menghentikan proses:**

- target tidak ditemukan atau lebih dari satu;
- target juga digunakan sebagai fitur;
- tidak ada fitur aktif;
- target hanya memiliki satu kelas;
- positive class tidak ada pada data;
- kolom konfigurasi tidak ditemukan;
- kategori ordinal tidak memiliki urutan;
- `test_size` tidak menyediakan sampel tiap kelas;
- parameter model di luar rentang;
- nilai target hilang tanpa strategi;
- hasil cleaning menjadi kosong.

**Warning yang membutuhkan perhatian:**

- class imbalance;
- possible identifier dipakai sebagai fitur;
- high-cardinality categorical feature;
- kemungkinan leakage;
- missing ratio tinggi;
- duplicate rows;
- kelas testing sangat kecil;
- kolom konstan;
- target candidate berconfidence rendah.

### 7.3 Format respons validasi

```json
{
  "valid": false,
  "errors": [
    {
      "path": "task.target_column",
      "code": "COLUMN_NOT_FOUND",
      "message": "Kolom IPK_bagus tidak ditemukan."
    }
  ],
  "warnings": [
    {
      "path": "columns.nim",
      "code": "POSSIBLE_IDENTIFIER",
      "message": "Kolom NIM memiliki 100% nilai unik."
    }
  ]
}
```

---

## 8. Pipeline machine learning

### 8.1 Urutan yang benar

1. Baca dataset dan pilih sheet.
2. Pisahkan target `y` dan fitur `X`.
3. Terapkan cleaning yang aman pada level baris.
4. Buat train/test split.
5. Fit imputer dan encoder hanya pada `X_train`.
6. Transform `X_train` dan `X_test`.
7. Fit Decision Tree memakai training set.
8. Prediksi testing set.
9. Hitung Confusion Matrix dan metrik.
10. Ekstrak tree, rules, dan feature importance.
11. Simpan model, hasil, dan metadata reproduksi.

### 8.2 Pipeline scikit-learn

```python
numeric_pipeline = Pipeline(
    steps=[
        ("imputer", SimpleImputer(strategy="median"))
    ]
)

categorical_pipeline = Pipeline(
    steps=[
        ("imputer", SimpleImputer(strategy="most_frequent")),
        (
            "encoder",
            OneHotEncoder(
                handle_unknown="ignore",
                sparse_output=False
            )
        )
    ]
)

preprocessor = ColumnTransformer(
    transformers=[
        ("numeric", numeric_pipeline, numeric_columns),
        ("categorical", categorical_pipeline, categorical_columns)
    ],
    remainder="drop"
)

pipeline = Pipeline(
    steps=[
        ("preprocessor", preprocessor),
        ("model", DecisionTreeClassifier(**model_params))
    ]
)
```

Untuk dataset besar, pertahankan `sparse_output=True` dan jangan mengubah hasil menjadi dense tanpa pemeriksaan memori.

### 8.3 Reproduksibilitas

Catat:

- SHA-256 dataset;
- ID dan versi konfigurasi;
- `random_state`;
- versi Python, pandas, NumPy, dan scikit-learn;
- timestamp;
- source code version atau Git commit;
- jumlah baris sebelum/sesudah cleaning;
- daftar feature name setelah encoding.

---

## 9. Hasil setiap tahap

Semua tahap menggunakan envelope yang sama:

```json
{
  "run_id": "90962fd7-0cc0-46bd-b0c2-4446ac3d3cb9",
  "stage": {
    "code": "evaluation",
    "sequence": 9,
    "name": "Evaluasi Model"
  },
  "status": "completed",
  "progress": 100,
  "summary": {},
  "visualizations": [],
  "tables": [],
  "explanations": [],
  "warnings": [],
  "artifacts": [],
  "started_at": "2026-07-31T07:29:58Z",
  "completed_at": "2026-07-31T07:30:00Z"
}
```

### 9.1 Upload

Output:

- filename, file size, checksum;
- daftar sheet;
- jumlah baris dan kolom;
- preview dengan pagination;
- total missing dan duplicate.

### 9.2 Profiling

Per kolom:

- inferred type;
- count, missing count/ratio;
- unique count/ratio;
- min, max, mean, median, standard deviation untuk numerik;
- top categories untuk kategorikal;
- histogram bins atau category distribution;
- role recommendation, confidence, dan reason.

### 9.3 Cleaning

- before/after row count;
- missing values before/after;
- duplicate rows removed;
- constant columns removed;
- daftar tindakan;
- sample data terdampak yang telah dibatasi dan dimasking bila sensitif.

### 9.4 Encoding

- fitur asli;
- fitur setelah encoding;
- category mapping;
- original-to-transformed feature map;
- ukuran matriks;
- unknown-category policy.

### 9.5 Data split

- jumlah training/testing;
- proporsi;
- distribusi kelas keseluruhan, training, dan testing;
- stratify dan random state.

### 9.6 Training

- parameter efektif;
- waktu training;
- kedalaman aktual;
- jumlah node dan leaf;
- fitur yang dipakai.

### 9.7 Evaluation

- confusion matrix;
- accuracy dan error rate;
- balanced accuracy;
- precision, recall, dan F1 per kelas;
- macro, micro, dan weighted averages;
- classification report;
- interpretasi berbasis rule yang transparan.

### 9.8 Tree, importance, dan rules

- struktur node;
- hubungan parent-child;
- kondisi split;
- impurity, samples, dan class distribution;
- feature importance transformed dan aggregated;
- permutation importance;
- root-to-leaf rules.

---

## 10. Confusion Matrix dan metrik

### 10.1 Definisi binary classification

Dengan positive class yang ditentukan konfigurasi:

- `TP`: aktual positif, prediksi positif.
- `TN`: aktual negatif, prediksi negatif.
- `FP`: aktual negatif, prediksi positif.
- `FN`: aktual positif, prediksi negatif.

\[
Accuracy = \frac{TP+TN}{TP+TN+FP+FN}
\]

\[
Precision = \frac{TP}{TP+FP}
\]

\[
Recall = \frac{TP}{TP+FN}
\]

\[
F1 = 2 \times \frac{Precision \times Recall}{Precision+Recall}
\]

Pembagian dengan nol mengikuti `evaluation.zero_division`, tetapi backend harus menambahkan warning.

### 10.2 Multiclass

Untuk multiclass, jangan mengirim `tp/tn/fp/fn` tunggal. Kirim:

- matriks `N × N`;
- metrics per kelas dengan skema one-vs-rest;
- macro average;
- weighted average;
- micro average jika relevan.

### 10.3 Kontrak evaluasi

```json
{
  "run_id": "uuid",
  "dataset_split": {
    "training_rows": 415,
    "testing_rows": 104,
    "test_size": 0.2,
    "stratified": true,
    "random_state": 42
  },
  "confusion_matrix": {
    "labels": ["Tidak", "Ya"],
    "values": [[3, 25], [4, 72]],
    "orientation": {
      "rows": "actual",
      "columns": "predicted"
    },
    "binary_values": {
      "negative_class": "Tidak",
      "positive_class": "Ya",
      "tn": 3,
      "fp": 25,
      "fn": 4,
      "tp": 72
    }
  },
  "metrics": {
    "accuracy": 0.7212,
    "error_rate": 0.2788,
    "balanced_accuracy": 0.5273,
    "macro_precision": 0.5854,
    "macro_recall": 0.5273,
    "macro_f1": 0.5019,
    "weighted_precision": 0.6579,
    "weighted_recall": 0.7212,
    "weighted_f1": 0.6545
  },
  "class_metrics": [
    {
      "class_label": "Tidak",
      "precision": 0.4286,
      "recall": 0.1071,
      "f1_score": 0.1714,
      "support": 28
    },
    {
      "class_label": "Ya",
      "precision": 0.7423,
      "recall": 0.9474,
      "f1_score": 0.8324,
      "support": 76
    }
  ]
}
```

Simpan nilai numerik sebagai desimal `0–1`. Frontend bertanggung jawab memformat persen dan jumlah digit.

---

## 11. Decision Tree

### 11.1 Struktur node API

```json
{
  "node_id": 0,
  "parent_node_id": null,
  "depth": 0,
  "is_leaf": false,
  "feature_original": "persepsi_pengaruh_akademik",
  "feature_transformed": "persepsi_pengaruh_akademik_Ya",
  "operator": "<=",
  "threshold": 0.5,
  "impurity_name": "gini",
  "impurity": 0.3919,
  "samples": 415,
  "weighted_samples": 415.0,
  "class_counts": {
    "Tidak": 111,
    "Ya": 304
  },
  "predicted_class": "Ya",
  "left_child_id": 1,
  "right_child_id": 12
}
```

### 11.2 Aturan keputusan

Setiap leaf dikonversi menjadi rule:

```json
{
  "rule_id": "uuid",
  "leaf_node_id": 8,
  "predicted_class": "Tidak",
  "conditions": [
    {
      "feature": "durasi_medsos_jam",
      "operator": ">",
      "value": 4
    },
    {
      "feature": "durasi_tidur_jam",
      "operator": "<=",
      "value": 6
    }
  ],
  "samples": 21,
  "purity": 0.7143,
  "class_counts": {
    "Tidak": 15,
    "Ya": 6
  }
}
```

Untuk one-hot features, service menerjemahkan kondisi teknis menjadi kalimat kategorikal yang mudah dipahami.

### 11.3 Feature importance

Simpan dua tingkat:

1. `transformed_feature_importance`: setiap kolom setelah encoding.
2. `original_feature_importance`: jumlah importance seluruh transformed feature dari variabel asli.

Importance berbasis impurity bukan hubungan sebab-akibat. Jika aktif, permutation importance dihitung pada testing set sebagai pembanding.

---

## 12. Desain database

Gunakan UUID sebagai primary key, `TIMESTAMPTZ`, dan `JSONB` hanya untuk struktur fleksibel. Data yang sering difilter atau diurutkan harus memiliki kolom/tabel normal.

### 12.1 Tabel utama

| Tabel | Fungsi |
|---|---|
| `projects` | Wadah proyek penelitian |
| `datasets` | Metadata file asli |
| `dataset_versions` | Versi file atau pemilihan sheet |
| `dataset_columns` | Profil setiap kolom |
| `dataset_profiles` | Ringkasan hasil profiling |
| `experiment_configs` | Identitas konfigurasi |
| `experiment_config_versions` | JSON konfigurasi immutable |
| `experiment_runs` | Satu eksekusi model |
| `run_steps` | Status dan output per tahap |
| `model_metrics` | Metrik agregat |
| `class_metrics` | Metrik per kelas |
| `confusion_matrix_values` | Sel matriks |
| `predictions` | Aktual, prediksi, probability, benar/salah |
| `tree_nodes` | Struktur Decision Tree |
| `decision_rules` | Aturan root-to-leaf |
| `feature_importances` | Importance per fitur |
| `artifacts` | File model, gambar, dan laporan |
| `audit_logs` | Perubahan penting oleh pengguna/sistem |

### 12.2 Relasi inti

```mermaid
erDiagram
    PROJECTS ||--o{ DATASETS : contains
    DATASETS ||--o{ CONFIG_VERSIONS : configured_by
    CONFIG_VERSIONS ||--o{ RUNS : executes
    RUNS ||--o{ RUN_STEPS : has
    RUNS ||--o{ MODEL_RESULTS : produces
```

`MODEL_RESULTS` pada diagram mewakili tabel metrics, predictions, tree nodes, rules, importance, dan artifacts.

### 12.3 Kolom penting

#### `datasets`

- `id UUID PK`
- `project_id UUID FK`
- `original_filename VARCHAR`
- `storage_key VARCHAR`
- `mime_type VARCHAR`
- `file_size BIGINT`
- `sha256 CHAR(64)`
- `status VARCHAR`
- `created_by UUID`
- `created_at TIMESTAMPTZ`

#### `experiment_config_versions`

- `id UUID PK`
- `experiment_config_id UUID FK`
- `dataset_id UUID FK`
- `version INTEGER`
- `schema_version VARCHAR`
- `config_json JSONB`
- `config_hash CHAR(64)`
- `source VARCHAR`
- `validation_status VARCHAR`
- `validation_result JSONB`
- `change_note TEXT`
- `parent_version_id UUID NULL`
- `is_active BOOLEAN`
- `created_by UUID`
- `created_at TIMESTAMPTZ`

Unique constraint: `(experiment_config_id, version)`.  
Partial unique index: satu `is_active=true` per `experiment_config_id`.

#### `experiment_runs`

- `id UUID PK`
- `config_version_id UUID FK`
- `status VARCHAR`
- `progress SMALLINT`
- `current_stage VARCHAR`
- `dataset_sha256 CHAR(64)`
- `code_version VARCHAR`
- `runtime_versions JSONB`
- `queued_at`, `started_at`, `completed_at`
- `duration_ms BIGINT`
- `error_code VARCHAR NULL`
- `error_message TEXT NULL`

#### `predictions`

- `id UUID PK`
- `run_id UUID FK`
- `row_key VARCHAR`
- `actual_label VARCHAR`
- `predicted_label VARCHAR`
- `is_correct BOOLEAN`
- `probabilities JSONB`
- `leaf_node_id INTEGER NULL`

Jangan menyimpan seluruh fitur pribadi pada tabel ini. Gunakan `row_key` untuk mengakses preview terotorisasi.

#### `confusion_matrix_values`

- `run_id UUID FK`
- `actual_label VARCHAR`
- `predicted_label VARCHAR`
- `value INTEGER`
- primary key gabungan `(run_id, actual_label, predicted_label)`

---

## 13. API REST

Base path: `/api/v1`

### 13.1 Projects

```http
POST   /projects
GET    /projects
GET    /projects/{project_id}
PATCH  /projects/{project_id}
```

### 13.2 Datasets dan profiling

```http
POST   /datasets/upload
GET    /datasets/{dataset_id}
GET    /datasets/{dataset_id}/sheets
POST   /datasets/{dataset_id}/profile
GET    /datasets/{dataset_id}/profile
GET    /datasets/{dataset_id}/preview
GET    /datasets/{dataset_id}/table
GET    /datasets/{dataset_id}/columns
POST   /datasets/{dataset_id}/recommend-config
GET    /datasets/{dataset_id}/eda-visualization
GET    /datasets/{dataset_id}/target-conversion-preview
```

Upload menggunakan `multipart/form-data`:

- `file`
- `project_id`
- `sheet_name` opsional
- `header_row` opsional

`GET /datasets/{dataset_id}/table` digunakan frontend untuk menampilkan isi dataset dalam bentuk tabel paginated. Secara default endpoint ini membaca data asli dari file upload, bukan hasil normalisasi.

Query parameter:

| Parameter | Default | Keterangan |
|---|---:|---|
| `page` | `1` | Halaman data, dimulai dari 1 |
| `page_size` | `50` | Jumlah baris per halaman, maksimum 500 |
| `normalized` | `false` | Jika `true`, tampilkan versi yang sudah melalui normalisasi preprocessing backend |

Contoh:

```http
GET /api/v1/datasets/{dataset_id}/table?page=1&page_size=50
GET /api/v1/datasets/{dataset_id}/table?page=1&page_size=50&normalized=true
```

Contoh respons:

```json
{
  "success": true,
  "data": {
    "dataset_id": "uuid",
    "dataset_name": "dataset.xlsx",
    "source": "original",
    "columns": ["Nama", "IPK"],
    "rows": [
      {
        "Nama": "Siti",
        "IPK": 3.5
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 50,
      "total_rows": 519,
      "total_pages": 11,
      "has_next": true,
      "has_previous": false
    }
  },
  "meta": {}
}
```

Contoh konfigurasi siap pakai untuk dataset `Pengaruh Medsos Nilai Akademik Mahasiswa Indonesia.xlsx` tersedia di:

```text
docs/sample_config_pengaruh_medsos_nilai_akademik.json
```

### 13.3 Konfigurasi

```http
GET    /datasets/{dataset_id}/configs
POST   /datasets/{dataset_id}/configs
GET    /configs/{config_version_id}
PUT    /configs/{config_version_id}/draft
POST   /configs/{config_version_id}/validate
POST   /configs/{config_version_id}/versions
POST   /configs/{config_version_id}/activate
POST   /configs/{config_version_id}/duplicate
GET    /configs/{left_id}/compare/{right_id}
GET    /configs/{config_version_id}/download
```

`PUT /draft` memakai optimistic locking melalui `version_token` agar perubahan dua editor tidak saling menimpa.

### 13.4 Experiment runs

```http
POST   /experiments/runs
GET    /runs/{run_id}
GET    /runs/{run_id}/status
POST   /runs/{run_id}/cancel
GET    /runs/{run_id}/stages
GET    /runs/{run_id}/stages/{stage_code}
GET    /runs/{run_id}/events
```

Request:

```json
{
  "config_version_id": "uuid",
  "run_name": "Baseline 80-20 Gini"
}
```

Respons:

```json
{
  "success": true,
  "data": {
    "run_id": "uuid",
    "status": "queued",
    "status_url": "/api/v1/runs/uuid/status",
    "events_url": "/api/v1/runs/uuid/events"
  },
  "meta": {
    "request_id": "uuid"
  }
}
```

HTTP status: `202 Accepted`.

### 13.5 Hasil model

```http
GET /runs/{run_id}/data-split
GET /runs/{run_id}/evaluation
GET /runs/{run_id}/confusion-matrix
GET /runs/{run_id}/metrics
GET /runs/{run_id}/classification-report
GET /runs/{run_id}/predictions
GET /runs/{run_id}/misclassifications
GET /runs/{run_id}/preprocessing-summary
GET /runs/{run_id}/tree
GET /runs/{run_id}/tree-visualization
GET /runs/{run_id}/tree/nodes/{node_id}
GET /runs/{run_id}/feature-importance
GET /runs/{run_id}/rules
GET /runs/{run_id}/workflow-visualization
```

### 13.6 Artifacts dan laporan

```http
POST /runs/{run_id}/reports
GET  /runs/{run_id}/artifacts
GET  /artifacts/{artifact_id}/download
```

Download menggunakan short-lived signed URL atau streaming terotorisasi.

---

## 14. Kontrak respons baku

### 14.1 Sukses

```json
{
  "success": true,
  "data": {},
  "meta": {
    "request_id": "c78f75db-6bb1-4210-a042-b4e10f73f690",
    "timestamp": "2026-07-31T07:30:00Z"
  }
}
```

### 14.2 Error

```json
{
  "success": false,
  "error": {
    "code": "CONFIG_VALIDATION_FAILED",
    "message": "Konfigurasi belum dapat dijalankan.",
    "details": [
      {
        "path": "task.target_column",
        "code": "COLUMN_NOT_FOUND",
        "message": "Kolom target tidak ditemukan."
      }
    ]
  },
  "meta": {
    "request_id": "uuid",
    "timestamp": "2026-07-31T07:30:00Z"
  }
}
```

### 14.3 Status HTTP

| Status | Penggunaan |
|---:|---|
| 200 | Read/update berhasil |
| 201 | Resource dibuat |
| 202 | Task diterima |
| 400 | Request tidak valid secara umum |
| 401 | Belum terautentikasi |
| 403 | Tidak berwenang |
| 404 | Resource tidak ditemukan |
| 409 | Konflik versi/status |
| 413 | File terlalu besar |
| 415 | Format file tidak didukung |
| 422 | Validasi field/config gagal |
| 429 | Rate limit |
| 500 | Internal error |

---

## 15. Progress real-time

Gunakan Server-Sent Events untuk update satu arah:

```http
GET /api/v1/runs/{run_id}/events
Accept: text/event-stream
```

Contoh event:

```text
event: stage.progress
data: {"stage":"train_model","progress":70,"message":"Melatih Decision Tree"}
```

Frontend tetap harus menyediakan polling fallback pada `/status`.

Worker memperbarui progress secara idempotent. Event bukan sumber data utama; status final tetap dibaca dari PostgreSQL.

---

## 16. Integrasi frontend

Backend menyediakan data untuk komponen reusable:

| Komponen frontend | Endpoint/data |
|---|---|
| Dataset summary cards | dataset dan profile summary |
| Data preview table | preview paginated |
| Column profile cards | dataset columns |
| JSON editor | config JSON + JSON Schema |
| Before/after comparison | cleaning stage |
| Distribution chart | profiling dan split |
| Confusion Matrix heatmap | confusion matrix |
| Metric cards | metrics |
| Classification report | class metrics |
| Interactive tree | normalized tree nodes |
| Feature importance chart | importance results |
| Rule cards | decision rules |
| Prediction table | predictions paginated |
| Process timeline | run steps/events |
| Artifact downloads | artifacts |

Untuk visualisasi, backend mengirim angka, label, orientasi, dan metadata. Warna, tooltip, locale persen, dan layout dikelola frontend.

---

## 17. Penyimpanan file dan artifact

### 17.1 Object key

```text
projects/{project_id}/
├── datasets/{dataset_id}/{version_id}/source.xlsx
├── runs/{run_id}/models/pipeline.joblib
├── runs/{run_id}/visuals/tree.svg
├── runs/{run_id}/visuals/tree.png
├── runs/{run_id}/exports/evaluation.xlsx
└── runs/{run_id}/reports/report.pdf
```

### 17.2 Jenis artifact

- `source_dataset`
- `cleaned_preview`
- `config_json`
- `trained_pipeline`
- `tree_png`
- `tree_svg`
- `metrics_json`
- `predictions_csv`
- `evaluation_xlsx`
- `report_pdf`
- `report_docx`

Metadata artifact mencatat content type, size, checksum, storage key, dan retention policy.

---

## 18. Keamanan dan privasi

- JWT/OAuth2 authentication.
- Role minimal: `admin`, `researcher`, `viewer`.
- Authorization berbasis kepemilikan project.
- Batasi ukuran upload, jumlah sheet, rows, columns, dan cardinality.
- Jangan menggunakan filename pengguna sebagai path.
- Jangan memuat artifact `joblib` yang berasal dari pengguna; pickle/joblib dapat mengeksekusi kode.
- Formula Excel dibaca sebagai data saja.
- Preview data sensitif harus dimasking.
- Signed download URL berumur pendek.
- Audit upload, perubahan config, aktivasi, run, download, dan penghapusan.
- Rahasia hanya melalui environment/secret manager.
- CORS hanya mengizinkan origin frontend yang diketahui.
- Rate limit upload, profiling, training, dan report generation.

---

## 19. Observability

### 19.1 Structured logging

Setiap log minimal memuat:

- timestamp;
- level;
- request ID;
- user ID;
- project ID;
- dataset ID;
- run ID;
- stage;
- duration;
- error code.

Jangan mencatat isi baris dataset atau token.

### 19.2 Metrics

- request latency dan error rate;
- upload size;
- queue depth;
- task duration per stage;
- success/failure run;
- worker memory dan CPU;
- storage usage;
- jumlah rows/features;
- model training duration.

### 19.3 Health endpoint

```http
GET /health/live
GET /health/db
GET /health/ready
```

`live` hanya memeriksa proses API hidup. `db` memeriksa koneksi database dengan query ringan. `ready` memeriksa kesiapan dependency utama; pada implementasi saat ini `ready` memakai pemeriksaan database.

---

## 20. Testing

### 20.1 Unit test

- type inference;
- identifier detection;
- config recommendation;
- config validation;
- feature mapping;
- metric calculation;
- binary/multiclass matrix orientation;
- tree node extraction;
- rule extraction;
- aggregation feature importance.

### 20.2 Integration test

- upload → profile → recommendation;
- save/validate/activate config;
- queued run → completed;
- database persistence;
- artifact creation;
- authorization;
- version conflict;
- idempotent task retry.

### 20.3 Golden dataset test

Sediakan dataset kecil dengan hasil yang telah diketahui. Uji:

- split reproducible dengan random state yang sama;
- confusion matrix persis;
- accuracy/precision/recall/F1 sesuai toleransi;
- jumlah node dan depth;
- transformed feature names;
- model serialization/deserialization.

### 20.4 Edge cases

- target satu kelas;
- missing target;
- unknown category di testing;
- seluruh nilai fitur hilang;
- kolom kategori sangat banyak;
- nama kolom duplikat;
- dataset sangat kecil;
- multiclass;
- class tidak seimbang;
- pembagi metrik nol;
- worker retry setelah partial failure.

Target coverage minimum yang disarankan: 80% pada domain service dan ML core.

---

## 21. Environment variables

```dotenv
APP_NAME=ml-analysis-api
APP_ENV=development
API_V1_PREFIX=/api/v1
SECRET_KEY=replace-me
ACCESS_TOKEN_EXPIRE_MINUTES=60

DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/ml_analysis
REDIS_URL=redis://localhost:6379/0

STORAGE_ENDPOINT=http://localhost:9000
STORAGE_ACCESS_KEY=replace-me
STORAGE_SECRET_KEY=replace-me
STORAGE_BUCKET=ml-artifacts
STORAGE_SECURE=false

ALLOWED_ORIGINS=http://localhost:3000
MAX_UPLOAD_MB=50
MAX_DATASET_ROWS=500000
MAX_DATASET_COLUMNS=500
PREVIEW_ROWS=100

LOG_LEVEL=INFO
```

`.env` tidak boleh masuk Git. Repository hanya menyimpan `.env.example`.

---

## 22. Dependencies awal

```text
fastapi
uvicorn[standard]
gunicorn
pydantic
pydantic-settings
python-multipart
email-validator

sqlalchemy
alembic
asyncpg
psycopg[binary]

pandas
numpy
scikit-learn
openpyxl
joblib
scipy

celery
redis
boto3

matplotlib
graphviz
pydot

python-jose[cryptography]
passlib[bcrypt]
httpx

pytest
pytest-asyncio
pytest-cov
ruff
mypy
```

Gunakan lock file dan pin versi setelah compatibility test. Jangan memasang `psycopg2-binary` dan `psycopg[binary]` sekaligus tanpa kebutuhan jelas.

---

## 23. Deployment

### 23.1 Layanan

- `ml-api`: Gunicorn/Uvicorn workers.
- `ml-worker`: Celery worker.
- `ml-scheduler`: opsional untuk cleanup.
- PostgreSQL.
- Redis.
- MinIO/S3-compatible object storage.
- Nginx reverse proxy.

### 23.2 Catatan worker

Training bersifat CPU-bound. Jumlah worker tidak boleh ditentukan hanya dari worker web. Tetapkan concurrency berdasarkan CPU dan batas RAM.

### 23.3 Alembic

Alur deployment:

1. Backup database.
2. Jalankan test dan lint.
3. Build artifact/container.
4. Jalankan `alembic upgrade head`.
5. Deploy API dan worker dengan versi sama.
6. Jalankan readiness check.
7. Smoke test upload dan run kecil.

---

## 24. Tahapan implementasi

### Fase 1 — Fondasi

- Project scaffolding.
- Configuration, database, migration, response/error standard.
- Authentication dan authorization.
- Object storage.

### Fase 2 — Dataset dan konfigurasi

- Upload CSV/XLSX.
- Sheet selection dan preview.
- Profiling.
- Config recommendation.
- Visual form/JSON contract.
- Validation dan versioning.

### Fase 3 — ML pipeline

- Cleaning.
- Train/test split.
- ColumnTransformer.
- Decision Tree training.
- Model artifact.
- Reproducibility metadata.

### Fase 4 — Hasil lengkap

- Confusion Matrix.
- Accuracy, Precision, Recall, F1.
- Classification report.
- Predictions dan misclassifications.
- Tree nodes.
- Rules dan feature importance.

### Fase 5 — Asinkron dan frontend readiness

- Task queue.
- Progress/event stream.
- Uniform stage responses.
- Pagination dan download.
- Error recovery.

### Fase 6 — Laporan dan pembanding

- Excel/PDF/DOCX.
- Baseline vs balanced model.
- Stratified cross-validation.
- Experiment comparison.

---

## 25. Acceptance criteria MVP

MVP dianggap selesai bila:

1. Pengguna dapat mengunggah CSV/XLSX secara aman.
2. Sistem menampilkan preview dan profiling per kolom.
3. Sistem membuat rekomendasi konfigurasi beserta confidence dan reason.
4. Konfigurasi dapat diedit, divalidasi, disimpan sebagai versi, dan diaktifkan.
5. Training menggunakan preprocessing yang hanya di-fit pada training set.
6. Run dapat dipantau per tahap.
7. Backend mengembalikan Confusion Matrix dengan orientasi eksplisit.
8. Backend mengembalikan Accuracy, Precision, Recall, dan F1 agregat serta per kelas.
9. Backend menyimpan prediction testing dan dapat memfilter kesalahan prediksi.
10. Backend mengembalikan node Decision Tree untuk visualisasi interaktif.
11. Backend menghasilkan feature importance dan decision rules.
12. Model, konfigurasi, dan hasil dapat ditelusuri ke dataset checksum yang sama.
13. Run lama tidak berubah ketika konfigurasi diedit.
14. Test golden dataset lulus secara deterministik.
15. Authorization mencegah akses antarproject yang tidak berhak.

---

## 26. Keputusan teknis utama

- **PostgreSQL** menyimpan metadata dan hasil terstruktur; file besar disimpan di object storage.
- **Celery/Redis** digunakan untuk proses berat, bukan `BackgroundTasks`.
- **JSONB** dipakai untuk snapshot konfigurasi dan output fleksibel, tetapi metrik utama tetap dinormalisasi.
- **SSE** digunakan untuk progress dengan polling sebagai fallback.
- **Pydantic discriminated models** disiapkan agar configuration schema dapat diperluas ke algoritma lain.
- **Experiment run immutable** untuk reproducibility.
- **Frontend menerima data visualisasi**, sehingga ECharts/Vue Flow/D3 dapat merender tampilan tanpa parsing artifact internal.

Desain ini memungkinkan aplikasi berkembang dari analisis penelitian mahasiswa menjadi platform analisis klasifikasi generik tanpa mengubah core pipeline untuk setiap nama atau struktur dataset baru.
