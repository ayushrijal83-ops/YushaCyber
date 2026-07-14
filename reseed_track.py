"""Clear the old Linux lab content so the YC-012.3 track seeds cleanly.

The Linux track replaced the single 'linux-basics' lab with nine sequential
labs, a much larger virtual filesystem, and new objectives/validators. This
removes the old Linux labs (and any sessions/progress tied to them) so the
seeder can rebuild the track from scratch.

Only Linux LAB content is touched. Your account, XP, achievements,
certificates, quizzes, CTF progress and every other feature are untouched.

    python reseed_track.py
    flask seed-labs
"""

from app import create_app
from app.extensions import db
from app.labs.models import (
    Lab,
    LabCategory,
    LabFileSystemNode,
    LabObjective,
    UserLabProgress,
    UserLabSession,
    UserObjectiveProgress,
)

app = create_app()

with app.app_context():
    category = LabCategory.query.filter_by(slug="linux").first()
    if category is None:
        print("No 'linux' category found — nothing to clear.")
        print("Just run:  flask seed-labs")
        raise SystemExit(0)

    labs = Lab.query.filter_by(category_id=category.id).all()
    if not labs:
        print("No Linux labs found — nothing to clear.")
        print("Just run:  flask seed-labs")
        raise SystemExit(0)

    lab_ids = [lab.id for lab in labs]
    objective_ids = [
        o.id for o in LabObjective.query.filter(
            LabObjective.lab_id.in_(lab_ids)
        ).all()
    ]

    if objective_ids:
        UserObjectiveProgress.query.filter(
            UserObjectiveProgress.objective_id.in_(objective_ids)
        ).delete(synchronize_session=False)

    UserLabSession.query.filter(
        UserLabSession.lab_id.in_(lab_ids)
    ).delete(synchronize_session=False)

    UserLabProgress.query.filter(
        UserLabProgress.lab_id.in_(lab_ids)
    ).delete(synchronize_session=False)

    LabFileSystemNode.query.filter(
        LabFileSystemNode.lab_id.in_(lab_ids)
    ).delete(synchronize_session=False)

    LabObjective.query.filter(
        LabObjective.lab_id.in_(lab_ids)
    ).delete(synchronize_session=False)

    # Clear prerequisite links first so the FK doesn't block deletion.
    for lab in labs:
        lab.prerequisite_lab_id = None
    db.session.flush()

    for lab in labs:
        db.session.delete(lab)

    db.session.commit()

    print(f"Removed {len(labs)} old Linux lab(s) and their content.")
    print("\nNow run:  flask seed-labs")