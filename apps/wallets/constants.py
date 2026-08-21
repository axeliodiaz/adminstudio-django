class PurchaseStatus:
    PENDING = "PENDING"
    PAID = "PAID"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


# Benefit name constants (case-insensitive matching)
class BenefitName:
    PRIORITY_BOOKING = "priority booking"
    PRIORITY_BOOKER = "priority booker"
    RESERVA_PRIORITARIA = "reserva prioritaria"
    FREEZE_MEMBERSHIP = "freeze membership"
    CONGELAR_MEMBRESIA = "congelar membresía"
    CAN_FREEZE = "can freeze"
    FOUNDERS_EXCLUSIVE = "founders exclusive"
    FOUNDERS_PASS = "founders pass"
    FOUNDERS = "founders"
    UNLIMITED_MEMBERSHIP = "unlimited membership"
    MEMBRESIA_ILIMITADA = "membresía ilimitada"
    UNLIMITED = "unlimited"


# Wallet field name constants
class WalletField:
    IS_PRIORITY_BOOKER = "is_priority_booker"
    CAN_FREEZE_MEMBERSHIP = "can_freeze_membership"
    IS_FOUNDERS_EXCLUSIVE = "is_founders_exclusive"
    IS_UNLIMITED_MEMBERSHIP_ACTIVE = "is_unlimited_membership_active"
