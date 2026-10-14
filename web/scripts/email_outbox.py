"""Look at and drive the email outbox by hand.

    python -m web.scripts.email_outbox            # counts by status
    python -m web.scripts.email_outbox --failed   # the failed ones (no addresses)
    python -m web.scripts.email_outbox --send     # send what is due now

The web workers send queued emails on their own; this is for checking on
them (failed rows are also logged at ERROR) and for local development,
where no gunicorn worker runs.
"""

import argparse

from backend.app.extensions import db
from backend.app.models.email_outbox import EmailOutbox
from backend.app.services import email_outbox
from web.app import create_app


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--failed", action="store_true", help="list failed emails")
    parser.add_argument("--send", action="store_true", help="send the due emails now")
    args = parser.parse_args(argv)

    app = create_app(pages=False)
    with app.app_context():
        if args.send:
            print("sent:", email_outbox.process_due())
        print("outbox:", email_outbox.counts())
        if args.failed:
            failed = EmailOutbox.query.filter_by(status=EmailOutbox.FAILED).order_by(EmailOutbox.id)
            for row in failed:
                print(f"#{row.id} {row.kind} attempts={row.attempts} created={row.created_at:%Y-%m-%d %H:%M} "
                      f"error={row.last_error}")
        db.session.remove()


if __name__ == "__main__":
    main()
