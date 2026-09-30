from flask import Flask
from app.auth import require_api_key
from app.errors import AuthenticationError
from app.validation import parse_pagination

def test_api_key_missing_raises() -> None:
    app=Flask(__name__)
    @app.get("/protected")
    @require_api_key(("test-key",))
    def protected(): return {"ok":True}
    with app.test_request_context("/protected"):
        try: protected()
        except AuthenticationError as error: assert error.message == "Missing or invalid API key"
        else: raise AssertionError("authentication was not enforced")

def test_pagination_defaults_and_cap() -> None:
    assert parse_pagination({}) == (1,20)
    try: parse_pagination({"per_page":"101"})
    except Exception: pass
    else: raise AssertionError("cap was not enforced")
