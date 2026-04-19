"""Tests for the hosted deployment contract."""

from __future__ import annotations

from pathlib import Path


def _repo_file(*parts: str) -> Path:
    return Path(__file__).resolve().parents[1].joinpath(*parts)


def test_hosted_compose_uses_same_origin_frontend_and_bm25_safe_backend() -> None:
    text = _repo_file("docker-compose.hosted.yml").read_text(encoding="utf-8")

    assert 'INSTALL_SEMANTIC: "false"' in text
    assert 'VITE_API_BASE_URL: ""' in text


def test_hosted_nginx_reserves_admin_page_and_admin_api_paths() -> None:
    text = _repo_file("frontend", "nginx.conf").read_text(encoding="utf-8")

    assert "location = /admin {" in text
    assert "location = /admin/ {" in text
    assert "location ^~ /admin/ {" in text


def test_frontend_prod_image_uses_hosted_nginx_config() -> None:
    text = _repo_file("frontend", "Dockerfile").read_text(encoding="utf-8")

    assert "COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf" in text
