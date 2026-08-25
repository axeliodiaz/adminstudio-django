PASSWORD_RESET_CODE_SIZE = 6

# Response detail messages
PASSWORD_RECOVERY_REQUEST_SUCCESS_MESSAGE = (
    "Si el correo electrónico existe, se ha enviado un código de recuperación."
)
PASSWORD_RECOVERY_CONFIRM_SUCCESS_MESSAGE = "Contraseña actualizada exitosamente."
PASSWORD_RECOVERY_INVALID_CODE_MESSAGE = "Código inválido o expirado."
PASSWORD_RECOVERY_CODE_EXPIRED_MESSAGE = "El código de recuperación ha expirado."
PASSWORD_RECOVERY_ADMIN_SUCCESS_MESSAGE = (
    "Se envió un código de recuperación al correo del usuario."
)
PASSWORD_RECOVERY_ADMIN_MISSING_EMAIL_MESSAGE = "El usuario no tiene un correo electrónico."
PASSWORD_RECOVERY_ADMIN_INACTIVE_MESSAGE = "No se puede enviar recuperación a una cuenta inactiva."

EMAIL_CHANGE_ADMIN_SUCCESS_MESSAGE = (
    "Se envió un correo de confirmación a la nueva dirección. "
    "El correo actual se mantiene hasta que el usuario confirme."
)
EMAIL_CHANGE_SAME_EMAIL_MESSAGE = "El nuevo correo es igual al actual."
EMAIL_CHANGE_TAKEN_MESSAGE = "Ya existe un usuario con ese correo."
EMAIL_CHANGE_INVALID_CODE_MESSAGE = "El enlace de confirmación es inválido o ha expirado."
EMAIL_CHANGE_CONFIRM_SUCCESS_MESSAGE = "Correo actualizado exitosamente."
EMAIL_CHANGE_REQUIRES_CONFIRMATION_MESSAGE = (
    "El correo no se puede cambiar directamente. El usuario debe confirmar el nuevo correo."
)
