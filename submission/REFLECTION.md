# Reflection — Lab 19

**Tên:** Lê Văn Sang · **Cohort:** A20-K4 · **Path:** Lite

Trên 50 golden queries, Precision@10 trung bình: BM25 77,8%, Vector 73,2%,
Hybrid 78,6%. Với `exact`, BM25 và Hybrid cùng đạt 96,7%, Vector 88,7%:
từ khóa kỹ thuật giúp BM25 khớp chính xác. Với `mixed`, Hybrid đạt 100%,
vượt BM25 97% và Vector 98,5%; RRF tận dụng hai danh sách bổ sung nhau.

Với `paraphrase`, BM25 đạt 33,3%, Hybrid 32%, Vector 24%. Vector không thắng
trong cấu hình Lite thực đo: bge-small-en-v1.5 thiên về tiếng Anh, yếu với
diễn đạt tiếng Việt. Không nên suy luận chất lượng chỉ từ loại thuật toán.

Tôi chọn pure BM25 khi tìm mã lỗi, định danh, tên API hoặc từ khóa chính xác,
đặc biệt khi cần độ trễ thấp. Tôi chọn pure vector khi truy vấn thiên về
ý nghĩa, ít khớp từ vựng, và mô hình đa ngữ đã được kiểm chứng trên corpus.
Hybrid phù hợp truy vấn hỗn hợp nhưng tăng chi phí embedding và fusion;
quyết định cần dựa trên chất lượng từng slice và latency thực tế.

Đã hoàn thành NB1–NB8 và bonus trong `bonus/`.
