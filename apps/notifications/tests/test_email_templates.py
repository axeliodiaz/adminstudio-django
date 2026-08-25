from apps.notifications.email_templates import (
    render_booking_confirmed,
    render_class_cancelled,
)


def test_render_booking_confirmed_matches_sketch_copy():
    html = render_booking_confirmed(
        first_name="María",
        class_title="Power Ride 45",
        coach_name="Tomás Muñoz",
        when_label="Jueves 25 ago · 07:00",
        duration_minutes=45,
        studio_name="PulseFit Patio Andino",
        room_name="Sala A",
        spot=18,
        reservation_url="http://localhost:5173/#my-reservations",
        frontend_url="http://localhost:5173",
        free_cancellation_hours=2,
    )

    assert "Tu spot está reservado" in html
    assert "María, confirmamos tu reserva" in html
    assert "Power Ride 45" in html
    assert "Tomás Muñoz" in html
    assert "Sala A · Spot 18" in html
    assert "Ver mi reserva" in html
    assert "Cancelación gratuita hasta 2 horas antes. Después se descuenta el crédito." in html


def test_render_class_cancelled_matches_sketch_copy():
    html = render_class_cancelled(
        class_title="Morning Climb",
        coach_name="Camila Rojas",
        when_label="martes 26 ago a las 06:30",
        reason="instructor no disponible",
        classes_url="http://localhost:5173/#classes",
        frontend_url="http://localhost:5173",
        credit_refunded=True,
    )

    assert "Tuvimos que cancelar la clase" in html
    assert "Morning Climb" in html
    assert "Camila Rojas" in html
    assert "El crédito ya está de vuelta en tu billetera." in html
    assert "Motivo: instructor no disponible. No se descuenta asistencia." in html
    assert "Ver otras clases del día" in html
    assert "Devolvimos el crédito a tu billetera. Disculpa el cambio." in html
