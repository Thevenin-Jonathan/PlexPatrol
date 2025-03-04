from PyQt5.QtWidgets import QLineEdit
from PyQt5.QtCore import QEvent


class PhoneNumberEdit(QLineEdit):
    """Champ de saisie personnalisé pour les numéros de téléphone français"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.installEventFilter(self)  # Installer l'écouteur d'événements

    def eventFilter(self, obj, event):
        """Filtrer les événements pour détecter la perte de focus"""
        if obj == self and event.type() == QEvent.FocusOut:
            # Convertir automatiquement le numéro lors de la perte de focus
            self.format_phone_number()
        return super().eventFilter(obj, event)

    def format_phone_number(self):
        """Formater le numéro de téléphone au format international (+33)"""
        phone = self.text().strip()

        # Supprimer tous les caractères non numériques
        digits_only = "".join(filter(str.isdigit, phone))

        # Vérifier si c'est un numéro français commençant par 0 et ayant 10 chiffres
        if phone.startswith("0") and len(digits_only) == 10:
            # Remplacer le 0 par +33
            formatted_phone = "+33" + digits_only[1:]
            self.setText(formatted_phone)
        # Pour les numéros déjà au format international
        elif phone.startswith("+33") and len(digits_only) == 11:
            # Conserver tel quel
            pass
        # Format incorrect, mais nous le gardons tel quel pour l'instant
