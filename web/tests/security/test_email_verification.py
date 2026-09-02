from web.app.models.verification_code import VerificationCode
from web.app import db


def test_send_code(client, app):
    response = client.post("/auth/send_code", data={"email": "test@example.com"})
    assert response.status_code == 302
    assert response.location.endswith("/auth/verify_email")

    record = VerificationCode.query.filter_by(email="test@example.com").first()
    assert record is not None


def test_verify_correct_code(client, app):
    db.session.add(VerificationCode(email="test@example.com", code="123456"))
    db.session.commit()

    with client.session_transaction() as sess:
        sess["pending_email"] = "test@example.com"

    response = client.post("/auth/verify_email", data={"code": "123456"})
    assert response.status_code == 302
    assert response.location.endswith("/auth/register_complete")
