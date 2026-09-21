"""Manual acceptance battery against a deployed Equity Strategist API."""

import os
import sys

import httpx


def main() -> None:
    base_url = os.environ["EQUITY_STRATEGIST_BASE_URL"].rstrip("/")
    api_key = os.environ["EQUITY_STRATEGIST_API_KEY"]
    headers = {"Authorization": f"Bearer {api_key}"}

    with httpx.Client(base_url=base_url, timeout=120) as client:
        health = client.get("/health")
        health.raise_for_status()
        assert health.json()["status"] == "ok"
        print("PASS health")

        unauthorized = client.post("/v1/chat", json={"question": "test"})
        assert unauthorized.status_code == 401
        print("PASS unauthenticated chat rejected")

        def chat(question: str, thread_id: str | None = None) -> dict:
            payload = {"question": question, "include_evidence": True}
            if thread_id is not None:
                payload["thread_id"] = thread_id
            response = client.post("/v1/chat", headers=headers, json=payload)
            response.raise_for_status()
            return response.json()

        one_turn = chat(
            "Compare Schneider Electric and Safran by historical performance "
            "from 2024-01-01 to 2025-12-31."
        )
        assert one_turn["status"] == "success" and one_turn["evidence"]["steps"]
        print("PASS one-turn analysis")

        feedback_payload = {"request_id": one_turn["request_id"], "useful": True}
        denied_feedback = client.post("/v1/feedback", json=feedback_payload)
        assert denied_feedback.status_code == 401
        feedback = client.post("/v1/feedback", headers=headers, json=feedback_payload)
        persistence_expected = (
            os.getenv("EQUITY_STRATEGIST_SMOKE_EXPECT_PERSISTENCE", "false").lower()
            == "true"
        )
        if persistence_expected:
            assert feedback.status_code == 201
            assert feedback.json()["request_id"] == one_turn["request_id"]
            print(f"Stored run request_id={one_turn['request_id']}")
            for useful, comment in ((False, ""), (1, "Shortcut positive"), (0, None)):
                checked = client.post(
                    "/v1/feedback",
                    headers=headers,
                    json={
                        "request_id": one_turn["request_id"],
                        "useful": useful,
                        "comment": comment,
                    },
                )
                assert checked.status_code == 201
                assert checked.json()["request_id"] == one_turn["request_id"]
            from uuid import uuid4

            missing = client.post(
                "/v1/feedback",
                headers=headers,
                json={
                    "request_id": str(uuid4()),
                    "useful": False,
                },
            )
            assert missing.status_code == 404
        else:
            assert feedback.status_code == 503
        print("PASS authenticated feedback and configured persistence behavior")

        first = chat(
            "Compare Schneider Electric and Safran by performance and risk "
            "from 2024-01-01 to 2025-12-31."
        )
        assert first["status"] == "needs_clarification"
        assert first["validation"]["issue_codes"]
        print("PASS clarification required")

        second = chat("Use historical volatility for risk.", first["thread_id"])
        assert second["status"] == "success"
        assert second["thread_id"] == first["thread_id"]
        assert second["evidence"]["steps"]
        print("PASS same-thread refinement")

        horizon = chat(
            "Compare Schneider Electric and Safran's excess return over the "
            "S&P 500 over 1Y as of 2025-12-31."
        )
        assert horizon["status"] == "success"
        assert horizon["request"]["benchmark"] == "S&P 500"
        assert horizon["request"]["horizons"] == ["1y"]
        assert horizon["request"]["performance_measure"] == "excess_return"
        assert horizon["evidence"]["steps"]
        print("PASS horizon and benchmark evidence")

    print("Remote API smoke battery passed (including feedback and validation codes).")


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, KeyError, httpx.HTTPError) as exc:
        print(f"Remote API smoke battery failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
