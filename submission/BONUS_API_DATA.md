# Dữ liệu cho demo API bonus

`bonus/demo.py --llm` chỉ gửi context của tài khoản mẫu `u_001` tới
`https://api.openai.com/v1/responses` để trả lời năm câu hỏi trong đề lab.

- Năm ký ức được viết trực tiếp trong `bonus/demo.py`: ghi chú minh họa về
  Kubernetes, autoscaling, IAM, BM25/RRF/Feast và chi phí cloud.
- Qdrant của agent là `:memory:` mới cho mỗi lần chạy. Demo không đọc ký ức
  cá nhân từ ổ đĩa hay từ tài khoản của người dùng.
- Hồ sơ Feast được NB4 sinh bằng công thức trong `make_user_profile()` và
  `make_query_velocity()`, với i=1: ngôn ngữ `vi`, topic `cloud`, tốc độ đọc
  `180 + 7 = 187`, số query `(1 * 11) % 50 = 11`, số topic `1 + 3 = 4`.
- Demo kiểm tra các giá trị mẫu này trước mỗi lần gọi API và kiểm tra rằng
  ký ức mẫu `PRIVATE_U002` của tài khoản khác không nằm trong context.
- API key chỉ dùng trong header xác thực, không ghi vào log. `store=false`
  được gửi trong request để tắt lưu response theo tùy chọn Responses API.

Đây là dữ liệu học tập tổng hợp, không phải lịch sử hoặc hồ sơ cá nhân của
Lê Văn Sang. Khi dùng dữ liệu người thật, cần xác thực, chính sách quyền riêng
tư và quyết định cho phép gửi context tới nhà cung cấp mô hình.
