# Lab 19 — Kết quả thực nghiệm và hồ sơ nộp bài

**Học viên:** Lê Văn Sang · **Cohort:** A20-K4 · **Ngày:** 05/10/2026

Đã thực hiện lộ trình **Lite** của README: Python 3.12.14, fastembed
`BAAI/bge-small-en-v1.5` (384 chiều), Qdrant in-memory, BM25, RRF k=60
với rank 1-based, FastAPI và Feast SQLite. Phiên bản thư viện thực tế được
lưu trong [ENVIRONMENT.txt](ENVIRONMENT.txt). Docker và mô hình đa ngữ chưa
được chạy trong hồ sơ này.

## Kết quả core

| Notebook | Kết quả thực đo |
|---|---|
| NB1 | Đã index 1.000 vector; cả 5 kết quả paraphrase thuộc `cloud` |
| NB2 | Hybrid Precision@10 78,6%, BM25 77,8%, Vector 73,2% trên 50 queries |
| NB3 | API trả đủ schema; Hybrid server-side P50/P95/P99 = 11,3/16,3/20,5 ms |
| NB4 | 3 views đã đăng ký và materialize; online P50/P95/P99 = 0,25/0,39/0,59 ms; PIT trả 3 dòng |

NB3 đo 100 request HTTP mỗi mode, sau 10 request warmup mỗi mode. Giá trị
server-side gồm embedding query, BM25, Qdrant và fusion; wall-clock được báo
riêng. Server trong notebook tự chọn một cổng trống và được dừng trong `finally`, cả khi request hoặc benchmark thất bại.
Lệnh API thủ công trong README vẫn dùng cổng 8000.

### Precision@10 theo loại query

| Slice | Số query | BM25 | Vector | Hybrid |
|---|---:|---:|---:|---:|
| exact | 15 | 96,7% | 88,7% | 96,7% |
| paraphrase | 15 | 33,3% | 24,0% | 32,0% |
| mixed | 20 | 97,0% | 98,5% | 100,0% |

Vector **không thắng** ở slice paraphrase với mô hình tiếng Anh của Lite.
Đây là kết quả quan sát, cũng phù hợp hạn chế mô hình mà README/NB2 có nhắc;
không thay đổi corpus, golden set hay công thức RRF để ép kết quả kỳ vọng.
Vì vậy tiêu chí rubric 5 điểm về slice (vector thắng paraphrase) chưa được
đáp ứng đầy đủ. Hồ sơ có thể nộp với số liệu thật; không khẳng định đạt trọn
điểm và chưa thử nghiệm model đa ngữ để chứng minh khả năng cải thiện.
[REFLECTION.md](REFLECTION.md) phân tích lựa chọn từng mode, dưới 200 từ.

### Benchmark chuẩn của README

`scripts/benchmark.py` chạy 5.000 lượt/mode, cùng 50 golden queries. Đây là
benchmark trực tiếp trong tiến trình, gồm query embedding và retrieval;
khác với bảng HTTP server-side của NB3. Số liệu đã được ghi tự động vào
[benchmark.json](benchmark.json) và [logs/benchmark.txt](logs/benchmark.txt).

| Mode | P50 | P95 | P99 |
|---|---:|---:|---:|
| keyword | 2,8 ms | 4,7 ms | 6,3 ms |
| semantic | 15,8 ms | 22,6 ms | 30,4 ms |
| hybrid | 18,4 ms | 25,5 ms | 28,9 ms |

Hybrid đạt P99 < 50 ms và vượt cả hai pure modes về Precision@10. Độ trễ
phụ thuộc máy và tải nền; đây là benchmark tuần tự của lab, chưa phải kiểm
thử production với nhiều người dùng đồng thời.

### Kiểm chứng Point-in-Time

NB4 tạo hai phiên bản hồ sơ cho mỗi user. Với u_001, hồ sơ hiện tại có tốc
độ đọc 187 tại NOW−1h, nhưng sự kiện training xảy ra NOW−2h. PIT chọn phiên
bản cũ 177, trong khi online lookup trả 187. Notebook assert rõ hai kết quả
này, cùng giá trị đúng của u_002/u_003. Item popularity dùng `doc_id` thật
của corpus, phù hợp entity `item`.

## Kết quả nâng cao

| Notebook | Minh chứng |
|---|---|
| NB5 | Filter `acme AND ≥2026` chọn 3,8% corpus: post-filter recall 0,00, filtered-ANN 1,00; over-fetch 500/1.000 đạt recall 1,00 |
| NB6 | Cùng ngân sách 16 doc: single-shot recall/balance 0,526/0,08; agentic no-filter 0,906/0,93; agentic +filter 0,823/0,76; context có Feast features và doc_ids |
| NB7 | Ngưỡng 0,75: 36% false answers trên negative probes; 0,85: tiết kiệm 100% positive probes, 0% false answers; demo leak khi không namespace và MISS khi namespace |
| NB8 | Session target-naive gap 0,477; in-fold −0,003; latest join rò 98,2% dòng, AUC 0,715 so với PIT 0,595; cùng user có ratio 0,03 và 4,21 ở hai amount |

Qdrant local không dùng payload index/HNSW như server. Kết quả recall của
NB5 hợp lệ, nhưng latency không đại diện filtered-ANN production. Threshold
0,85 của NB7 chỉ được chọn cho bộ probe này, cần đánh giá lại khi đổi corpus,
model hoặc phân phối câu hỏi.

## Bonus

Đã có [ARCHITECTURE.md](../bonus/ARCHITECTURE.md),
[agent.py](../bonus/agent.py), [demo.py](../bonus/demo.py).
Kiến trúc trình bày chunking, feature schema, freshness, phương án bị loại
và ngữ cảnh tiếng Việt. Agent thực hiện `remember()`/`recall()` với Qdrant,
BM25 + RRF và profile Feast thật. Demo in đủ 5 context, exit code 0 và assert
không rò memory từ u_002 sang u_001. Xem [logs/bonus_demo.txt](logs/bonus_demo.txt).
POC dùng RAM cho memory và activity đã materialize, chưa cập nhật streaming.
Có chế độ tùy chọn `bonus/demo.py --llm` để sinh câu trả lời tiếng Việt bằng
OpenAI Responses API. Nguồn dữ liệu tổng hợp được mô tả tại
[BONUS_API_DATA.md](BONUS_API_DATA.md).

Lần kiểm tra API ngày 05/10/2026 đã hoàn tất **5/5 câu trả lời**, exit code 0,
model trả về `gpt-4.1-mini-2025-04-14`. Tổng usage: 1.584 input tokens,
543 output tokens, 2.127 tokens. Câu trả lời tiếng Việt có ID ký ức nguồn;
context đã kiểm tra cách ly user trước khi gửi. Xem log thực thi tại
[logs/bonus_llm_demo.txt](logs/bonus_llm_demo.txt). Đây là kiểm tra tích hợp
thành công, chưa phải đánh giá độc lập về độ chính xác của mọi câu trả lời.

## Kiểm tra và tái chạy theo README Lite

README đã được khôi phục về bản gốc. Dùng Git Bash và GNU Make trên Windows,
chạy cùng lộ trình Lite của README; không cần WSL hoặc Docker. Script
`setup-lite.ps1` đã được bỏ. Giữ các sửa tương thích cần thiết cho Python
Windows (`.venv/Scripts`) trong `setup-lite.sh` và Makefile.

Tại thư mục gốc repo, chạy trong Git Bash:

```bash
bash setup-lite.sh
source .venv/Scripts/activate  # Windows; Linux/macOS dùng .venv/bin/activate
make verify-lite
make test
make benchmark
make notebooks
```

`make api` mở FastAPI và `make lab` mở Jupyter theo README. Sau NB4, chạy
`python bonus/demo.py`; tùy chọn `python bonus/demo.py --llm` gọi API trả phí.

GNU Make 4.4.1 dùng trong Git Bash. Lần kiểm chứng sau review đã chạy
trực tiếp các lệnh chuẩn, không chỉ dry-run:

| Lệnh | Kết quả | Log |
|---|---|---|
| `bash setup-lite.sh` | Dependency, seed và smoke test PASS trên môi trường hiện có | [setup_lite_bash.txt](logs/setup_lite_bash.txt) |
| `make verify-lite` | All checks passed | [verify_lite_make.txt](logs/verify_lite_make.txt) |
| `make test` | 53 passed | [tests_make.txt](logs/tests_make.txt) |
| `make benchmark` | 15.000 lượt; Hybrid Precision@10 thắng trung bình, P99 < 50 ms | [benchmark.txt](logs/benchmark.txt) |
| `make notebooks` | 8/8 notebook PASS, output được lưu | [notebooks_recheck.txt](logs/notebooks_recheck.txt) |
| `python bonus/demo.py` | 5 truy vấn PASS, exit 0, không trộn memory giữa user | [bonus_demo.txt](logs/bonus_demo.txt) |

Các thư mục cache uv/Jupyter và thư mục tạm pytest được đặt trong `.venv`
do giới hạn quyền ghi của phiên Codex. Đây là cấu hình phiên kiểm tra,
không thay đổi thuật toán, tiêu chí test hoặc lộ trình Lite của README.
Môi trường được tái setup với venv hiện có; chưa chứng minh cài đặt trên máy
hoàn toàn sạch và chưa chạy lộ trình Docker.

### Sửa sau review

- Runner kiểm tra số notebook trước khi chạy: `99`, hoặc chọn lẫn `01 99`,
  trả lỗi thay vì thành công khi không thực thi đủ notebook. Không có nguồn
  notebook cũng trả lỗi.
- NB3 dùng context manager `running_search_api()` cho toàn bộ request,
  benchmark và assertion. `finally` luôn dọn server do notebook tạo;
  nếu terminate quá hạn thì kill và wait. Không tác động API người dùng mở.
- Bổ sung 6 regression tests cho lựa chọn notebook sai, thiếu notebook,
  lỗi trong query/benchmark, readiness timeout và terminate timeout.
- NB2 giữ model Lite/golden set và RRF k=60; ghi rõ hạn chế paraphrase,
  bỏ khẳng định chưa có thực nghiệm rằng đổi model chắc chắn sẽ thắng.

Repo ban đầu có 41 test. Tổng hiện tại 53 gồm 3 test core, 3 test bonus LLM
và 6 test quy trình notebook. Các test LLM dùng mock transport, không gọi
API trả phí trong lần kiểm chứng này. Log API thật ở mục Bonus là lần chạy
trước, không được trình bày như một lần gọi mới.

## Hồ sơ và ảnh minh chứng

8 file `.ipynb` trong `notebooks/` đã lưu execution counts và outputs.
Ảnh chụp trình duyệt hiển thị trích đoạn stdout của notebook, với SHA-256
nguồn để đối chiếu. Không nhập tay các chỉ số lên ảnh. Trang nguồn nằm trong
[evidence/](evidence/), tái dựng bằng `python scripts/build_evidence.py`.

- [NB1 — index và paraphrase](screenshots/nb1_indexed_1000.png)
- [NB2 — Precision@10](screenshots/nb2_precision_table.png)
- [NB3 — API và P99](screenshots/nb3_latency_p99.png)
- [NB4 — Feast và PIT](screenshots/nb4_feast_materialize.png)

Hồ sơ local đã được kiểm chứng và đủ cấu trúc để nộp. Commit được thực hiện
sau bước kiểm chứng; cần push commit lên repository cá nhân public trước
khi nộp URL vào LMS theo README. Không cần PR. Việc đủ hồ sơ không bảo đảm
trọn điểm: hạn chế slice paraphrase đã được ghi rõ ở trên.

Kiểm tra GitHub công khai ngày 05/10/2026: repo cá nhân đã Public, nhưng
`notebooks/01_embeddings_index.ipynb` và `bonus/ARCHITECTURE.md` chưa có trên
remote tại thời điểm kiểm tra (HTTP 404). Vì vậy cần commit/push các file
trong workspace trước khi nộp URL. README/rubric không yêu cầu report Word/PDF;
`REFLECTION.md` là file Markdown bắt buộc, `ARCHITECTURE.md` bắt buộc khi làm
bonus. `RESULTS.md` này là báo cáo bổ sung để đối chiếu minh chứng.
