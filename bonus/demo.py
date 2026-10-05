"""Run after NB4: python bonus/demo.py (five contexts, exit code 0)."""
from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bonus.agent import HybridMemoryAgent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--llm", action="store_true", help="Generate five answers using the configured OpenAI API key.")
    args = parser.parse_args()
    if not (ROOT / "app/feast_repo/registry.db").exists():
        raise RuntimeError("Run NB4 first in Jupyter (make lab), or run make notebooks.")
    agent = HybridMemoryAgent()
    memories = [
        "Tôi đã đọc Kubernetes: dùng HPA để tự động mở rộng pod theo CPU và lưu lượng truy cập.",
        "Ghi chú cloud: autoscaling giúp co giãn hạ tầng khi nhiều người dùng truy cập; kết hợp spot instance để giảm chi phí.",
        "Tài liệu cloud security: IAM cấp quyền tối thiểu, mã hóa dữ liệu và audit log cho tài nguyên đám mây.",
        "Tôi đang học BM25, vector search, RRF và Feast để cá nhân hóa tìm kiếm.",
        "Gần đây tôi quan tâm chi phí cloud và cân bằng tải giữa nhiều region.",
    ]
    try:
        for text in memories:
            agent.remember(text, "u_001")
        private = "PRIVATE_U002: dữ liệu riêng của người dùng khác về cloud security."
        agent.remember(private, "u_002")
        queries = ["Tôi đã đọc gì về Kubernetes?", "Recommend đọc gì tiếp",
                   "Tôi đang quan tâm gì gần đây?", "Tài liệu về tự động mở rộng hạ tầng?",
                   "Cho tôi summary cloud security"]
        for i, query in enumerate(queries, 1):
            context = agent.recall(query, "u_001")
            assert "PRIVATE_U002" not in context, "Cross-user memory leak"
            assert "reading=187" in context and "queries_last_hour=11" in context
            print(f"\n{'=' * 70}\nQuery {i}/5\n{context}")
            if args.llm:
                # NB4 generates these exact values from i=1; no real profile
                # is allowed across the optional paid API boundary in this demo.
                assert "Profile: language=vi; topic=cloud; reading=187 wpm." in context
                assert "queries_last_hour=11; distinct_topics_24h=4." in context
                from bonus.llm import answer
                result = answer(context)
                print(f"\nLLM answer ({result['model']}):\n{result['text']}")
                print(f"Token usage: {result['usage']}")
        print("\nPASS — 5 queries, real Feast profile, no cross-user episodic leak.")
        if args.llm:
            print("PASS — 5 completed OpenAI Responses API answers.")
        return 0
    finally:
        agent.close()


if __name__ == "__main__":
    sys.exit(main())
