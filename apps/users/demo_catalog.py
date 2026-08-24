"""Shared PulseFit demo personas, events and horizon helpers.

Celebrity usernames are stable fixture identities. `axelio` is never renamed.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import date, time
from decimal import Decimal

PRESERVED_USERNAMES = frozenset({"axelio"})
DEMO_PASSWORD = "demo1234"
KRISTINA_USERNAME = "kristina.girod"
TOMAS_USERNAME = "tomasride"


def demo_history_start(today: date) -> date:
    """1 January of last year."""
    return date(today.year - 1, 1, 1)


def demo_horizon_end(today: date) -> date:
    """Last day of February next year (leap-year aware)."""
    year = today.year + 1
    return date(year, 2, calendar.monthrange(year, 2)[1])


coach_seed_start = demo_history_start
coach_seed_end = demo_horizon_end


@dataclass(frozen=True)
class Persona:
    username: str
    first_name: str
    last_name: str
    is_instructor: bool = False
    is_staff: bool = False
    gender: str = "other"
    phone_number: str = ""
    birthdate: date | None = None
    address: str = ""
    height_cm: int | None = None
    weight_kg: Decimal | None = None
    shoe_size: Decimal | None = None
    seat_height: int | None = None
    seat_distance: int | None = None
    handlebar_distance: int | None = None
    cycling_shoe_size: Decimal | None = None
    waitlist_auto_confirm: bool = False
    tagline: str = ""
    description: str = ""
    website_url: str = ""
    instagram_username: str = ""
    tiktok_username: str = ""
    is_verified: bool = False
    instructor_since: date | None = None
    location: str = ""
    specialties: tuple[str, ...] = field(default_factory=tuple)
    languages: tuple[str, ...] = field(default_factory=tuple)
    certifications: tuple[str, ...] = field(default_factory=tuple)
    last_spotify_playlist: str = ""
    last_apple_music_playlist: str = ""
    last_youtube_music_playlist: str = ""

    @property
    def email(self) -> str:
        return f"{self.username.replace('.', '_')}@pulsefit.cl"


def _d(value: str) -> Decimal:
    return Decimal(value)


INSTRUCTORS: tuple[Persona, ...] = (
    Persona(
        username=KRISTINA_USERNAME,
        first_name="Kristina",
        last_name="Girod",
        is_instructor=True,
        is_staff=True,
        gender="female",
        phone_number="+56911110001",
        birthdate=date(1991, 3, 14),
        address="Camino El Alba 12345, Las Condes — camarín de la coach estrella",
        height_cm=168,
        weight_kg=_d("58.40"),
        shoe_size=_d("38.5"),
        seat_height=74,
        seat_distance=10,
        handlebar_distance=9,
        cycling_shoe_size=_d("38.5"),
        waitlist_auto_confirm=True,
        tagline="La capitana de PulseFit · climbs con glitter",
        description=(
            "Kristina Girod no calienta motores: los enamora. Head coach de PulseFit, "
            "mezcla cueing quirúrgico con playlists que hacen llorar a los woofers. "
            "Si el puesto 1 está libre, no lo está: lo está guardando el destino."
        ),
        website_url="https://pulsefit.cl/coaches/kristina-girod",
        instagram_username="kristinagirod",
        tiktok_username="kristina.girod.ride",
        is_verified=True,
        instructor_since=date(2016, 5, 1),
        location="Las Condes, Santiago",
        specialties=("Power Ride", "Climb", "HIIT", "Signature Girod"),
        languages=("Español", "English", "Deutsch"),
        certifications=(
            "Schwinn Indoor Cycling",
            "First Aid / RCP",
            "Licencia informal para subir el BPM",
        ),
        last_spotify_playlist="https://open.spotify.com/playlist/kristina-girod-power",
        last_apple_music_playlist="https://music.apple.com/playlist/kristina-girod-power",
        last_youtube_music_playlist="https://music.youtube.com/playlist?list=KRISTINA_GIROD",
    ),
    Persona(
        username=TOMAS_USERNAME,
        first_name="Tomás",
        last_name="Muñoz",
        is_instructor=True,
        is_staff=True,
        gender="male",
        phone_number="+56911112222",
        birthdate=date(1993, 7, 22),
        address="Av. Las Condes 11000, depto con bicicleta colgada",
        height_cm=181,
        weight_kg=_d("76.20"),
        shoe_size=_d("43.0"),
        seat_height=82,
        seat_distance=12,
        handlebar_distance=11,
        cycling_shoe_size=_d("43.0"),
        tagline="Power Ride · HIIT cycling",
        description="Coach de indoor cycling en PulseFit. Power, climbs y sprints.",
        website_url="https://pulsefit.cl/coaches/tomas-munoz",
        instagram_username="tomasride",
        tiktok_username="tomasride",
        is_verified=True,
        instructor_since=date(2022, 1, 15),
        location="Santiago, Chile",
        specialties=("Power Ride", "HIIT", "Climb"),
        languages=("Español", "English"),
        certifications=("Schwinn Indoor Cycling", "First Aid / RCP"),
        last_spotify_playlist="https://open.spotify.com/playlist/tomasride-power",
        last_apple_music_playlist="https://music.apple.com/playlist/tomasride-power",
        last_youtube_music_playlist="https://music.youtube.com/playlist?list=TOMASRIDE",
    ),
    Persona(
        username="michelle.obama",
        first_name="Michelle",
        last_name="Obama",
        is_instructor=True,
        is_staff=True,
        gender="female",
        phone_number="+56911110002",
        birthdate=date(1964, 1, 17),
        address="White House West Wing, sucursal Las Condes",
        height_cm=180,
        weight_kg=_d("70.00"),
        shoe_size=_d("41.0"),
        seat_height=84,
        seat_distance=11,
        handlebar_distance=10,
        cycling_shoe_size=_d("41.0"),
        tagline="When they go low, we climb high",
        description=(
            "Arms Tour 2026: ahora con cadencia. Michelle dirige el Let's Move Ride "
            "y no acepta resistencia 1 ni como broma."
        ),
        website_url="https://pulsefit.cl/coaches/michelle-obama",
        instagram_username="michelleobama",
        tiktok_username="flotus.ride",
        is_verified=True,
        instructor_since=date(2009, 1, 20),
        location="Chicago / Santiago",
        specialties=("Sculpt", "Power Ride", "Community"),
        languages=("English", "Español"),
        certifications=("Let's Move Coach", "First Aid / RCP"),
        last_spotify_playlist="https://open.spotify.com/playlist/obama-arms",
        last_apple_music_playlist="https://music.apple.com/playlist/obama-arms",
        last_youtube_music_playlist="https://music.youtube.com/playlist?list=OBAMA_ARMS",
    ),
    Persona(
        username="tom.cruise",
        first_name="Tom",
        last_name="Cruise",
        is_instructor=True,
        is_staff=True,
        gender="male",
        phone_number="+56911110003",
        birthdate=date(1962, 7, 3),
        address="Misión: Patio Andino. Cohete opcional.",
        height_cm=170,
        weight_kg=_d("67.80"),
        shoe_size=_d("41.0"),
        seat_height=76,
        seat_distance=9,
        handlebar_distance=8,
        cycling_shoe_size=_d("41.0"),
        tagline="Impossible Ride — protocol 7",
        description=(
            "Tom no enseña sprints: los filma en IMAX. Si se cae el manubrio, "
            "lo sostiene con la sonrisa."
        ),
        website_url="https://pulsefit.cl/coaches/tom-cruise",
        instagram_username="tomcruise",
        tiktok_username="ethanhunt.ride",
        is_verified=True,
        instructor_since=date(1996, 5, 22),
        location="Hollywood / Las Condes",
        specialties=("HIIT", "Night Power", "Stunt Sprints"),
        languages=("English", "Español"),
        certifications=("STG Cycling", "Helicóptero nivel 3 (honorífico)"),
        last_spotify_playlist="https://open.spotify.com/playlist/mission-ride",
        last_apple_music_playlist="https://music.apple.com/playlist/mission-ride",
        last_youtube_music_playlist="https://music.youtube.com/playlist?list=MISSION_RIDE",
    ),
    Persona(
        username="nicole.kidman",
        first_name="Nicole",
        last_name="Kidman",
        is_instructor=True,
        is_staff=True,
        gender="female",
        phone_number="+56911110004",
        birthdate=date(1967, 6, 20),
        address="Hotel Costanera, suite con velas y clip-ins",
        height_cm=180,
        weight_kg=_d("63.00"),
        shoe_size=_d("40.0"),
        seat_height=83,
        seat_distance=10,
        handlebar_distance=9,
        cycling_shoe_size=_d("40.0"),
        tagline="Eyes Wide Cadence",
        description=(
            "Nicole enseña climbs en cámara lenta emocional. El cool-down incluye "
            "un monólogo y un vaso de agua sparkling."
        ),
        website_url="https://pulsefit.cl/coaches/nicole-kidman",
        instagram_username="nicolekidman",
        tiktok_username="kidman.climb",
        is_verified=True,
        instructor_since=date(2001, 12, 10),
        location="Sydney / Santiago",
        specialties=("Climb", "Yoga Ride", "Cool-down cinema"),
        languages=("English", "Español"),
        certifications=("Moulin Rouge Endurance", "First Aid / RCP"),
        last_spotify_playlist="https://open.spotify.com/playlist/kidman-climb",
        last_apple_music_playlist="https://music.apple.com/playlist/kidman-climb",
        last_youtube_music_playlist="https://music.youtube.com/playlist?list=KIDMAN_CLIMB",
    ),
    Persona(
        username="usain.bolt",
        first_name="Usain",
        last_name="Bolt",
        is_instructor=True,
        is_staff=True,
        gender="male",
        phone_number="+56911110005",
        birthdate=date(1986, 8, 21),
        address="Pista 8, Patio Andino (récord incluido)",
        height_cm=195,
        weight_kg=_d("94.00"),
        shoe_size=_d("47.0"),
        seat_height=92,
        seat_distance=14,
        handlebar_distance=12,
        cycling_shoe_size=_d("47.0"),
        tagline="9.58 de cadencia, 0.00 de excusas",
        description=(
            "Usain convierte cada sprint en final olímpica. El lightning pose es "
            "mandatory al minuto 32."
        ),
        website_url="https://pulsefit.cl/coaches/usain-bolt",
        instagram_username="usainbolt",
        tiktok_username="lightning.ride",
        is_verified=True,
        instructor_since=date(2017, 8, 5),
        location="Jamaica / Santiago",
        specialties=("Sprints", "HIIT", "Weekend Ride"),
        languages=("English", "Español", "Patois"),
        certifications=("IAAF Honorary Spin", "First Aid / RCP"),
        last_spotify_playlist="https://open.spotify.com/playlist/bolt-sprints",
        last_apple_music_playlist="https://music.apple.com/playlist/bolt-sprints",
        last_youtube_music_playlist="https://music.youtube.com/playlist?list=BOLT_SPRINTS",
    ),
    Persona(
        username="shakira",
        first_name="Shakira",
        last_name="Mebarak",
        is_instructor=True,
        is_staff=True,
        gender="female",
        phone_number="+56911110006",
        birthdate=date(1977, 2, 2),
        address="Caderas no mienten 45, Las Condes",
        height_cm=157,
        weight_kg=_d("54.00"),
        shoe_size=_d("37.0"),
        seat_height=68,
        seat_distance=8,
        handlebar_distance=7,
        cycling_shoe_size=_d("37.0"),
        tagline="Hips don't lie, the cadence does not either",
        description="Shakira enseña SCULPT Ride: si las caderas no se mueven, la resistencia sí.",
        website_url="https://pulsefit.cl/coaches/shakira",
        instagram_username="shakira",
        tiktok_username="shakira.sculpt",
        is_verified=True,
        instructor_since=date(2006, 6, 9),
        location="Barranquilla / Santiago",
        specialties=("SCULPT Ride", "Party Ride", "Latin Power"),
        languages=("Español", "English", "Português"),
        certifications=("Waka Waka Endurance", "First Aid / RCP"),
        last_spotify_playlist="https://open.spotify.com/playlist/shakira-sculpt",
        last_apple_music_playlist="https://music.apple.com/playlist/shakira-sculpt",
        last_youtube_music_playlist="https://music.youtube.com/playlist?list=SHAKIRA_SCULPT",
    ),
    Persona(
        username="pedro.pascal",
        first_name="Pedro",
        last_name="Pascal",
        is_instructor=True,
        is_staff=True,
        gender="male",
        phone_number="+56911110007",
        birthdate=date(1975, 4, 2),
        address="This is the Way 12, Providencia",
        height_cm=180,
        weight_kg=_d("79.00"),
        shoe_size=_d("43.0"),
        seat_height=81,
        seat_distance=11,
        handlebar_distance=10,
        cycling_shoe_size=_d("43.0"),
        tagline="This is the Way (a 140 BPM)",
        description="Pedro abre la sala como si fuera un set. Abrazos post-clase: ilimitados.",
        website_url="https://pulsefit.cl/coaches/pedro-pascal",
        instagram_username="pascallisp",
        tiktok_username="daddy.cadence",
        is_verified=True,
        instructor_since=date(2019, 11, 12),
        location="Chile / Hollywood",
        specialties=("RIDE 45", "After Work", "Storytelling climb"),
        languages=("Español", "English"),
        certifications=("Mandalorian Mindfulness", "First Aid / RCP"),
        last_spotify_playlist="https://open.spotify.com/playlist/pascal-ride",
        last_apple_music_playlist="https://music.apple.com/playlist/pascal-ride",
        last_youtube_music_playlist="https://music.youtube.com/playlist?list=PASCAL_RIDE",
    ),
)

MEMBERS: tuple[Persona, ...] = (
    Persona(
        username="taylor.swift",
        first_name="Taylor",
        last_name="Swift",
        gender="female",
        phone_number="+56922220001",
        birthdate=date(1989, 12, 13),
        address="The Eras Parking, Patio Andino",
        height_cm=180,
        weight_kg=_d("62.00"),
        shoe_size=_d("40.0"),
        seat_height=82,
        seat_distance=10,
        handlebar_distance=9,
        cycling_shoe_size=_d("40.0"),
        waitlist_auto_confirm=True,
    ),
    Persona(
        username="bad.bunny",
        first_name="Bad",
        last_name="Bunny",
        gender="male",
        phone_number="+56922220002",
        birthdate=date(1994, 3, 10),
        address="Nadie Sabe lo que va a pasar mañana 8",
        height_cm=178,
        weight_kg=_d("78.00"),
        shoe_size=_d("43.0"),
        seat_height=80,
        seat_distance=11,
        handlebar_distance=10,
        cycling_shoe_size=_d("43.0"),
        waitlist_auto_confirm=True,
    ),
    Persona(
        username="zendaya",
        first_name="Zendaya",
        last_name="Coleman",
        gender="female",
        phone_number="+56922220003",
        birthdate=date(1996, 9, 1),
        address="Arrakis 10, Las Condes (arena no incluida)",
        height_cm=178,
        weight_kg=_d("61.00"),
        shoe_size=_d("40.5"),
        seat_height=81,
        seat_distance=9,
        handlebar_distance=8,
        cycling_shoe_size=_d("40.5"),
    ),
    Persona(
        username="lionel.messi",
        first_name="Lionel",
        last_name="Messi",
        gender="male",
        phone_number="+56922220004",
        birthdate=date(1987, 6, 24),
        address="Rosario 10, sucursal Interlagos",
        height_cm=170,
        weight_kg=_d("72.00"),
        shoe_size=_d("41.0"),
        seat_height=75,
        seat_distance=8,
        handlebar_distance=8,
        cycling_shoe_size=_d("41.0"),
        waitlist_auto_confirm=True,
    ),
    Persona(
        username="serena.williams",
        first_name="Serena",
        last_name="Williams",
        gender="female",
        phone_number="+56922220005",
        birthdate=date(1981, 9, 26),
        address="Court 1 convertido en sala de bikes",
        height_cm=175,
        weight_kg=_d("70.00"),
        shoe_size=_d("41.0"),
        seat_height=79,
        seat_distance=10,
        handlebar_distance=9,
        cycling_shoe_size=_d("41.0"),
    ),
    Persona(
        username="ryan.gosling",
        first_name="Ryan",
        last_name="Gosling",
        gender="male",
        phone_number="+56922220006",
        birthdate=date(1980, 11, 12),
        address="Ken's DreamHouse, Las Condes",
        height_cm=184,
        weight_kg=_d("80.00"),
        shoe_size=_d("44.0"),
        seat_height=85,
        seat_distance=12,
        handlebar_distance=11,
        cycling_shoe_size=_d("44.0"),
    ),
    Persona(
        username="margot.robbie",
        first_name="Margot",
        last_name="Robbie",
        gender="female",
        phone_number="+56922220007",
        birthdate=date(1990, 7, 2),
        address="Barbie Pink Locker 3",
        height_cm=168,
        weight_kg=_d("58.00"),
        shoe_size=_d("38.0"),
        seat_height=73,
        seat_distance=9,
        handlebar_distance=8,
        cycling_shoe_size=_d("38.0"),
        waitlist_auto_confirm=True,
    ),
    Persona(
        username="keanu.reeves",
        first_name="Keanu",
        last_name="Reeves",
        gender="male",
        phone_number="+56922220008",
        birthdate=date(1964, 9, 2),
        address="Zion, piso -1 (muy amable con el staff)",
        height_cm=186,
        weight_kg=_d("84.00"),
        shoe_size=_d("45.0"),
        seat_height=88,
        seat_distance=13,
        handlebar_distance=12,
        cycling_shoe_size=_d("45.0"),
    ),
    Persona(
        username="beyonce",
        first_name="Beyoncé",
        last_name="Knowles",
        gender="female",
        phone_number="+56922220009",
        birthdate=date(1981, 9, 4),
        address="Hive Penthouse, Costanera Center",
        height_cm=169,
        weight_kg=_d("62.00"),
        shoe_size=_d("39.0"),
        seat_height=74,
        seat_distance=9,
        handlebar_distance=8,
        cycling_shoe_size=_d("39.0"),
        waitlist_auto_confirm=True,
    ),
    Persona(
        username="the.rock",
        first_name="Dwayne",
        last_name="Johnson",
        gender="male",
        phone_number="+56922220010",
        birthdate=date(1972, 5, 2),
        address="Iron Paradise 7, Vitacura",
        height_cm=196,
        weight_kg=_d("118.00"),
        shoe_size=_d("48.0"),
        seat_height=96,
        seat_distance=15,
        handlebar_distance=14,
        cycling_shoe_size=_d("48.0"),
    ),
    Persona(
        username="chayanne",
        first_name="Chayanne",
        last_name="Figueroa",
        gender="male",
        phone_number="+56922220011",
        birthdate=date(1968, 6, 28),
        address="Tiempo de Vals 45, eternamente 25 años",
        height_cm=180,
        weight_kg=_d("78.00"),
        shoe_size=_d("43.0"),
        seat_height=82,
        seat_distance=11,
        handlebar_distance=10,
        cycling_shoe_size=_d("43.0"),
        waitlist_auto_confirm=True,
    ),
    Persona(
        username="mon.laferte",
        first_name="Mon",
        last_name="Laferte",
        gender="female",
        phone_number="+56922220012",
        birthdate=date(1983, 5, 2),
        address="Viña del Mar 1, corazón abierto",
        height_cm=160,
        weight_kg=_d("55.00"),
        shoe_size=_d("37.5"),
        seat_height=70,
        seat_distance=8,
        handlebar_distance=7,
        cycling_shoe_size=_d("37.5"),
    ),
    Persona(
        username="gal.gadot",
        first_name="Gal",
        last_name="Gadot",
        gender="female",
        phone_number="+56922220013",
        birthdate=date(1985, 4, 30),
        address="Themyscira locker, lazo de la verdad en el manubrio",
        height_cm=178,
        weight_kg=_d("63.00"),
        shoe_size=_d("40.0"),
        seat_height=80,
        seat_distance=10,
        handlebar_distance=9,
        cycling_shoe_size=_d("40.0"),
        waitlist_auto_confirm=True,
    ),
    Persona(
        username="simone.biles",
        first_name="Simone",
        last_name="Biles",
        gender="female",
        phone_number="+56922220014",
        birthdate=date(1997, 3, 14),
        address="Vault Lane 4, gravity optional",
        height_cm=142,
        weight_kg=_d("47.00"),
        shoe_size=_d("35.0"),
        seat_height=62,
        seat_distance=6,
        handlebar_distance=6,
        cycling_shoe_size=_d("35.0"),
        waitlist_auto_confirm=True,
    ),
    Persona(
        username="chris.hemsworth",
        first_name="Chris",
        last_name="Hemsworth",
        gender="male",
        phone_number="+56922220015",
        birthdate=date(1983, 8, 11),
        address="Asgard Gym, hamaca de Mjolnir",
        height_cm=191,
        weight_kg=_d("95.00"),
        shoe_size=_d("46.0"),
        seat_height=90,
        seat_distance=13,
        handlebar_distance=12,
        cycling_shoe_size=_d("46.0"),
    ),
    Persona(
        username="rihanna",
        first_name="Rihanna",
        last_name="Fenty",
        gender="female",
        phone_number="+56922220016",
        birthdate=date(1988, 2, 20),
        address="Work Work Work 9, Vitacura",
        height_cm=173,
        weight_kg=_d("64.00"),
        shoe_size=_d("39.5"),
        seat_height=77,
        seat_distance=9,
        handlebar_distance=8,
        cycling_shoe_size=_d("39.5"),
        waitlist_auto_confirm=True,
    ),
    Persona(
        username="elon.musk",
        first_name="Elon",
        last_name="Musk",
        gender="male",
        phone_number="+56922220017",
        birthdate=date(1971, 6, 28),
        address="Starship Pad, next to Sala A",
        height_cm=188,
        weight_kg=_d("86.00"),
        shoe_size=_d("45.0"),
        seat_height=87,
        seat_distance=12,
        handlebar_distance=11,
        cycling_shoe_size=_d("45.0"),
    ),
    Persona(
        username="oprah.winfrey",
        first_name="Oprah",
        last_name="Winfrey",
        gender="female",
        phone_number="+56922220018",
        birthdate=date(1954, 1, 29),
        address="You get a bike, you get a bike 1",
        height_cm=169,
        weight_kg=_d("80.00"),
        shoe_size=_d("40.0"),
        seat_height=76,
        seat_distance=10,
        handlebar_distance=9,
        cycling_shoe_size=_d("40.0"),
        waitlist_auto_confirm=True,
    ),
    Persona(
        username="c.tangana",
        first_name="C.",
        last_name="Tangana",
        gender="male",
        phone_number="+56922220019",
        birthdate=date(1990, 7, 16),
        address="Madrid / Santiago, tropico de la resistencia 8",
        height_cm=178,
        weight_kg=_d("75.00"),
        shoe_size=_d("42.5"),
        seat_height=79,
        seat_distance=10,
        handlebar_distance=9,
        cycling_shoe_size=_d("42.5"),
    ),
    Persona(
        username="dua.lipa",
        first_name="Dua",
        last_name="Lipa",
        gender="female",
        phone_number="+56922220020",
        birthdate=date(1995, 8, 22),
        address="Levitating 11, Las Condes",
        height_cm=173,
        weight_kg=_d("58.00"),
        shoe_size=_d("39.0"),
        seat_height=76,
        seat_distance=9,
        handlebar_distance=8,
        cycling_shoe_size=_d("39.0"),
        waitlist_auto_confirm=True,
    ),
    Persona(
        username="gordon.ramsay",
        first_name="Gordon",
        last_name="Ramsay",
        gender="male",
        phone_number="+56922220021",
        birthdate=date(1966, 11, 8),
        address="Hell's Kitchen locker, it's RAW if you skip warm-up",
        height_cm=188,
        weight_kg=_d("86.00"),
        shoe_size=_d("45.0"),
        seat_height=87,
        seat_distance=12,
        handlebar_distance=11,
        cycling_shoe_size=_d("45.0"),
    ),
    Persona(
        username="florence.pugh",
        first_name="Florence",
        last_name="Pugh",
        gender="female",
        phone_number="+56922220022",
        birthdate=date(1996, 1, 3),
        address="Don't Worry Darling penthouse 2",
        height_cm=162,
        weight_kg=_d("54.00"),
        shoe_size=_d("37.0"),
        seat_height=71,
        seat_distance=8,
        handlebar_distance=7,
        cycling_shoe_size=_d("37.0"),
    ),
    Persona(
        username="ibrahimovic",
        first_name="Zlatan",
        last_name="Ibrahimović",
        gender="male",
        phone_number="+56922220023",
        birthdate=date(1981, 10, 3),
        address="I am PulseFit, PulseFit is me",
        height_cm=195,
        weight_kg=_d("95.00"),
        shoe_size=_d("47.0"),
        seat_height=93,
        seat_distance=14,
        handlebar_distance=13,
        cycling_shoe_size=_d("47.0"),
    ),
    Persona(
        username="billie.eilish",
        first_name="Billie",
        last_name="Eilish",
        gender="female",
        phone_number="+56922220024",
        birthdate=date(2001, 12, 18),
        address="Happier Than Ever, bike 13",
        height_cm=160,
        weight_kg=_d("52.00"),
        shoe_size=_d("37.0"),
        seat_height=69,
        seat_distance=8,
        handlebar_distance=7,
        cycling_shoe_size=_d("37.0"),
        waitlist_auto_confirm=True,
    ),
    Persona(
        username="ke.penny",
        first_name="Penny",
        last_name="Proud",
        gender="female",
        phone_number="+56922220025",
        birthdate=date(1993, 4, 4),
        address="Proud Family locker 5",
        height_cm=165,
        weight_kg=_d("60.00"),
        shoe_size=_d("38.0"),
        seat_height=72,
        seat_distance=9,
        handlebar_distance=8,
        cycling_shoe_size=_d("38.0"),
    ),
)

SPECIAL_EVENTS: tuple[tuple[int, int, str, int, str], ...] = (
    (1, 1, "Año Nuevo: sudor vs. resaca", 11, "Primer climb del año. Promesas en resistencia 8."),
    (
        2,
        14,
        "Valentine's Ride: pedalea con el corazón",
        19,
        "Parejas, singles y bikes con glitter.",
    ),
    (3, 8, "Ride de las Leonas", 10, "8M: potencia, cueing y playlists que empoderan."),
    (4, 1, "April Fools HIIT (no es broma, Usain)", 7, "Sprints reales. El chiste es sobrevivir."),
    (5, 1, "Día del Trabajador: After-Office matinal", 9, "Feriado, pero las piernas trabajan."),
    (6, 21, "Solsticio Midnight Ride", 21, "La noche más larga, el sprint más corto."),
    (7, 16, "Girod Fest: Kristina takeover", 18, "Evento firma. Si no sudas, no estabas."),
    (9, 18, "Dieciocho Ride: empanada after-class", 12, "Cueca opcional, cadencia obligatoria."),
    (10, 31, "Halloween HIIT: brujas en clip-in", 20, "Disfraz sumaba 2 de resistencia extra."),
    (11, 1, "Día de Todos los Riders", 10, "Homenaje a quienes no faltaron en octubre."),
    (12, 24, "Nochebuena Glow Ride", 18, "Luces, villancicos a 140 BPM y abrazos."),
    (12, 31, "NYE Countdown Sprint", 21, "10, 9, 8… sprint. Champagne imaginario."),
)

FUN_RIDER_NOTES = (
    "Pidió el puesto 7 'porque es el de Taylor'. Coach: concedido con glitter.",
    "Llegó con café de especialidad y una tesis sobre cadencia. Escuchar.",
    "Lesión de rodilla imaginaria de telenovela — evitar sprints largos igual.",
    "Prefiere handlebar más cerca, 'modo Top Gun'.",
    "Primera semana; explicar resistencia 1–3 como si fuera un Oscar.",
    "Llega 10 min antes y saluda a la bici por su nombre (Dolores).",
    "Pide playlist con 0 baladas. Cero. Ni en el cool-down.",
    "Trae toalla de superhéroe. No preguntar, solo nod.",
)

FUN_CLASS_BLURBS = (
    "Hoy el ego se queda en el locker y la cadencia entra en IMAX.",
    "Si puedes hablar, puedes subir un cuartito de resistencia.",
    "Clase con derecho a pose de rayo, de cadera o de Oscar.",
    "Evento PulseFit: sudor, drama y un poquito de glitter.",
)

DEMO_STUDIO_ADDRESS = "Camino El Alba 12345, Las Condes, Santiago"
DEMO_STUDIO_LAT = Decimal("-33.402890")
DEMO_STUDIO_LNG = Decimal("-70.580210")
DEMO_OPENING = time(6, 0)
DEMO_CLOSING = time(22, 0)

PROMO_CODES = (
    ("GIRODGOAT", "Kristina te invita: 20% off porque sí.", "PERCENT", "20.00"),
    ("BOLT958", "Sprints a precio de 9.58. $8.000 off.", "FIXED", "8000.00"),
    ("OBAMAARMS", "Let's Move: 15% para brazos y bikes.", "PERCENT", "15.00"),
    ("IMPOSSIBLE", "Misión: ahorrar 10% en el plan.", "PERCENT", "10.00"),
    ("SPINMEBABY", "Promo party ride. $5.000 de descuento.", "FIXED", "5000.00"),
)


def all_personas() -> tuple[Persona, ...]:
    return INSTRUCTORS + MEMBERS


def demo_usernames() -> frozenset[str]:
    return frozenset(item.username for item in all_personas())


def is_preserved_username(username: str) -> bool:
    return username.lower() in PRESERVED_USERNAMES


def persona_user_defaults(persona: Persona) -> dict:
    return {
        "email": persona.email,
        "first_name": persona.first_name,
        "last_name": persona.last_name,
        "is_staff": persona.is_staff,
        "phone_number": persona.phone_number,
        "gender": persona.gender,
        "birthdate": persona.birthdate,
        "address": persona.address,
        "height_cm": persona.height_cm,
        "weight_kg": persona.weight_kg,
        "shoe_size": persona.shoe_size,
        "seat_height": persona.seat_height,
        "seat_distance": persona.seat_distance,
        "handlebar_distance": persona.handlebar_distance,
        "cycling_shoe_size": persona.cycling_shoe_size,
        "waitlist_auto_confirm": persona.waitlist_auto_confirm,
    }


def apply_persona_user(user, persona: Persona, *, preserve_identity: bool) -> None:
    """Fill optional profile fields. Never rename preserved identities."""
    if not preserve_identity:
        user.first_name = persona.first_name
        user.last_name = persona.last_name
        user.email = persona.email
        user.is_staff = persona.is_staff or user.is_staff
    user.phone_number = persona.phone_number or user.phone_number
    user.gender = persona.gender or user.gender
    user.birthdate = persona.birthdate or user.birthdate
    user.address = persona.address or user.address
    user.height_cm = persona.height_cm if persona.height_cm is not None else user.height_cm
    user.weight_kg = persona.weight_kg if persona.weight_kg is not None else user.weight_kg
    user.shoe_size = persona.shoe_size if persona.shoe_size is not None else user.shoe_size
    user.seat_height = persona.seat_height if persona.seat_height is not None else user.seat_height
    user.seat_distance = (
        persona.seat_distance if persona.seat_distance is not None else user.seat_distance
    )
    user.handlebar_distance = (
        persona.handlebar_distance
        if persona.handlebar_distance is not None
        else user.handlebar_distance
    )
    user.cycling_shoe_size = (
        persona.cycling_shoe_size
        if persona.cycling_shoe_size is not None
        else user.cycling_shoe_size
    )
    user.waitlist_auto_confirm = persona.waitlist_auto_confirm
    user.save()


def apply_persona_instructor(instructor, persona: Persona) -> None:
    instructor.tagline = persona.tagline
    instructor.description = persona.description
    instructor.website_url = persona.website_url
    instructor.instagram_username = persona.instagram_username
    instructor.tiktok_username = persona.tiktok_username
    instructor.is_verified = persona.is_verified
    instructor.instructor_since = persona.instructor_since
    instructor.location = persona.location
    instructor.specialties = list(persona.specialties)
    instructor.languages = list(persona.languages)
    instructor.certifications = list(persona.certifications)
    instructor.last_spotify_playlist = persona.last_spotify_playlist
    instructor.last_apple_music_playlist = persona.last_apple_music_playlist
    instructor.last_youtube_music_playlist = persona.last_youtube_music_playlist
    instructor.save()
