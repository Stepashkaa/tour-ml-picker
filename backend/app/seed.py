from sqlalchemy.orm import Session
from .models import Tour

SEED_TOURS = [
    # Rome
    dict(city="Rome", price=110000, duration_days=7, rating=4.7, season="summer", tour_type="excursion",
         description="Экскурсионный тур по Риму: Колизей, Ватикан, Трастевере."),
    dict(city="Rome", price=90000, duration_days=5, rating=4.4, season="all", tour_type="excursion",
         description="Короткий тур по Риму на 5 дней, насыщенная программа."),
    dict(city="Rome", price=140000, duration_days=10, rating=4.6, season="summer", tour_type="relax",
         description="Рим + отдых, комфортный темп, свободные дни."),

    # Paris
    dict(city="Paris", price=120000, duration_days=6, rating=4.8, season="all", tour_type="excursion",
         description="Париж: музеи, прогулки, Эйфелева башня."),
    dict(city="Paris", price=160000, duration_days=8, rating=4.5, season="summer", tour_type="relax",
         description="Париж и пригород: спокойный отдых и экскурсии."),

    # Barcelona
    dict(city="Barcelona", price=100000, duration_days=7, rating=4.6, season="summer", tour_type="beach",
         description="Барселона: пляж + город, идеальный баланс."),
    dict(city="Barcelona", price=85000, duration_days=5, rating=4.3, season="all", tour_type="beach",
         description="Бюджетный тур в Барселону на 5 дней."),

    # Prague
    dict(city="Prague", price=70000, duration_days=4, rating=4.7, season="all", tour_type="excursion",
         description="Прага: старый город, мосты, замки."),
]

# проверка есть ли у нас туры
def seed_tours_if_empty(db: Session) -> None:
    if db.query(Tour).count() > 0:
        return

    for t in SEED_TOURS:
        db.add(Tour(**t)) # добавление туров
    db.commit()
