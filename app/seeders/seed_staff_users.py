from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.role import Role
from app.models.staff_user import StaffUser


FIRST_NAMES = [
    "Jean", "Sarah", "Mickael", "Lina", "Paul",
    "Anna", "David", "Fara", "Lucas", "Nina",
    "Eric", "Mialy", "Tiana", "Joel", "Kevin",
    "Sandra", "Hery", "Aina", "Rado", "Elisa",
    "Bryan", "Sophie", "Tony", "Claire", "Mamy",
    "Olivia", "Noah", "Emma", "Lova", "Yvan",
]

LAST_NAMES = [
    "Rakoto", "Rabe", "Andriam", "Ranaivo", "Rasolo",
    "Andry", "Randria", "Razaka", "Ravelo", "Raman",
    "Rasoana", "Rija", "Tahina", "Miora", "Sitraka",
    "Fenosoa", "Nirina", "Haja", "Malala", "Soa",
    "Ravel", "Andrian", "Vola", "Rakotobe", "Ratsimba",
    "Heriniaina", "Faniry", "Tsanta", "Randranto", "Raveloson",
]


def build_staff_user(index: int, role_id: int) -> dict:
    first_name = FIRST_NAMES[index % len(FIRST_NAMES)]
    last_name = LAST_NAMES[index % len(LAST_NAMES)]
    now = datetime.utcnow()

    is_active = index % 6 != 0
    failed_login_attempts = index % 4

    last_login_at = now - timedelta(days=index, hours=index % 12)

    locked_until = None
    if not is_active and index % 3 == 0:
        locked_until = now + timedelta(hours=2 + index)

    return {
        "role_id": role_id,
        "first_name": first_name,
        "last_name": last_name,
        "email": f"agent{index + 1:02d}@rfid.local",
        "password_hash": hash_password("agent1234"),
        "is_active": is_active,
        "failed_login_attempts": failed_login_attempts,
        "last_login_at": last_login_at,
        "locked_until": locked_until,
    }


def seed_staff_users(db: Session, total: int = 30) -> None:
    agent_role = db.query(Role).filter(Role.name == "agent").first()

    if not agent_role:
        raise Exception("Le rôle agent n'existe pas. Lance d'abord seed_roles.")

    created = 0

    for i in range(total):
        item = build_staff_user(i, agent_role.id)

        exists = db.query(StaffUser).filter(StaffUser.email == item["email"]).first()
        if exists:
            continue

        db.add(StaffUser(**item))
        created += 1

    db.commit()
    print(f"{created} agents seeded successfully.")


def main():
    db = SessionLocal()
    try:
        seed_staff_users(db, total=30)
    finally:
        db.close()


if __name__ == "__main__":
    main()