# API Workflow Visualization

## Status Dukungan Saat Ini

Aplikasi sekarang **sudah menyediakan endpoint backend** untuk seluruh 7 langkah yang ada pada gambar, tetapi bentuk visualisasinya tetap dirender oleh frontend.

Yang sudah tersedia:

1. EDA visualization berbasis dataset;
2. preprocessing summary berbasis experiment run;
3. preview konversi target atau CGPA ke kategori;
4. training model Decision Tree;
5. confusion matrix;
6. accuracy, precision, recall, dan F1-score;
7. visualisasi pohon keputusan dalam format node-edge;
8. endpoint agregat workflow untuk halaman hasil analisis.

Catatan:

- Step 1 dan step 3 menggunakan `dataset_id`.
- Step 2, 4, 5, 6, dan 7 menggunakan `run_id`.
- Backend mengirim data siap render, bukan HTML, SVG statis, atau styling chart.
- Endpoint tree dan preprocessing summary paling akurat untuk run yang dibuat setelah perubahan ini.

Base path: `/api/v1`

## Kontrak Response Frontend

Semua endpoint sukses memakai wrapper standar:

```json
{
  "success": true,
  "data": {},
  "meta": {
    "request_id": "request-id",
    "timestamp": "2026-08-02T00:00:00+00:00"
  }
}
```

Frontend harus membaca payload utama dari `response.data`, bukan dari root
response. Contoh: hasil metrik ada di `response.data.metrics`, bukan
`response.metrics`.

## Endpoint Dataset-Level

### 0. Tabel Dataset Asli

`GET /datasets/{dataset_id}/table`

Fungsi:

- menampilkan isi file upload sebagai tabel paginated;
- default mengembalikan data asli dari file Excel/CSV;
- mendukung `normalized=true` untuk melihat data setelah normalisasi backend.

Query parameter:

| Parameter | Default | Keterangan |
|---|---:|---|
| `page` | `1` | Halaman data |
| `page_size` | `50` | Jumlah baris per halaman, maksimum 500 |
| `normalized` | `false` | Tampilkan versi normalisasi jika `true` |

Contoh:

```http
GET /api/v1/datasets/{dataset_id}/table?page=1&page_size=50
```

Frontend use case:

- tabel preview dataset asli;
- pagination dataset upload;
- pembanding data asli dan data normalized.

### 1. Profiling Dataset untuk EDA

`POST /datasets/{dataset_id}/profile`

Fungsi:

- membentuk profil dataset;
- menghitung missing values, unique ratio, duplicate rows;
- mendeteksi tipe kolom;
- menyediakan statistik numerik dan kategori teratas.

Frontend use case:

- summary cards EDA;
- tabel profiling kolom;
- bar chart missing value;
- distribusi kategori.

### 2. EDA Visualization Siap Pakai Frontend

`GET /datasets/{dataset_id}/eda-visualization`

Fungsi:

- menyediakan summary dataset;
- menyediakan series untuk missing ratio dan unique ratio;
- menyediakan statistik numerik dan distribusi kategori;
- menjadi endpoint utama untuk langkah EDA.

Contoh respons:

```json
{
  "success": true,
  "data": {
    "dataset_id": "dataset_uuid",
    "dataset_name": "student_performance.xlsx",
    "summary": {
      "rows": 500,
      "columns": 12,
      "duplicate_rows": 3,
      "missing_cells": 17
    },
    "charts": {
      "missing_ratio_by_column": [
        {
          "column": "cgpa",
          "missing_ratio": 0.004,
          "missing_count": 2
        }
      ],
      "unique_ratio_by_column": [
        {
          "column": "student_id",
          "unique_ratio": 1.0,
          "unique_count": 500
        }
      ],
      "numeric_distributions": [
        {
          "column": "cgpa",
          "stats": {
            "min": 1.75,
            "max": 3.98,
            "mean": 3.11,
            "median": 3.2
          }
        }
      ],
      "categorical_distributions": [
        {
          "column": "gender",
          "top_categories": [
            {
              "value": "Female",
              "count": 280
            }
          ]
        }
      ]
    },
    "columns": [
      {
        "name": "cgpa",
        "inferred_type": "numeric",
        "missing_count": 2,
        "missing_ratio": 0.004,
        "unique_count": 36,
        "unique_ratio": 0.072,
        "stats": {
          "min": 1.75,
          "max": 3.98,
          "mean": 3.11,
          "median": 3.2
        }
      }
    ]
  },
  "meta": {}
}
```

Frontend use case:

- halaman EDA;
- chart missing values;
- ringkasan kualitas data;
- tabel profil kolom.

### 3. Pilihan Preset dan Konfigurasi Dataset

Frontend wajib meminta pengguna memilih preset. Jangan menentukan preset dari nama file atau hasil tebakan otomatis.

Daftar pilihan:

`GET /datasets/configuration-presets`

Contoh respons `data`:

```json
[
  {
    "id": "indonesia",
    "label": "Mahasiswa Indonesia",
    "description": "Kuesioner mahasiswa Indonesia dengan target persepsi prestasi akademik."
  },
  {
    "id": "india",
    "label": "Mahasiswa India",
    "description": "Dataset CGPA India dengan target Rendah, Sedang, dan Tinggi."
  }
]
```

Setelah dataset diunggah dan preset dipilih:

`POST /datasets/{dataset_id}/recommend-config?preset=indonesia`

atau:

`POST /datasets/{dataset_id}/recommend-config?preset=india`

Query `preset` wajib diisi. Backend memeriksa kolom wajib dan mengembalikan error jika struktur dataset tidak cocok. Respons sukses berisi konfigurasi final yang harus disimpan frontend tanpa mengganti target, fitur aktif, transformasi target, atau parameter model secara diam-diam.

Perbedaan preset:

| Bagian | Indonesia | India |
|---|---|---|
| Target | Pertanyaan persepsi prestasi akademik | `current_sem_CGPA` |
| Transformasi target | Tidak ada | Skala `0.01`, batas `7.0` dan `8.0` |
| Kelas | `Tidak`, `Ya` | `Rendah`, `Sedang`, `Tinggi` |
| Fitur | Delapan kolom kuesioner aktif | `daily_screen_time_hours`, `social_media_hours` |
| `min_samples_leaf` | `1` | `5` |

Preset India mengembalikan blok berikut di dalam `task`:

```json
{
  "target_column": "current_sem_CGPA",
  "positive_class": null,
  "target_transform": {
    "type": "numeric_bins",
    "scale": 0.01,
    "thresholds": [7.0, 8.0],
    "labels": ["Rendah", "Sedang", "Tinggi"]
  }
}
```

Contoh blok config preprocessing:

```json
{
  "preprocessing": {
    "mode": "strict",
    "collapse_rare_study_programs": true,
    "simplify_social_media_platforms": true,
    "normalize_binary_labels": true,
    "normalize_duration_buckets": true
  }
}
```

Arti mode:

- `raw`: hanya trim spasi dasar, tanpa penyederhanaan kategori.
- `strict`: aktifkan seluruh normalisasi yang direkomendasikan backend.
- `custom`: frontend dapat mengirim kombinasi boolean sendiri.

### 4. Preview Konversi Target atau CGPA ke Kategori

`GET /datasets/{dataset_id}/target-conversion-preview?preset={preset}`

Fungsi:

- menampilkan target sesuai preset yang dipilih;
- menampilkan distribusi kategori target;
- menampilkan `target_transform` yang akan digunakan saat training;
- menampilkan `positive_class`;
- menjadi endpoint utama untuk langkah konversi CGPA ke kategori klasifikasi.

Contoh respons:

```json
{
  "success": true,
  "data": {
    "dataset_id": "dataset_uuid",
    "target_column": "cgpa_category",
    "positive_class": "High",
    "task_type": "classification",
    "target_distribution": [
      {
        "label": "High",
        "count": 320
      },
      {
        "label": "Low",
        "count": 180
      }
    ],
    "recommendations": [
      {
        "column": "cgpa_category",
        "recommended_role": "target",
        "confidence": 0.9,
        "reasons": [
          "low cardinality suitable for classification target",
          "column name matches target pattern"
        ],
        "requires_confirmation": true
      }
    ],
    "columns": [
      {
        "name": "cgpa_category",
        "data_type": "categorical",
        "role": "target",
        "enabled": true,
        "encoding": "one_hot"
      }
    ]
  },
  "meta": {}
}
```

Frontend use case:

- pie atau bar chart distribusi kategori target;
- review hasil konversi CGPA;
- approval target sebelum training.

## Endpoint Run-Level

### 5. Ringkasan Preprocessing per Run

`GET /experiments/runs/{run_id}/preprocessing-summary`

Fungsi:

- memberi ringkasan fitur numerik, kategorikal, ordinal;
- menjelaskan imputasi dan encoding yang dipakai;
- memberi jumlah fitur sebelum dan sesudah encoding;
- menampilkan konfigurasi preprocessing yang dipakai saat run dibuat.

Contoh respons:

```json
{
  "success": true,
  "data": {
    "run_id": "run_uuid",
    "target_column": "cgpa_category",
    "preprocessing_config": {
      "mode": "strict",
      "collapse_rare_study_programs": true,
      "simplify_social_media_platforms": true,
      "normalize_binary_labels": true,
      "normalize_duration_buckets": true
    },
    "numeric_features": ["study_hours", "sleep_hours"],
    "categorical_features": ["gender", "internet_quality"],
    "ordinal_features": ["semester"],
    "feature_count_before_encoding": 5,
    "feature_count_after_encoding": 9,
    "transformed_feature_names": [
      "numeric__study_hours",
      "numeric__sleep_hours",
      "categorical__gender_Female",
      "categorical__gender_Male",
      "categorical__internet_quality_Good",
      "categorical__internet_quality_Poor",
      "ordinal__semester"
    ],
    "imputation": {
      "numeric": "median",
      "categorical": "most_frequent"
    },
    "encoding": {
      "categorical": "one_hot",
      "ordinal": "ordinal"
    }
  },
  "meta": {}
}
```

Frontend use case:

- preprocessing summary cards;
- before/after feature count;
- transformed-feature table.

### 6. Visualisasi Pohon Keputusan

`GET /experiments/runs/{run_id}/tree-visualization`

Fungsi:

- menyediakan struktur pohon dalam format `nodes` dan `edges`;
- dapat langsung dipakai oleh frontend untuk diagram interaktif.

Contoh respons:

```json
{
  "success": true,
  "data": {
    "run_id": "run_uuid",
    "root_node_id": 0,
    "nodes": [
      {
        "node_id": 0,
        "depth": 0,
        "parent_node_id": null,
        "is_leaf": false,
        "samples": 400,
        "weighted_samples": 400.0,
        "impurity": 0.41,
        "predicted_class": "High",
        "class_counts": {
          "High": 260,
          "Low": 140
        },
        "left_child_id": 1,
        "right_child_id": 2,
        "feature_name": "numeric__study_hours",
        "operator": "<=",
        "threshold": 2.5
      }
    ],
    "edges": [
      {
        "source": 0,
        "target": 1,
        "branch": "left",
        "condition": "true"
      },
      {
        "source": 0,
        "target": 2,
        "branch": "right",
        "condition": "false"
      }
    ]
  },
  "meta": {}
}
```

Frontend use case:

- tree graph;
- expandable decision nodes;
- tooltip split condition;
- node purity and sample detail.

### 7. Ringkasan Workflow 7 Langkah

`GET /experiments/runs/{run_id}/workflow-visualization`

Fungsi:

- menggabungkan langkah visual yang berbasis run;
- cocok untuk halaman hasil analisis atau timeline langkah kerja;
- memberi `status` per langkah.

Contoh respons:

```json
{
  "success": true,
  "data": {
    "run_id": "run_uuid",
    "run_name": "Baseline Run",
    "steps": [
      {
        "step_number": 1,
        "code": "eda",
        "title": "Exploratory Data Analysis (EDA)",
        "status": "not_available",
        "visualization_type": "dataset-profile",
        "endpoint": null,
        "notes": "Gunakan endpoint dataset-level untuk langkah ini."
      },
      {
        "step_number": 2,
        "code": "preprocessing",
        "title": "Preprocessing Data",
        "status": "available",
        "visualization_type": "summary-cards-and-table",
        "endpoint": "/api/v1/experiments/runs/run_uuid/preprocessing-summary",
        "data": {}
      },
      {
        "step_number": 3,
        "code": "target-conversion",
        "title": "Konversi CGPA Menjadi Kategori",
        "status": "configured",
        "visualization_type": "config-summary",
        "endpoint": null,
        "data": {
          "preset": "india",
          "target_column": "current_sem_CGPA",
          "positive_class": null,
          "target_transform": {
            "type": "numeric_bins",
            "scale": 0.01,
            "thresholds": [7.0, 8.0],
            "labels": ["Rendah", "Sedang", "Tinggi"]
          }
        }
      },
      {
        "step_number": 4,
        "code": "model-training",
        "title": "Pembangunan Model Decision Tree",
        "status": "available",
        "visualization_type": "summary-cards",
        "endpoint": "/api/v1/experiments/runs/run_uuid",
        "data": {}
      },
      {
        "step_number": 5,
        "code": "confusion-matrix",
        "title": "Confusion Matrix",
        "status": "available",
        "visualization_type": "heatmap",
        "endpoint": "/api/v1/experiments/runs/run_uuid/confusion-matrix",
        "data": {}
      },
      {
        "step_number": 6,
        "code": "metrics",
        "title": "Accuracy, Precision, Recall, dan F1-Score",
        "status": "available",
        "visualization_type": "metric-cards-and-table",
        "endpoint": "/api/v1/experiments/runs/run_uuid/metrics",
        "data": {}
      },
      {
        "step_number": 7,
        "code": "decision-tree-visualization",
        "title": "Visualisasi Pohon Keputusan",
        "status": "available",
        "visualization_type": "node-link-diagram",
        "endpoint": "/api/v1/experiments/runs/run_uuid/tree-visualization",
        "data": {}
      }
    ]
  },
  "meta": {}
}
```

Frontend use case:

- wizard hasil analisis;
- timeline proses;
- halaman detail experiment run;
- conditional rendering per langkah.

### 8. Metrics Model

`GET /experiments/runs/{run_id}/metrics`

Fungsi:

- menyediakan aggregate metrics untuk kartu ringkasan global;
- menyediakan per-class metrics untuk tabel classification report;
- mengirim angka raw decimal `0-1` agar format akhir dikelola frontend.

Contoh respons:

```json
{
  "success": true,
  "data": {
    "run_id": "run_uuid",
    "metrics": {
      "accuracy": 0.7211538462,
      "precision": 0.6423117034,
      "recall": 0.7211538462,
      "f1_score": 0.6420940171,
      "f1": 0.6420940171
    },
    "class_metrics": [
      {
        "class_label": "Tidak",
        "precision": 0.4,
        "recall": 0.0714285714,
        "f1_score": 0.1212121212,
        "support": 28
      },
      {
        "class_label": "Ya",
        "precision": 0.7373737374,
        "recall": 0.9605263158,
        "f1_score": 0.8342857143,
        "support": 76
      }
    ]
  },
  "meta": {}
}
```

Frontend parsing:

- Accuracy card: `response.data.metrics.accuracy`.
- Precision card: `response.data.metrics.precision`.
- Recall card: `response.data.metrics.recall`.
- F1 card: gunakan `response.data.metrics.f1_score`; fallback ke `response.data.metrics.f1`.
- Classification report: `response.data.class_metrics`.

Catatan penting:

- Jangan menganggap field metrics berada di root response.
- Jangan default ke `0` tanpa menandai field hilang; itu dapat menyamarkan mismatch kontrak API sebagai hasil model valid.
- Backend mengirim nilai decimal `0-1`. Bila UI ingin persen, frontend yang mengalikan `100`.

## Contoh Training Dataset Medsos

### Alur Implementasi Frontend

Urutan UI yang disarankan:

1. Upload dataset dan simpan `dataset_id` dari respons.
2. Ambil daftar preset dari `GET /datasets/configuration-presets`.
3. Tampilkan dua radio button atau selection cards: `Mahasiswa Indonesia` dan `Mahasiswa India`.
4. Nonaktifkan tombol lanjut sampai pengguna memilih salah satu preset.
5. Panggil `recommend-config` dengan preset pilihan.
6. Tampilkan halaman konfirmasi berisi target, transformasi target, fitur aktif, split, dan parameter model.
7. Panggil `target-conversion-preview` dengan preset yang sama dan tampilkan distribusi kelas.
8. Saat training, kirim objek konfigurasi hasil `recommend-config` sebagai string pada field multipart `config_json`.

Tipe minimum frontend:

```ts
type DatasetPreset = "indonesia" | "india";

interface ConfigurationPreset {
  id: DatasetPreset;
  label: string;
  description: string;
}

interface TargetTransform {
  type: "numeric_bins";
  scale: number;
  thresholds: number[];
  labels: string[];
}

interface DecisionTreeConfig {
  preset: DatasetPreset;
  task: {
    type: "classification";
    target_column: string;
    positive_class: string | null;
    target_transform: TargetTransform | null;
  };
  preprocessing: Record<string, boolean | string>;
  columns: Array<{
    name: string;
    data_type: string;
    role: "feature" | "target" | "identifier" | "excluded";
    enabled: boolean;
  }>;
  split: Record<string, number | boolean | string>;
  model: Record<string, number | string | null>;
}
```

Contoh pemanggilan:

```ts
const configResponse = await api.post(
  `/datasets/${datasetId}/recommend-config`,
  undefined,
  { params: { preset: selectedPreset } },
);

const config = configResponse.data.data as DecisionTreeConfig;
const form = new FormData();
form.append("run_name", runName);
form.append("config_json", JSON.stringify(config));
form.append("file", uploadedFile);
await api.post("/experiments/runs/upload-train", form);
```

Aturan state dan validasi UI:

- Reset `config` dan preview jika pengguna mengganti preset.
- Jangan mengaktifkan tombol training sebelum rekomendasi untuk preset terbaru berhasil dimuat.
- Tampilkan `preset_label`, target, fitur aktif, dan parameter model pada dialog konfirmasi.
- Jangan mengubah `target_transform` di sisi frontend.
- Jika backend mengembalikan HTTP `422`, tampilkan bahwa preset wajib dipilih.
- Jika backend mengembalikan pesan `Dataset tidak cocok`, pertahankan file yang sudah diunggah dan minta pengguna memilih preset lain atau mengganti file.
- Gunakan preset yang sama untuk `recommend-config` dan `target-conversion-preview`.

Konfigurasi final ikut tersimpan pada experiment run. Halaman detail hasil dapat membaca `config_json.preset`, sedangkan workflow menampilkan `steps[].data.preset` dan `steps[].data.target_transform` pada tahap konversi target.

### Dataset Mahasiswa Indonesia

File contoh:

`Pengaruh Medsos Nilai Akademik Mahasiswa Indonesia.xlsx`

Config final:

`docs/sample_config_pengaruh_medsos_nilai_akademik.json`

Endpoint:

`POST /experiments/runs/upload-train`

Content type:

`multipart/form-data`

Field request:

| Field | Tipe | Wajib | Keterangan |
|---|---|---:|---|
| `run_name` | string | Ya | Nama run, contoh `Medsos IPK Strict Baseline` |
| `config_json` | string JSON | Ya | Isi JSON dari `sample_config_pengaruh_medsos_nilai_akademik.json` |
| `file` | file | Ya | File `.xlsx` dataset |

Contoh `curl`:

```bash
curl -X POST "http://localhost:8000/api/v1/experiments/runs/upload-train" \
  -F "run_name=Medsos IPK Strict Baseline" \
  -F "config_json=<docs/sample_config_pengaruh_medsos_nilai_akademik.json" \
  -F "file=@/path/to/Pengaruh Medsos Nilai Akademik Mahasiswa Indonesia.xlsx"
```

Ringkasan hasil uji lokal dengan config ini:

| Item | Nilai |
|---|---:|
| Jumlah baris | 519 |
| Jumlah kolom | 10 |
| Target | `Apakah Anda merasa prestasi akademik (IPK) Anda baik?` |
| Positive class | `Ya` |
| Fitur aktif sebelum encoding | 8 |
| Fitur aktif setelah encoding | 40 |
| Accuracy | 0.7211538462 |
| Confusion matrix | `[[2, 26], [3, 73]]` |

Catatan interpretasi:

- Baris confusion matrix mengikuti orientasi `rows = actual`, `columns = predicted`.
- Label matrix untuk dataset ini adalah `["Tidak", "Ya"]`.
- Mode `strict` dipakai agar kategori `Program Studi/Jurusan` dan `Platform Media Sosial` lebih ringkas untuk visualisasi frontend.

### Dataset Mahasiswa India

Config referensi:

`docs/sample_config_mahasiswa_india.json`

Gunakan `preset=india` saat mengambil rekomendasi dan preview. Hasil konfigurasi memakai dua fitur, pembagian stratified `80:20`, `random_state=42`, `max_depth=4`, dan `min_samples_leaf=5`. Target `current_sem_CGPA` dikalikan `0.01`, lalu dibagi menjadi `Rendah < 7.0`, `Sedang 7.0-7.99`, dan `Tinggi >= 8.0`.

## Mapping 7 Langkah ke Endpoint

| Langkah | Status backend | Endpoint utama |
|---|---|---|
| EDA | Tersedia | `GET /datasets/{dataset_id}/eda-visualization` |
| Preprocessing data | Tersedia | `GET /experiments/runs/{run_id}/preprocessing-summary` |
| Konversi CGPA ke kategori | Tersedia | `GET /datasets/{dataset_id}/target-conversion-preview` |
| Pembangunan model Decision Tree | Tersedia | `POST /experiments/runs/upload-train`, `GET /experiments/runs/{run_id}` |
| Confusion Matrix | Tersedia | `GET /experiments/runs/{run_id}/confusion-matrix` |
| Accuracy, Precision, Recall, F1 | Tersedia | `GET /experiments/runs/{run_id}/metrics` |
| Visualisasi pohon keputusan | Tersedia | `GET /experiments/runs/{run_id}/tree-visualization` |

## Kontrak Confusion Matrix

`GET /experiments/runs/{run_id}/confusion-matrix`

Frontend harus memakai `values` sebagai matrix 2D sesuai urutan `labels`.
Baris merepresentasikan actual label, kolom merepresentasikan predicted label.

```json
{
  "success": true,
  "data": {
    "run_id": "run_uuid",
    "labels": ["Tidak", "Ya"],
    "values": [
      [2, 26],
      [3, 73]
    ],
    "entries": [
      {
        "actual_label": "Tidak",
        "predicted_label": "Tidak",
        "value": 2
      }
    ],
    "orientation": {
      "rows": "actual",
      "columns": "predicted"
    }
  },
  "meta": {}
}
```

Catatan frontend:

- Cell matrix dibaca dengan `values[rowIndex][columnIndex]`.
- Label baris dan kolom diambil dari array `labels`.
- `entries` disediakan untuk kebutuhan tabel/debug, bukan untuk render grid 2D utama.

## Kontrak Feature Importance

`GET /experiments/runs/{run_id}/feature-importance`

Frontend sebaiknya memakai `original_feature_importance` untuk chart utama
"Original feature importance". Field `feature_importance` dan
`transformed_feature_importance` berisi fitur setelah preprocessing, misalnya
hasil one-hot encoding.

```json
{
  "success": true,
  "data": {
    "run_id": "run_uuid",
    "original_feature_importance": [
      {
        "feature_name": "Tingkat Semester",
        "importance": 0.42,
        "value": 0.42,
        "percentage": 42.0
      }
    ],
    "transformed_feature_importance": [
      {
        "feature_name": "numeric__Tingkat Semester",
        "importance": 0.42,
        "value": 0.42
      }
    ],
    "feature_importance": []
  },
  "meta": {}
}
```

Catatan frontend:

- Chart utama gunakan `response.data.original_feature_importance`.
- Nilai `importance` dan `value` memakai skala `0-1`.
- Nilai `percentage` sudah dalam skala `0-100`.
- Jika tetap memakai `feature_importance`, nama fitur akan berupa transformed feature dan bisa terlihat panjang/terpecah.

## Catatan untuk Tim Frontend

1. Gunakan `workflow-visualization` untuk halaman hasil berbasis `run`.
2. Gunakan `eda-visualization` dan `target-conversion-preview` saat user masih ada di tahap persiapan dataset.
3. Untuk heatmap confusion matrix, gunakan `labels` sebagai sumbu `x` dan `y`.
4. Untuk tree graph, gunakan `nodes` dan `edges` apa adanya; backend tidak mengirim styling.
5. Bila ingin satu halaman end-to-end dari upload sampai hasil model, frontend perlu menyimpan `dataset_id` dan `run_id`.
6. Untuk dataset Excel Anda, mode `strict` memberi hasil visual lebih rapi dengan fitur encoding jauh lebih sedikit dibanding `raw`.
7. Untuk metric cards, baca aggregate metrics dari `response.data.metrics` dan per-class metrics dari `response.data.class_metrics`.
8. Hindari fallback diam-diam ke angka `0` ketika field metrics tidak ada; tampilkan state kosong/error agar mismatch API cepat terlihat.
