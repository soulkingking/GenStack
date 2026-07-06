import httpx

from app.core.logging import masked_response_preview


def test_masked_preview_hides_sensitive_fields_recursively() -> None:
    response = httpx.Response(
        200,
        json={
            "code": 200,
            "result": {
                "access_token": "secret-access-token",
                "refreshToken": "secret-refresh-token",
                "nested": {"clientSecret": "secret-value", "username": "admin"},
                "items": [{"password": "secret-password", "deptName": "平台部"}],
            },
        },
    )

    preview = masked_response_preview(response)

    assert "secret-access-token" not in preview
    assert "secret-refresh-token" not in preview
    assert "secret-value" not in preview
    assert "secret-password" not in preview
    assert preview.count("***") == 4
    # 非敏感业务字段保持原样，日志才有排查价值。
    assert '"username": "admin"' in preview
    assert "平台部" in preview


def test_masked_preview_falls_back_to_truncated_text_for_invalid_json() -> None:
    response = httpx.Response(200, text="<html>" + "x" * 5000)

    preview = masked_response_preview(response)

    assert preview.startswith("<html>")
    assert len(preview) < 2200
    assert "截断" in preview


def test_masked_preview_keeps_short_json_untruncated() -> None:
    response = httpx.Response(200, json={"code": 200, "success": True, "result": {}})

    preview = masked_response_preview(response)

    assert preview == '{"code": 200, "success": true, "result": {}}'
