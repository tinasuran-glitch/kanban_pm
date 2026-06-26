from app.main import is_authenticated_cookie, is_valid_credentials


def test_valid_credentials() -> None:
    assert is_valid_credentials("user", "password") is True


def test_invalid_credentials() -> None:
    assert is_valid_credentials("user", "wrong") is False
    assert is_valid_credentials("wrong", "password") is False


def test_cookie_authentication() -> None:
    assert is_authenticated_cookie("mvp-user") is True
    assert is_authenticated_cookie(None) is False
    assert is_authenticated_cookie("something-else") is False
